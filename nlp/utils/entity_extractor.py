import re
import spacy


# -------------------------
# Load spaCy model
# -------------------------
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    raise OSError(
        "spaCy English model not found. "
        "Run: python3 -m spacy download en_core_web_sm"
    )


# -------------------------
# Intent → relevant slots
# -------------------------
INTENT_SLOTS = {
    "set_timer"        : ["duration"],
    "cancel_timer"     : [],
    "create_reminder"  : ["time", "date", "relative_time", "person", "topic"],
    "play_music"       : ["app", "genre"],
    "pause_music"      : [],
    "skip_song"        : [],
    "web_search"       : ["query", "topic", "app"],
    "open_app"         : ["app"],
    "close_app"        : ["app"],
    "get_weather"      : ["location", "date", "relative_time", "unit"],
    "take_note"        : ["topic"],
    "ask_question"     : ["topic"],
    "system_volume"    : ["direction", "amount"],
    "system_brightness": ["direction", "amount"],
    "send_message"     : ["person", "topic"],
    "stop_cancel"      : [],
    "greet"            : [],
    "how_are_you"      : [],
    "tell_time"        : [],
    "tell_date"        : [],
    "unknown_intent"   : []
}


# -------------------------
# Known apps list
# -------------------------
KNOWN_APPS = [
    "spotify", "chrome", "discord", "youtube",
    "whatsapp", "twitch", "netflix", "safari",
    "vs code", "vscode", "terminal", "notepad",
    "calculator", "settings", "finder",
    "chat gpt", "chatgpt", "notes"
]

MUSIC_GENRES = [
    "lo-fi", "lofi", "chill", "jazz", "hip hop",
    "classical", "rock", "pop", "ambient", "study"
]

WORD_TO_NUM = {
    "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8",
    "nine": "9", "ten": "10", "eleven": "11", "twelve": "12",
    "fifteen": "15", "twenty": "20", "thirty": "30",
    "forty": "40", "forty-five": "45", "sixty": "60"
}


# -------------------------
# spaCy NER extraction
# -------------------------
def _spacy_entities(text: str, doc) -> dict:

    entities = {}

    for ent in doc.ents:

        if ent.label_ == "PERSON":
            entities["person"] = ent.text

        elif ent.label_ in ("TIME",):
            entities["time"] = ent.text

        elif ent.label_ in ("DATE",):
            relative = ["tomorrow", "today", "tonight", "morning", "evening", "friday",
                        "monday", "tuesday", "wednesday", "thursday", "saturday", "sunday"]
            if any(r in ent.text.lower() for r in relative):
                entities["relative_time"] = ent.text
            else:
                entities["date"] = ent.text

        elif ent.label_ == "GPE":
            entities["location"] = ent.text

        elif ent.label_ == "ORG":
            if ent.text.lower() in KNOWN_APPS:
                entities["app"] = ent.text.lower()

        elif ent.label_ == "CARDINAL":
            entities["amount"] = ent.text

    return entities


# -------------------------
# Regex fallback extraction
# -------------------------
def _regex_entities(text: str) -> dict:
    entities = {}
    text_lower = text.lower()

    # Normalize word numbers to digits
    for word, num in WORD_TO_NUM.items():
        text_lower = re.sub(rf'\b{word}\b', num, text_lower)
        
    # Duration — "5 minutes", "30 seconds", "1 hour"
    duration_match = re.search(
        r"\b(\d+)\s*(s|sec|secs|seconds?|m|min|mins|minutes?|h|hr|hrs|hours?)\b",
        text_lower
    )
    if duration_match:
        entities["duration"] = (
            f"{duration_match.group(1)} {duration_match.group(2)}"
        )

    # Explicit time — "7pm", "8:30am"
    time_match = re.search(
        r"\b(\d{1,2}(:\d{2})?\s?(am|pm))\b",
        text_lower
    )
    if time_match:
        entities["time"] = time_match.group(1)

    # Relative time keywords
    for word in ["tomorrow", "tonight", "morning", "evening", "today"]:
        if word in text_lower:
            entities["relative_time"] = word

    # App detection
    for app in KNOWN_APPS:
        if app in text_lower:
            entities["app"] = app

    # Music genre
    for genre in MUSIC_GENRES:
        if genre in text_lower:
            entities["genre"] = genre

    # Volume / brightness direction
    if any(w in text_lower for w in ["up", "louder", "brighter", "higher", "increase", "max"]):
        entities["direction"] = "up"
    elif any(w in text_lower for w in ["down", "lower", "quieter", "dimmer", "decrease", "reduce", "dim"]):
        entities["direction"] = "down"
    elif "mute" in text_lower:
        entities["direction"] = "mute"

    # Percentage amount — "50 percent", "80%"
    percent_match = re.search(r"\b(\d+)\s*(%|percent)\b", text_lower)
    if percent_match:
        entities["amount"] = f"{percent_match.group(1)}%"

    # Bare number — store for slot filling with context
    bare_match = re.search(r"\b(\d+)\b", text_lower)
    if bare_match and "duration" not in entities and "amount" not in entities:
        entities["bare_number"] = bare_match.group(1)

    # Temperature unit
    if any(w in text_lower for w in ["fahrenheit", "in f", "degrees f"]):
        entities["unit"] = "imperial"
    elif any(w in text_lower for w in ["celsius", "in c", "degrees c"]):
        entities["unit"] = "metric"

    return entities


# -------------------------
# Intent-aware slot filter
# -------------------------
def _filter_by_intent(entities: dict, intent: str) -> dict:
    relevant_slots = INTENT_SLOTS.get(intent, None)
    if relevant_slots is None:
        return entities
    return {
        k: v for k, v in entities.items()
        if k in relevant_slots or k == "bare_number"
    }


# -------------------------
# Topic extraction
# (for notes, questions, searches)
# -------------------------


def _extract_topic(text: str, intent: str) -> dict:

    entities = {}

    topic_intents = ["take_note", "ask_question", "web_search", "send_message", "create_reminder"]

    if intent not in topic_intents:
        return entities

    strip_phrases = [
        "could you remind me to",
        "could you remind me about",
        "can you remind me to",
        "can you remind me about",
        "please remind me to",
        "please remind me about",
        "remind me to", "remind me about", "remind me",
        "search for ", "look up", "google", "find information about",
        "take a note", "write down", "note that", "note to self",
        "tell me about", "explain", "what is", "how does", "who is",
        "text", "send a message to", "tell", "search for", "search google for", 
        "search youtube for", "search on youtube for"
    ]

    cleaned = text.lower()
    for phrase in strip_phrases:
        cleaned = cleaned.replace(phrase, "").strip()

    # Clean up any leftover filler words
    filler = ["could you", "can you", "please", "hey", "actually"]
    for word in filler:
        cleaned = cleaned.replace(word, "").strip()

    # Strip time expressions from topic for reminders
    if intent == "create_reminder":
        topic_cleaned = re.sub(
            r'\b(at|by|on|for)?\s*\d{1,2}(:\d{2})?\s*(a\.?m\.?|p\.?m\.?)\b',
            '',
            cleaned,
            flags=re.IGNORECASE
        ).strip()

        # Strip relative time from topic
        topic_cleaned = re.sub(
            r'\bin\s+\d+\s*(s|sec|secs|seconds?|m|min|mins|minutes?|h|hr|hrs|hours?)\b',
            '',
            topic_cleaned,
            flags=re.IGNORECASE
        ).strip(" .")

        # Strip day/date/time-of-day references
        topic_cleaned = re.sub(
            r'\b(tomorrow|today|tonight|night|morning|afternoon|evening|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            '',
            topic_cleaned,
            flags=re.IGNORECASE
        ).strip(" .")

        # Final cleanup — stray prepositions and punctuation
        topic_cleaned = re.sub(r'\b(on|at|by|for|in)\b', '', topic_cleaned, flags=re.IGNORECASE)
        topic_cleaned = re.sub(r'\s+', ' ', topic_cleaned).strip(" .")

        if topic_cleaned:
            entities["topic"] = topic_cleaned
        return entities

    if cleaned:
        key = "query" if intent == "web_search" else "topic"
        entities[key] = cleaned

    return entities

# -------------------------
# Main extraction function
# -------------------------
def extract_entities(text: str, intent: str = "unknown_intent") -> dict:

    doc = nlp(text)

    # 1. spaCy NER
    spacy_ents = _spacy_entities(text, doc)

    # 2. Regex fallback
    regex_ents = _regex_entities(text)

    # 3. Topic extraction
    topic_ents = _extract_topic(text, intent)

    # Merge — spaCy takes priority, regex fills gaps
    merged = {**regex_ents, **spacy_ents, **topic_ents}

    # 4. Filter to relevant slots for this intent
    filtered = _filter_by_intent(merged, intent)

    return filtered