import os
import time
import urllib.parse
import threading
import datetime
from dotenv import load_dotenv
import requests
import random
from speaker import speak as _speak
import subprocess

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
DEFAULT_CITY = "Toronto"


# -------------------------
# Music tools
# -------------------------
def play_music(entities: dict = {}):
    os.system("open -a Spotify")
    os.system("osascript -e 'tell application \"Spotify\" to play'")
    return random.choice([
        "Spotify's up. Enjoy.",
        "Music on.",
        "Playing.",
    ])

def pause_music(entities: dict = {}):
    os.system("osascript -e 'tell application \"Spotify\" to playpause'")
    return random.choice([
        "Paused.",
        "Done.",
        "Stopped the music.",
    ])

def skip_song(entities: dict = {}):
    os.system("osascript -e 'tell application \"Spotify\" to next track'")
    return random.choice([
        "Skipped.",
        "Next track.",
        "Moving on.",
    ])


# -------------------------
# TIMER STATE
# -------------------------
_timer_thread = None
_timer_cancel = threading.Event()


# -------------------------
# WEBSITE TOOLS
# -------------------------

def open_youtube(entities: dict = {}):
    os.system("open -a 'Google Chrome' 'https://youtube.com'")
    return random.choice([
        "YouTube's open.",
        "Opening YouTube.",
        "There you go.",
    ])

def open_google(entities: dict = {}):
    os.system("open -a 'Google Chrome'")
    return random.choice([
        "Chrome's open.",
        "Google's up.",
        "Opening Chrome.",
    ])

def open_chatgpt(entities: dict = {}):
    os.system("open -a 'Google Chrome' 'https://chatgpt.com'")
    return random.choice([
        "Opening ChatGPT. The competition.",
        "ChatGPT's up.",
        "Opening ChatGPT.",
    ])

def open_spotify(entities: dict = {}):
    os.system("open -a Spotify")
    return random.choice([
        "Spotify's open.",
        "Opening Spotify.",
    ])


# -------------------------
# APP TOOLS
# -------------------------

def open_terminal(entities: dict = {}):
    os.system("open -a Terminal")
    return random.choice([
        "Terminal's open. Try not to break anything.",
        "Terminal up.",
        "Opening Terminal.",
    ])

def open_notes(entities: dict = {}):
    os.system("open -a Notes")
    return random.choice([
        "Notes is open.",
        "Opening Notes.",
    ])

def open_finder(entities: dict = {}):
    os.system("open -a Finder")
    return random.choice([
        "Finder's open.",
        "Opening Finder.",
    ])

def open_settings(entities: dict = {}):
    os.system("open -a 'System Settings'")
    return random.choice([
        "Settings open. Don't touch anything important.",
        "Opening Settings.",
        "Settings up.",
    ])

def open_vscode(entities: dict = {}):
    os.system("open -a 'Visual Studio Code'")
    return random.choice([
        "VS Code's open. Let's build something.",
        "Opening VS Code.",
        "VS Code up.",
    ])


# -------------------------
# CONTROL TOOLS
# -------------------------

def close_app(entities: dict = {}):
    os.system(
        "osascript -e 'tell application \"System Events\" to keystroke \"q\" using command down'"
    )
    return random.choice([
        "Closed.",
        "Done.",
        "Gone.",
    ])

def increase_volume(entities: dict = {}):
    os.system(
        "osascript -e \"set volume output volume ((output volume of (get volume settings)) + 10)\""
    )
    return random.choice([
        "Volume up.",
        "Louder.",
        "Turned it up.",
    ])

def decrease_volume(entities: dict = {}):
    os.system(
        "osascript -e \"set volume output volume ((output volume of (get volume settings)) - 10)\""
    )
    return random.choice([
        "Volume down.",
        "Quieter.",
        "Turned it down.",
    ])

def mute_volume(entities: dict = {}):
    os.system(
        "osascript -e \"set volume with output muted\""
    )
    return random.choice([
        "Muted.",
        "Silenced.",
        "Quiet mode.",
    ])

def lock_mac(entities: dict = {}):
    os.system("osascript -e 'tell application \"System Events\" to keystroke \"q\" using {control down, command down}'")
    return random.choice([
        "Locking. Don't go anywhere.",
        "Locked.",
        "Locking up.",
    ])

def increase_brightness(entities: dict = {}):
    os.system(
        "osascript -e 'tell application \"System Events\" to key code 144'"
    )
    return random.choice([
        "Brighter.",
        "Brightness up.",
        "Turned it up.",
    ])

def decrease_brightness(entities: dict = {}):
    os.system(
        "osascript -e 'tell application \"System Events\" to key code 145'"
    )
    return random.choice([
        "Dimmed.",
        "Brightness down.",
        "Turned it down.",
    ])


# -------------------------
# SEARCH TOOLS
# -------------------------

def search_youtube(entities: dict = {}):
    query = entities.get("query", "")
    encoded = urllib.parse.quote(query)
    os.system(
        f"open -a 'Google Chrome' 'https://www.youtube.com/results?search_query={encoded}'"
    )
    return f"Searching YouTube for {query}." if query else "Searching YouTube."

def search_google(entities: dict = {}):
    query = entities.get("query", "")
    encoded = urllib.parse.quote(query)
    os.system(
        f"open -a 'Google Chrome' 'https://www.google.com/search?q={encoded}'"
    )
    return f"Searching for {query}." if query else "Searching Google."


# -------------------------
# TIMER TOOLS
# -------------------------

def _parse_duration(entities: dict) -> int:
    """Convert duration entity to seconds."""
    duration = entities.get("duration", "")
    if not duration:
        return 0

    duration = duration.lower()
    parts = duration.split()

    if len(parts) < 2:
        return 0

    try:
        amount = int(parts[0])
    except ValueError:
        return 0

    unit = parts[1]

    if unit.startswith("s"):
        return amount
    elif unit.startswith("m"):
        return amount * 60
    elif unit.startswith("h"):
        return amount * 3600

    return 0


def set_timer(entities: dict = {}):
    global _timer_thread, _timer_cancel
    print(f"DEBUG entities in set_timer: {entities}")


    seconds = _parse_duration(entities)

    if seconds == 0:
        return "Couldn't figure out the duration. Try again."

    # Cancel any existing timer
    _timer_cancel.set()
    _timer_cancel = threading.Event()

    def countdown():
        cancelled = _timer_cancel.wait(timeout=seconds)
        if not cancelled:
            os.system("osascript -e 'display notification \"Timer is up!\" with title \"Arcn\"'")
            _speak("Time's up.")

    _timer_thread = threading.Thread(target=countdown, daemon=True)
    _timer_thread.start()

    # Human-readable duration
    if seconds < 60:
        label = f"{seconds} seconds"
    elif seconds < 3600:
        label = f"{seconds // 60} minutes"
    else:
        label = f"{seconds // 3600} hours"

    return random.choice([
        f"Timer set for {label}. I'll let you know.",
        f"{label}. On it.",
        f"Timer running — {label}.",
    ])


def cancel_timer(entities: dict = {}):
    global _timer_cancel
    _timer_cancel.set()
    return random.choice([
        "Timer cancelled.",
        "Stopped.",
        "Timer's gone.",
    ])


# -------------------------
# TIME + DATE
# -------------------------

def tell_time(entities: dict = {}):
    now = datetime.datetime.now()
    time_str = now.strftime("%I:%M %p")
    return random.choice([
        f"It's {time_str}.",
        f"{time_str}.",
        f"Currently {time_str}.",
    ])

def tell_date(entities: dict = {}):
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %B %d %Y")
    return random.choice([
        f"Today is {date_str}.",
        f"{date_str}.",
        f"It's {date_str}.",
    ])


# -------------------------
# NOTES
# -------------------------

def take_note(entities: dict = {}):
    from state import StateManager
    import db  # SQLite notes live here now
    state = StateManager()

    stage        = state.get_pending_note_stage()
    raw          = entities.get("raw_text", "").strip()
    title_entity = entities.get("title", "").strip()

    # ── Stage 0: fresh "take a note" — kick off the flow ──
    if not stage:
        # Title was given inline ("make a note called study list") —
        # skip the title prompt entirely, go straight to content.
        if title_entity:
            state.set_pending_note_title(title_entity)
            print(f"DEBUG stage0 set title to: {repr(title_entity)}, readback: {repr(state.get_pending_note_title())}")
            state.set_pending_note_stage("awaiting_content")
            return "What should the note say?"

        state.set_pending_note_stage("awaiting_title")
        return "What do you want to title it?"

    # ── Stage 1: this reply is the title ──
    if stage == "awaiting_title":
        if not raw:
            return "What do you want to title it?"
        state.set_pending_note_title(raw)
        state.set_pending_note_stage("awaiting_content")
        return "What should the note say?"

    # ── Stage 2: this reply is the content — save to SQLite ──
    if stage == "awaiting_content":
        title   = state.get_pending_note_title()
        content = raw

        if not content:
            return "What should the note say?"

        state.set_pending_note_content(content)  # stage for UI visibility before save
        note_id = db.create_note(title, content)

        time.sleep(1.2)  # hold pending state open long enough for the UI's
                          # 500ms poll loop to actually see the saved content
                          # before we clear it and the overlay auto-closes

        state.clear_pending_note_content()
        state.set_last_note_id(note_id)

        state.clear_pending_note_stage()
        state.clear_pending_note_title()

        return random.choice([
            f"Noted — {title}. Say 'save that on my Mac too' if you want a copy in Notes.",
            f"Got it. Saved. Let me know if you want it in Apple Notes too.",
            f"Saved — {title}.",
        ])

    # ── Fallback — shouldn't be reachable, but don't get stuck ──
    state.clear_pending_note_stage()
    state.clear_pending_note_title()
    return "Something went wrong with that note. Let's try again."


def export_note_mac(entities: dict = {}):
    from state import StateManager
    import db
    state = StateManager()

    note_id = state.get_last_note_id()
    if not note_id:
        return "I don't have a recent note to export. Take a note first."

    note = db.get_note(note_id)
    if not note:
        return "Couldn't find that note anymore."

    if note["exported_to_mac"]:
        return "That one's already in Apple Notes."

    safe_title   = note["title"].replace("\\", "\\\\").replace('"', '\\"')
    safe_content = note["content"].replace("\\", "\\\\").replace('"', '\\"')

    script = f'''
    tell application "Notes"
        make new note at folder "Notes" with properties {{name:"{safe_title}", body:"{safe_content}"}}
    end tell
    '''

    try:
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"[export_note_mac] osascript failed: {e.stderr}")
        return "Couldn't save that to Apple Notes."
    except subprocess.TimeoutExpired:
        print("[export_note_mac] osascript timed out")
        return "Couldn't save that to Apple Notes — timed out."

    db.mark_note_exported(note_id)
    return random.choice([
        "Saved to Apple Notes too.",
        "Done — it's in Notes now.",
        "Copied over to Apple Notes.",
    ])

# -------------------------
# Shared single-match lookup —
# used by read_note / edit_note / delete_note.
# Deliberately fails on 0 or 2+ matches rather
# than guessing — minimum viable disambiguation.
# -------------------------
def _find_single_note(note_query: str):
    import db

    if not note_query:
        return None, "Which note do you mean?"

    matches = db.search_notes_by_title(note_query)

    if not matches:
        return None, f"I couldn't find a note matching '{note_query}'."

    if len(matches) > 1:
        return None, "I found more than one note matching that — try being more specific."

    return matches[0], None


def read_note(entities: dict = {}):
    from state import StateManager
    state = StateManager()

    note_query = entities.get("note_query", "").strip()
    note, error = _find_single_note(note_query)

    if error:
        # Even on failure, open the grid — better than a dead end
        state.set_pending_show_note_id(-1)  # -1 = "open grid, nothing to highlight"
        return error

    state.set_pending_show_note_id(note["id"])
    return f"{note['title']} — {note['content']}"


def delete_note(entities: dict = {}):
    from state import StateManager
    import db
    state = StateManager()

    pending_action = state.get_pending_note_action()

    # ── Awaiting yes/no confirmation ──
    if pending_action == "delete":
        raw = entities.get("raw_text", "").strip().lower()
        note_id = state.get_pending_note_id()

        confirm_words = ["yes", "yeah", "yep", "confirm", "delete it", "do it"]
        cancel_words  = ["no", "nope", "cancel", "nevermind", "don't", "stop"]

        if any(w in raw for w in confirm_words):
            note = db.get_note(note_id)
            db.delete_note(note_id)
            state.clear_pending_note_action_full()
            title = note["title"] if note else "that note"
            return f"Deleted — {title}."

        if any(w in raw for w in cancel_words):
            state.clear_pending_note_action_full()
            return "Okay, keeping it."

        # Neither confirm nor cancel — re-ask, stay pending
        state.set_needs_followup(True)
        return "Say yes to confirm the delete, or no to cancel."

    # ── Fresh delete request — search first ──
    note_query = entities.get("note_query", "").strip()
    note, error = _find_single_note(note_query)
    if error:
        return error

    state.set_pending_note_action("delete")
    state.set_pending_note_id(note["id"])
    state.set_needs_followup(True)
    return f"Delete '{note['title']}'? Say yes to confirm."


def edit_note(entities: dict = {}):
    from state import StateManager
    import db
    state = StateManager()

    pending_action = state.get_pending_note_action()

    # ── Awaiting new content ──
    if pending_action == "edit":
        raw = entities.get("raw_text", "").strip()
        note_id = state.get_pending_note_id()

        if not raw:
            state.set_needs_followup(True)
            return "What should it say instead?"

        db.update_note_content(note_id, raw)
        note = db.get_note(note_id)
        title = note["title"] if note else "the note"
        state.clear_pending_note_action_full()
        return f"Updated — {title}."

    # ── Fresh edit request — search first ──
    note_query = entities.get("note_query", "").strip()
    note, error = _find_single_note(note_query)
    if error:
        return error

    state.set_pending_note_action("edit")
    state.set_pending_note_id(note["id"])
    state.set_needs_followup(True)
    return f"What should '{note['title']}' say instead?"

# -------------------------
# MODES
# -------------------------

def developer_mode(entities: dict = {}):
    os.system("open -a 'Visual Studio Code'")
    os.system("open -a Terminal")
    return random.choice([
        "Developer workspace ready. Let's build.",
        "VS Code and Terminal up. Go.",
        "Dev mode. You know what to do.",
    ])

def study_mode(entities: dict = {}):
    os.system("osascript -e 'set volume with output muted'")
    os.system("open -a 'Google Chrome'")
    return random.choice([
        "Study mode. Muted, Chrome's open. Focus.",
        "Muted and ready. No distractions.",
        "Study mode on. Make it count.",
    ])


# -------------------------
# GREET + PERSONALITY
# -------------------------

def greet(entities: dict = {}):
    hour = datetime.datetime.now().hour
    if hour < 6:
        greetings = [
            "You're up early. Or very late. Either way, I'm here.",
            "It's the middle of the night. This better be important.",
        ]
    elif hour < 12:
        greetings = [
            "Morning. Let's make it count.",
            "Good morning. I've been waiting.",
            "Morning. Coffee first, or straight to it?",
        ]
    elif hour < 17:
        greetings = [
            "Afternoon. What do you need?",
            "Back again. What are we solving?",
            "Good afternoon. I'm listening.",
        ]
    else:
        greetings = [
            "Evening. Long day?",
            "Good evening. Still at it, I see.",
            "Evening. What's on your mind?",
        ]
    return random.choice(greetings)


def how_are_you(entities: dict = {}):
    responses = [
        "Running clean, no complaints. You?",
        "Fully operational and mildly bored until now. You?",
        "Better now that you're here. You?",
        "Everything's nominal. More importantly — how are you?",
        "I don't sleep, I don't eat, I don't complain. You though?",
    ]
    return random.choice(responses)


def stop_cancel(entities: dict = {}):
    cancel_timer()
    return random.choice([
        "Done. Gone.",
        "Cancelled. Moving on.",
        "Stopped. What's next?",
        "Consider it forgotten.",
    ])


# -------------------------
# WEATHER
# -------------------------

def get_weather(entities: dict = {}):
    city = entities.get("location") or entities.get("city") or DEFAULT_CITY

    if not OPENWEATHER_API_KEY:
        return "No weather API key found."

    try:
        degree_sign = "C"
        current_url = "https://api.openweathermap.org/data/2.5/weather"
        current_params = {
            "q"     : city,
            "appid" : OPENWEATHER_API_KEY,
            "units" : "metric"
        }

        current = requests.get(current_url, params=current_params, timeout=5)
        if current.status_code != 200:
            return f"Couldn't get weather for {city}."

        data        = current.json()
        temp        = round(data["main"]["temp"])
        feels_like  = round(data["main"]["feels_like"])
        humidity    = data["main"]["humidity"]
        description = data["weather"][0]["description"]

        forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
        forecast_params = {
            "q"     : city,
            "appid" : OPENWEATHER_API_KEY,
            "units" : "metric",
            "cnt"   : 8
        }

        forecast = requests.get(forecast_url, params=forecast_params, timeout=5)
        forecast_data = forecast.json()

        rain_expected = False
        if forecast.status_code == 200:
            for entry in forecast_data.get("list", []):
                condition = entry["weather"][0]["main"].lower()
                if "rain" in condition or "drizzle" in condition or "thunderstorm" in condition:
                    rain_expected = True
                    break

        rain_line = "Rain expected later — you might want an umbrella." if rain_expected else "No rain today."

        return (
            f"{city} right now — {temp}°{degree_sign}, {description}. "
            f"Feels like {feels_like}°{degree_sign}, humidity {humidity}%. "
            f"{rain_line}"
        )

    except Exception as e:
        return "Couldn't reach the weather service."


def send_message(entities: dict = {}):
    return "Messaging isn't set up yet. Coming soon."


# -------------------------
# Conversation history for
# multi-turn Mistral context
# -------------------------
_conversation_history = []


def ask_question(entities: dict = {}):
    import ollama
    global _conversation_history

    topic = (
        entities.get("topic", "")
        or entities.get("query", "")
        or entities.get("raw_text", "")
    )

    if not topic:
        return "What would you like to know?"

    memory_context   = entities.get("memory_context", [])
    semantic_context = entities.get("semantic_context", [])

    

    # Build semantic context string injected into system prompt
    semantic_note = ""
    if semantic_context:
        lines = []
        for turn in semantic_context:
            if turn["raw_text"] and turn["response"]:
                lines.append(
                    f"Past topic: {turn['raw_text']} → {turn['response'][:120]}"
                )
        if lines:
            semantic_note = "\n\nRelevant past conversations:\n" + "\n".join(lines)
    _conversation_history.append({
        "role"   : "user",
        "content": topic
    })

    messages = [
        {
            "role"   : "system",
            "content": (
                "You are Arcn, a sharp personal AI assistant with a dry wit and genuine personality. "
                "You're helpful, direct, occasionally funny, and never robotic. "
                "Answer concisely in plain conversational language — no markdown, no bullet points, no lists. "
                "Keep responses short unless depth is actually needed."
                + semantic_note
            )
        }
    ] + _conversation_history

    response = ollama.chat(
        model    = "mistral",
        messages = messages,
        keep_alive = "1m"
        
    )

    answer = response["message"]["content"]

    _conversation_history.append({
        "role"   : "assistant",
        "content": answer
    })

    if len(_conversation_history) > 20:
        _conversation_history = _conversation_history[-20:]

    return answer

# -------------------------
# Shared factory for simple
# Mistral-backed tools — vent,
# brainstorm, explain_code.
# Each gets its own isolated
# conversation history so they
# don't bleed into each other.
# ask_question stays separate —
# it has memory-injection logic
# this factory doesn't handle.
# -------------------------
def _make_mistral_tool(system_prompt: str):

    history = []

    def tool(entities: dict = {}):
        import ollama
        nonlocal history

        raw_text = entities.get("raw_text", "")
        if not raw_text:
            return "What's on your mind?"

        history.append({"role": "user", "content": raw_text})

        messages = [{"role": "system", "content": system_prompt}] + history

        response = ollama.chat(model="mistral", messages=messages, keep_alive="1m")
        answer = response["message"]["content"]

        history.append({"role": "assistant", "content": answer})

        if len(history) > 20:
            history[:] = history[-20:]

        return answer

    return tool


vent = _make_mistral_tool(
    "You are Arcn, and right now the user just needs to vent. "
    "Do not give advice, do not problem-solve, do not lecture. "
    "Just listen and respond with genuine, brief encouragement or validation — "
    "1-2 sentences, plain conversational language, no bullet points."
)

brainstorm = _make_mistral_tool(
    "You are Arcn, helping the user brainstorm ideas. "
    "Give 3-5 concrete, varied suggestions, plain conversational language, no bullet points. "
    "Ask a clarifying question if the request is too vague to give good ideas."
)

explain_code = _make_mistral_tool(
    "You are Arcn, explaining code to someone learning Python and software architecture "
    "by building this very assistant. Be clear and instructive, step-by-step where useful, "
    "plain conversational language. Assume intermediate familiarity, don't over-explain basics."
)

from time_parser import parse_reminder_time

def create_reminder(entities: dict = {}):
    from state import StateManager
    state = StateManager()

    topic = entities.get("topic", "") or state.get_pending_reminder()
    raw   = entities.get("raw_text", "")

    if not entities.get("relative_time") and state.get_pending_date():
        entities["relative_time"] = state.get_pending_date()

    reminder_dt, needs_clarification = parse_reminder_time(entities, raw)

    if needs_clarification:
        import re
        clean_topic = re.sub(
            r'\b(tomorrow|today|tonight|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            '', topic, flags=re.IGNORECASE
        ).strip(" .")
        state.set_pending_reminder(clean_topic)
        state.set_pending_date(entities.get("relative_time", ""))
        state.set_needs_followup(True)
        return "What time should I set that for?"

    state.clear_pending_reminder()
    state.clear_needs_followup()

    date_str = reminder_dt.strftime("%B %d, %Y %I:%M %p")

    script = f'''
    tell application "Reminders"
        set newReminder to make new reminder
        set name of newReminder to "{topic}"
        set due date of newReminder to date "{date_str}"
    end tell
    '''

    os.system(f"osascript -e '{script}'")
    return random.choice([
        f"Done — {topic} at {reminder_dt.strftime('%I:%M %p on %B %d')}.",
        f"Reminder set. {topic} at {reminder_dt.strftime('%I:%M %p')} on {reminder_dt.strftime('%B %d')}.",
    ])


# -------------------------
# TOOL REGISTRY
# expects_followup — True means assistant loop
# stays in conversation window after this response
# -------------------------

TOOLS = {

    # WEBSITES
    "open_youtube"      : {"function": open_youtube,       "confirmation": "Opening YouTube.",           "type": "website",     "expects_followup": False},
    "open_google"       : {"function": open_google,        "confirmation": "Opening Google.",            "type": "website",     "expects_followup": False},
    "open_chatgpt"      : {"function": open_chatgpt,       "confirmation": "Opening ChatGPT.",           "type": "website",     "expects_followup": False},

    # APPS
    "open_terminal"     : {"function": open_terminal,      "confirmation": "Opening Terminal.",          "type": "app",         "expects_followup": False},
    "open_notes"        : {"function": open_notes,         "confirmation": "Opening Notes.",             "type": "app",         "expects_followup": False},
    "open_finder"       : {"function": open_finder,        "confirmation": "Opening Finder.",            "type": "app",         "expects_followup": False},
    "open_settings"     : {"function": open_settings,      "confirmation": "Opening Settings.",          "type": "app",         "expects_followup": False},
    "open_vscode"       : {"function": open_vscode,        "confirmation": "Opening VS Code.",           "type": "app",         "expects_followup": False},
    "open_spotify"      : {"function": open_spotify,       "confirmation": "Opening Spotify.",           "type": "app",         "expects_followup": False},

    # CONTROLS
    "close_app"         : {"function": close_app,          "confirmation": "Closed.",                    "type": "control",     "expects_followup": False},
    "system_volume_up"  : {"function": increase_volume,    "confirmation": "Volume up.",                 "type": "control",     "expects_followup": False},
    "system_volume_down": {"function": decrease_volume,    "confirmation": "Volume down.",               "type": "control",     "expects_followup": False},
    "mute_volume"       : {"function": mute_volume,        "confirmation": "Muted.",                     "type": "control",     "expects_followup": False},
    "lock_mac"          : {"function": lock_mac,           "confirmation": "Locking.",                   "type": "control",     "expects_followup": False},
    "system_brightness_up"  : {"function": increase_brightness, "confirmation": "Brightness up.",        "type": "control",     "expects_followup": False},
    "system_brightness_down": {"function": decrease_brightness, "confirmation": "Brightness down.",      "type": "control",     "expects_followup": False},

    # SEARCHES
    "search_google"     : {"function": search_google,      "confirmation": "Searching Google.",          "type": "search",      "expects_followup": False},
    "search_youtube"    : {"function": search_youtube,     "confirmation": "Searching YouTube.",         "type": "search",      "expects_followup": False},

    # TIMER
    "set_timer"         : {"function": set_timer,          "confirmation": "Timer started.",             "type": "timer",       "expects_followup": False},
    "cancel_timer"      : {"function": cancel_timer,       "confirmation": "Timer cancelled.",           "type": "timer",       "expects_followup": False},

    # TIME + DATE
    "tell_time"         : {"function": tell_time,          "confirmation": "Checking time.",             "type": "info",        "expects_followup": False},
    "tell_date"         : {"function": tell_date,          "confirmation": "Checking date.",             "type": "info",        "expects_followup": False},

    # NOTES
    "take_note"         : {"function": take_note,          "confirmation": "Note saved.",                "type": "note",        "expects_followup": True},
    "export_note_mac"   : {"function": export_note_mac,   "confirmation": "",                           "type": "note",        "expects_followup": False},
    "read_note"         : {"function": read_note,          "confirmation": "",                           "type": "note",        "expects_followup": False},
    "edit_note"         : {"function": edit_note,           "confirmation": "",                           "type": "note",        "expects_followup": False},
    "delete_note"       : {"function": delete_note,         "confirmation": "",                           "type": "note",        "expects_followup": True},
    # PERSONALITY
    "greet"             : {"function": greet,              "confirmation": "",                           "type": "personality", "expects_followup": False},
    "how_are_you"       : {"function": how_are_you,        "confirmation": "",                           "type": "personality", "expects_followup": False},
    "stop_cancel"       : {"function": stop_cancel,        "confirmation": "Cancelled.",                 "type": "control",     "expects_followup": False},

    # MODES
    "developer_mode"    : {"function": developer_mode,     "confirmation": "Developer mode.",            "type": "mode",        "expects_followup": False},
    "study_mode"        : {"function": study_mode,         "confirmation": "Study mode.",                "type": "mode",        "expects_followup": False},

    # MEDIA / WIP
    "play_music"        : {"function": play_music,         "confirmation": "Playing.",                   "type": "media",       "expects_followup": False},
    "pause_music"       : {"function": pause_music,        "confirmation": "Paused.",                    "type": "media",       "expects_followup": False},
    "skip_song"         : {"function": skip_song,          "confirmation": "Skipped.",                   "type": "media",       "expects_followup": False},
    "get_weather"       : {"function": get_weather,        "confirmation": "",                           "type": "info",        "expects_followup": False},
    "send_message"      : {"function": send_message,       "confirmation": "",                           "type": "message",     "expects_followup": False},
    "ask_question"      : {"function": ask_question,       "confirmation": "",                           "type": "knowledge",   "expects_followup": True},
    "create_reminder"   : {"function": create_reminder,    "confirmation": "",                           "type": "reminder",    "expects_followup": False},
    "vent"               : {"function": vent,               "confirmation": "",                           "type": "knowledge",   "expects_followup": True},
    "brainstorm"         : {"function": brainstorm,         "confirmation": "",                           "type": "knowledge",   "expects_followup": True},
    "explain_code"       : {"function": explain_code,       "confirmation": "",                           "type": "knowledge",   "expects_followup": True},

}