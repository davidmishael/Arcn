import os
import urllib.parse
import threading
import datetime
from dotenv import load_dotenv
import requests
import random
from speaker import speak as _speak

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
DEFAULT_CITY = "Chennai"


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

    if any(u in unit for u in ["s", "sec"]):
        return amount
    elif any(u in unit for u in ["m", "min"]):
        return amount * 60
    elif any(u in unit for u in ["h", "hr", "hour"]):
        return amount * 3600

    return 0


def set_timer(entities: dict = {}):
    global _timer_thread, _timer_cancel

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
    topic = entities.get("topic", "")
    if not topic:
        return "What would you like me to note?"

    # Escape single quotes so osascript doesn't break
    safe_topic = topic.replace("'", "\\'")

    script = f"""
    tell application "Notes"
        make new note at folder "Notes" with properties {{body:"{safe_topic}"}}
    end tell
    """

    os.system(f"osascript -e '{script}' > /dev/null 2>&1")
    return random.choice([
        f"Noted — {topic}.",
        f"Got it. Saved to Notes.",
        f"Saved — {topic}.",
    ])


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
    city = entities.get("city") or DEFAULT_CITY

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

    # Seed conversation history on fresh boot from SQLite
    if not _conversation_history and memory_context:
        for turn in memory_context:
            if turn["intent"] == "ask_question" and turn["raw_text"]:
                _conversation_history.append({
                    "role"   : "user",
                    "content": turn["raw_text"]
                })
                if turn["response"]:
                    _conversation_history.append({
                        "role"   : "assistant",
                        "content": turn["response"]
                    })

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
        messages = messages
    )

    answer = response["message"]["content"]

    _conversation_history.append({
        "role"   : "assistant",
        "content": answer
    })

    if len(_conversation_history) > 20:
        _conversation_history = _conversation_history[-20:]

    return answer


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
        return "What time should I set that for?"

    state.clear_pending_reminder()

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

    # PERSONALITY
    "greet"             : {"function": greet,              "confirmation": "",                           "type": "personality", "expects_followup": False},
    "how_are_you"       : {"function": how_are_you,        "confirmation": "",                           "type": "personality", "expects_followup": True},
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
}