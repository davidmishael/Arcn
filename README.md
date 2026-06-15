# Arcn

A modular AI assistant built from the ground up in Python. Not a wrapper around an API — every component is understood, designed, and built deliberately.

Arcn listens to what you say, understands what you mean, remembers what you've discussed, and does it. It runs entirely on your machine.

---

## What it does

- Understands natural language commands across 20+ intent categories
- Remembers context across a conversation — follow-ups, references, corrections
- Remembers across sessions — recalls past conversations, learns your preferences over time
- Executes real actions: opens apps, searches the web, controls system volume and brightness, sets timers, takes notes in Apple Notes, tells the time and date, fetches live weather, controls Spotify
- Asks Mistral 7B knowledge questions with full multi-turn context restored after restarts
- Activates on wake word — always-on CNN detector, trained on your voice only
- Runs fully offline — no cloud, no subscriptions, no data leaving your machine (weather requires internet)

---

## Architecture

Arcn is built as a set of independent cognitive modules, each with a single responsibility, coordinated through a central orchestration layer.

```
Wake Word (CNN)
│
▼
Voice Input (Whisper)
│
▼
NLP Module          ← understands language, extracts intent and entities
│
▼
Command Center      ← orchestrates, routes, enriches with memory context
│         │
│         ▼
│       Memory      ← SQLite (history, preferences, state) + ChromaDB (semantic search)
│
▼
Tools Module        ← executes the actual actions
│
▼
Voice Output (Kokoro TTS)
```

The defining principle: no module does another module's job. The NLP doesn't execute actions. The Command Center doesn't parse language. Clean contracts between everything.

---

## Modules

### NLP Module
The language understanding layer. Processes raw text into a structured packet the Command Center can act on.

- Fine-tuned DistilBERT trained on 300 examples across 20+ intent categories
- Confidence scoring with automatic unknown intent detection
- spaCy NER + regex for entity extraction (durations, times, people, apps, locations)
- 10-turn context window with slot accumulation, follow-up detection, and vague reference resolution

Output:
```python
{
    "intent": "set_timer",
    "confidence": 0.921,
    "entities": {"duration": "10 mins"},
    "requires_clarification": False,
    "context_used": False
}
```

### Command Center
The orchestration core. Receives structured packets, enriches them with memory context, and decides what to do.

- Routes intents and entities to the right tool via `INTENT_MAP`
- Enriches packets with saved preferences and recent history before routing
- Multi-turn clarification via pending state pattern — saves context to `StateManager`, restores on next turn
- Graceful shutdown on both voice command and KeyboardInterrupt

### Memory Module
Persistent context layer. Two-tier architecture:

- **SQLite** — sessions, full conversation history, user preference accumulation, system state (WAL mode)
- **ChromaDB** — semantic vector search over all past conversations using `all-MiniLM-L6-v2`
- Passive preference learning — learns default city, units, and more from repeated usage (minimum 2 occurrences before persisting)
- Cross-session recall — Mistral restores conversation context after restarts
- Semantic recall — finds relevant past turns by meaning, not just recency

### Tools Module
The execution layer. A registry of 30+ real actions the system can take.

- App launching (YouTube, Chrome, Terminal, VS Code, Apple Notes, Finder, Settings, Spotify)
- System controls (volume, brightness, lock screen via Ctrl+Cmd+Q)
- Web search (Google, YouTube)
- Timer with Mac notification
- Notes saved to Apple Notes via osascript
- Time and date
- Music control via Spotify (play, pause, skip) via osascript
- Live weather via OpenWeatherMap — any city, defaults to Chennai
- Developer and study workspace modes
- Reminders via Mac Reminders app (osascript)
- Knowledge questions via Mistral 7B with persistent cross-session memory context

### Speech Module
Voice I/O and wake word detection.

- **Wake word** — always-on tiny CNN, mel spectrogram input, trained on your voice only. Confidence threshold 0.88. Model and training architecture kept in sync (`wake_word.py` ↔ `train_wake_word.py`)
- **Input** — faster-whisper (small model, int8), energy threshold 600, 4s timeout
- **Output** — Kokoro TTS, `af_heart` voice, 24000Hz, chunked streaming, PyTorch

---

## Roadmap

- [x] NLP — intent classification, entity extraction, multi-turn context
- [x] Command Center — orchestration, routing, state management
- [x] Tools — 30+ real Mac actions
- [x] Speech — voice input via faster-whisper, voice output via Kokoro TTS
- [x] Weather — live weather via OpenWeatherMap API
- [x] Memory — SQLite session history + ChromaDB semantic vector search
- [x] Cross-session recall — Mistral restores context after restarts
- [x] Preference learning — passive preference accumulation from usage
- [x] Unified entry point — single `main.py` boots the full system
- [x] Notes → Apple Notes via osascript
- [x] lock_mac intent wired up
- [x] SQLite state — replaces `assistant_state.json`
- [x] Wake word detection — always-on CNN, user-voice-trained
- [x] pywebview UI — Sheikah-inspired SVG rings, state-driven animations
- [ ] send_message — iMessage via phone number mapping
- [ ] Menu bar icon — deferred to .app packaging phase
- [ ] Cancel/modify reminders
- [ ] Proactive engine — schedule-aware, condition-triggered assistant actions
- [ ] Computer Vision — gesture recognition, screen analysis via LLaVA
- [ ] Cross-platform support — Windows and Linux

---

## Setup

**Requirements:** Python 3.12, macOS (M1/Apple Silicon), [Ollama](https://ollama.com) with Mistral 7B pulled

```bash
git clone https://github.com/davidmishael/Arcn.git
cd Arcn
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m spacy download en_core_web_sm
brew install espeak-ng
```

**Train the intent classifier (one-time):**
```bash
python3 nlp/train_intent.py
```

**Train the wake word model (one-time):**

Record samples first:
```bash
python3 speech/record_samples.py
```
Then train:
```bash
python3 speech/train_wake_word.py
```

**Environment variables:**
Create `tools_assistant/.env` and add:
```
OPENWEATHER_API_KEY=your_key_here
```

**Run:**
```bash
source venv/bin/activate
python3 main.py
```

---

## Tech Stack

- Python 3.12
- HuggingFace Transformers — DistilBERT fine-tuning
- PyTorch — model training and inference
- spaCy — named entity recognition
- faster-whisper — local speech recognition (small, int8)
- Kokoro TTS — local neural voice output (offline, Apple Silicon optimized)
- Ollama + Mistral 7B — local knowledge engine
- SQLite (WAL mode) — persistent session history, preferences, system state
- ChromaDB — semantic vector memory with all-MiniLM-L6-v2 embeddings
- sentence-transformers — all-MiniLM-L6-v2
- OpenWeatherMap API — live weather data (only external dependency)
- MediaPipe — gesture recognition (planned)
- LLaVA — vision and screen understanding (planned)

---

## Status

Core pipeline fully operational end-to-end: wake word → Whisper → NLP → Command Center → Tools → Kokoro TTS. Memory is complete — SQLite tracks full conversation history, preferences, and system state across sessions; ChromaDB enables semantic recall of relevant past conversations. Mistral restores prior context on every boot. Wake word detector trained and integrated. pywebview UI live with state-driven Sheikah-inspired animations.

Everything from here builds toward a proactive, memory-driven assistant that acts on your behalf without being asked.

---

Built by David Mishael.