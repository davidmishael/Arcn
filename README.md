# Arcn

A modular AI assistant built from the ground up in Python. Not a wrapper around an API — every component is understood, designed, and built deliberately.

Arcn listens to what you say, understands what you mean, remembers what you've discussed, and does it. It runs entirely on your machine.

---

## What it does

- Understands natural language commands across 20 intent categories
- Remembers context across a conversation — follow-ups, references, corrections
- Remembers across sessions — recalls past conversations, learns your preferences over time
- Executes real actions: opens apps, searches the web, controls system volume and brightness, sets timers, takes notes, tells the time and date, fetches live weather
- Asks Mistral 7B knowledge questions with full multi-turn context restored after restarts
- Runs fully offline — no cloud, no subscriptions, no data leaving your machine (weather requires internet)

---

## Architecture

Arcn is built as a set of independent cognitive modules, each with a single responsibility, coordinated through a central orchestration layer.

```
Voice / Text
│
▼
NLP Module          ← understands language, extracts intent and entities
│
▼
Command Center      ← orchestrates, routes, enriches with memory context
│         │
│         ▼
│       Memory      ← SQLite (history, preferences) + ChromaDB (semantic search)
│
▼
Tools Module        ← executes the actual actions
```

The defining principle: no module does another module's job. The NLP doesn't execute actions. The Command Center doesn't parse language. Clean contracts between everything.

---

## Modules

### NLP Module
The language understanding layer. Processes raw text into a structured packet the Command Center can act on.

- Fine-tuned DistilBERT trained on 300 examples across 20 intent categories
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

- Routes intents and entities to the right tool
- Enriches packets with saved preferences and recent history before routing
- Handles unknown intents and clarification requests
- Manages system state
- Graceful shutdown on both voice command and KeyboardInterrupt

### Memory Module
Persistent context layer. Two-tier architecture:

- **SQLite** — sessions, full conversation history, user preference accumulation
- **ChromaDB** — semantic vector search over all past conversations using `all-MiniLM-L6-v2`
- Passive preference learning — learns default city, units, and more from repeated usage
- Cross-session recall — Mistral restores conversation context after restarts
- Semantic recall — finds relevant past turns even from weeks ago by meaning, not recency

### Tools Module
The execution layer. A registry of real actions the system can take.

- App launching (YouTube, Chrome, Terminal, VS Code, Notes, Finder, Settings)
- System controls (volume, brightness, lock)
- Web search (Google, YouTube)
- Timer with Mac notification
- Notes saved to disk with timestamps
- Time and date
- Music control via Spotify (play, pause, skip)
- Live weather via OpenWeatherMap — any city, defaults to Chennai
- Developer and study workspace modes
- Reminders via Mac Reminders app (osascript)
- Knowledge questions via Mistral 7B with persistent cross-session memory

---

## Roadmap

- [x] NLP — intent classification, entity extraction, multi-turn context
- [x] Command Center — orchestration, routing, state management
- [x] Tools — real Mac actions across 20 intent categories
- [x] Speech — voice input via Whisper, voice output via Kokoro TTS
- [x] Weather — live weather via OpenWeatherMap API
- [x] Memory — SQLite session history + ChromaDB semantic vector search
- [x] Cross-session recall — Mistral restores context after restarts
- [x] Preference learning — passive preference accumulation from usage
- [ ] send_message — iMessage via phone number mapping
- [ ] main.py — single entry point that boots the full system
- [ ] Notes → Apple Notes app via osascript
- [ ] lock_mac intent wired up
- [ ] Cancel/modify reminders
- [ ] Proactive engine — schedule-aware, condition-triggered assistant actions
- [ ] Computer Vision — gesture recognition, screen analysis via LLaVA
- [ ] Logs & Validator — action auditing, confidence checks, safety layer
- [ ] Ambient UI — visual state feedback
- [ ] Cross-platform support — Windows and Linux

---

## Setup

**Requirements:** Python 3.12, macOS (Mac-first, cross-platform support planned)

```bash
git clone https://github.com/foxCoder-star/Arcn.git
cd Arcn
```

**NLP module:**
```bash
cd nlp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m spacy download en_core_web_sm
python3 train_intent.py
deactivate
```

**Command Center:**
```bash
cd ../command_center
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

**Tools:**
```bash
cd ../tools_assistant
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

**Memory:**
```bash
cd ../memory
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

**Speech:**
```bash
cd ../speech
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

**System dependency (required for Kokoro TTS):**
```bash
brew install espeak-ng
```

**Environment variables:**
Create `tools_assistant/.env` and add:
```
OPENWEATHER_API_KEY=your_key_here
```

**Run:**
```bash
cd command_center
source venv/bin/activate
python3 test_wired.py
```

---

## Tech Stack

- Python 3.12
- HuggingFace Transformers — DistilBERT fine-tuning
- PyTorch — model training and inference
- spaCy — named entity recognition
- faster-whisper — local speech recognition
- Kokoro TTS — local neural voice output (offline, Apple Silicon optimized)
- Ollama + Mistral 7B — local knowledge engine
- SQLite — persistent session and conversation history
- ChromaDB — semantic vector memory with all-MiniLM-L6-v2 embeddings
- OpenWeatherMap API — live weather data
- MediaPipe — gesture recognition (planned)
- LLaVA — vision and screen understanding (planned)

---

## Status

Core pipeline — NLP → Command Center → Tools — is fully operational. Speech (Whisper + Kokoro TTS) is integrated and running. Weather is live. Memory is complete — SQLite tracks full conversation history and user preferences across sessions, ChromaDB enables semantic recall of relevant past conversations. Mistral restores prior conversation context on every boot.

Everything from here builds toward a proactive, memory-driven assistant that acts on your behalf without being asked.

---

Built by David Mishael.