from html import entities
import os
import urllib.parse
import threading
import datetime
from dotenv import load_dotenv
import requests

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
DEFAULT_CITY = "Chennai"

# -------------------------
# Music tools
# -------------------------
def play_music(entities: dict = {}):
    os.system("open -a Spotify")
    os.system("osascript -e 'tell application \"Spotify\" to play'")
    return "Playing music"

def pause_music(entities: dict = {}):
    os.system("osascript -e 'tell application \"Spotify\" to playpause'")
    return "Paused"

def skip_song(entities: dict = {}):
    os.system("osascript -e 'tell application \"Spotify\" to next track'")
    return "Skipped"

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

def open_google(entities: dict = {}):
    os.system("open -a 'Google Chrome'")

def open_chatgpt(entities: dict = {}):
    os.system("open -a 'Google Chrome' 'https://chatgpt.com'")

def open_spotify(entities: dict = {}):
    os.system("open -a Spotify")


# -------------------------
# APP TOOLS
# -------------------------

def open_terminal(entities: dict = {}):
    os.system("open -a Terminal")

def open_notes(entities: dict = {}):
    os.system("open -a Notes")

def open_finder(entities: dict = {}):
    os.system("open -a Finder")

def open_settings(entities: dict = {}):
    os.system("open -a 'System Settings'")

def open_vscode(entities: dict = {}):
    os.system("open -a 'Visual Studio Code'")


# -------------------------
# CONTROL TOOLS
# -------------------------

def close_app(entities: dict = {}):
    os.system(
        "osascript -e 'tell application \"System Events\" to keystroke \"q\" using command down'"
    )

def increase_volume(entities: dict = {}):
    os.system(
        "osascript -e \"set volume output volume ((output volume of (get volume settings)) + 10)\""
    )

def decrease_volume(entities: dict = {}):
    os.system(
        "osascript -e \"set volume output volume ((output volume of (get volume settings)) - 10)\""
    )

def mute_volume(entities: dict = {}):
    os.system(
        "osascript -e \"set volume with output muted\""
    )

def lock_mac(entities: dict = {}):
    os.system("osascript -e 'tell application \"System Events\" to keystroke \"q\" using {control down, command down}'")
    return "Locking Mac."

def increase_brightness(entities: dict = {}):
    os.system(
        "osascript -e 'tell application \"System Events\" to key code 144'"
    )

def decrease_brightness(entities: dict = {}):
    os.system(
        "osascript -e 'tell application \"System Events\" to key code 145'"
    )


# -------------------------
# SEARCH TOOLS
# -------------------------

def search_youtube(entities: dict = {}):
    query = entities.get("query", "")
    encoded = urllib.parse.quote(query)
    os.system(
        f"open -a 'Google Chrome' 'https://www.youtube.com/results?search_query={encoded}'"
    )

def search_google(entities: dict = {}):
    query = entities.get("query", "")
    encoded = urllib.parse.quote(query)
    os.system(
        f"open -a 'Google Chrome' 'https://www.google.com/search?q={encoded}'"
    )


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
        print("TIMER: Couldn't parse duration")
        return

    # Cancel any existing timer
    _timer_cancel.set()
    _timer_cancel = threading.Event()

    def countdown():
        print(f"TIMER: Started for {seconds} seconds")
        cancelled = _timer_cancel.wait(timeout=seconds)
        if not cancelled:
            print("TIMER: Time is up!")
            os.system("osascript -e 'display notification \"Timer is up!\" with title \"Arcn\"'")

    _timer_thread = threading.Thread(target=countdown, daemon=True)
    _timer_thread.start()


def cancel_timer(entities: dict = {}):
    global _timer_cancel
    _timer_cancel.set()
    print("TIMER: Cancelled")


# -------------------------
# TIME + DATE
# -------------------------

def tell_time(entities: dict = {}):
    now = datetime.datetime.now()
    time_str = now.strftime("%I:%M %p")
    print(f"TIME: {time_str}")
    return time_str

def tell_date(entities: dict = {}):
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %B %d %Y")
    print(f"DATE: {date_str}")
    return date_str


# -------------------------
# NOTES
# -------------------------

def take_note(entities: dict = {}):
    topic = entities.get("topic", "")
    if not topic:
        return "What would you like me to note?"

    # Escape single quotes in topic so osascript doesn't break
    safe_topic = topic.replace("'", "\\'")

    script = f"""
    tell application "Notes"
        make new note at folder "Notes" with properties {{body:"{safe_topic}"}}
    end tell
    """

    os.system(f"osascript -e '{script}' > /dev/null 2>&1")
    return f"Note saved — {topic}"

# -------------------------
# GREET + PERSONALITY
# -------------------------

def greet(entities: dict = {}):
    hour = datetime.datetime.now().hour
    if hour < 12:
        return "Good morning."
    elif hour < 17:
        return "Good afternoon."
    else:
        return "Good evening."

def how_are_you(entities: dict = {}):
    return "All systems running. How can I help?"

def stop_cancel(entities: dict = {}):
    cancel_timer()
    return "Understood, cancelling."


# -------------------------
# MODES
# -------------------------

def developer_mode(entities: dict = {}):
    os.system("open -a 'Visual Studio Code'")
    os.system("open -a Terminal")

def study_mode(entities: dict = {}):
    os.system("open -a Notes")
    os.system("open -a 'Google Chrome'")


# -------------------------
# PLACEHOLDERS
# (real implementations coming)
# -------------------------





def get_weather(entities: dict = {}):
    city = entities.get("location", DEFAULT_CITY)
    unit = entities.get("unit", "imperial")  # imperial = F, metric = C

    if not OPENWEATHER_API_KEY:
        return "Weather API key is missing."

    try:
        # Current weather
        current_url = "https://api.openweathermap.org/data/2.5/weather"
        current_params = {
            "q"     : city,
            "appid" : OPENWEATHER_API_KEY,
            "units" : unit
        }

        current = requests.get(current_url, params=current_params, timeout=5)
        current_data = current.json()

        if current.status_code != 200:
            return f"Couldn't get weather for {city}."

        temp        = round(current_data["main"]["temp"])
        feels_like  = round(current_data["main"]["feels_like"])
        humidity    = current_data["main"]["humidity"]
        description = current_data["weather"][0]["description"]
        unit_label  = "Fahrenheit" if unit == "imperial" else "Celsius"
        degree_sign = "F" if unit == "imperial" else "C"

        # Forecast — check for rain today
        forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
        forecast_params = {
            "q"     : city,
            "appid" : OPENWEATHER_API_KEY,
            "units" : unit,
            "cnt"   : 8  # next 24 hours in 3hr blocks
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

        rain_line = "Rain is expected later today." if rain_expected else "No rain expected today."

        response = (
            f"Currently in {city}, it's {temp}°{degree_sign} "
            f"with {description}. "
            f"Feels like {feels_like}°{degree_sign}, humidity at {humidity}%. "
            f"{rain_line}"
        )

        #print(f"ARCN: {response}")
        return response

    except Exception as e:
        print(f"ARCN: Weather fetch failed — {e}")
        return "Couldn't reach the weather service."

def send_message(entities: dict = {}):
    print("ARCN: Messaging coming soon.")

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

    # Recent turns from SQLite
    memory_context   = entities.get("memory_context", [])

    # Semantically similar turns from ChromaDB
    semantic_context = entities.get("semantic_context", [])

    # Seed _conversation_history on fresh boot
    # from SQLite recent turns if history is empty
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

    # Build semantic context string from ChromaDB results
    # injected into the system prompt so Mistral knows
    # what relevant topics were discussed in the past
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

    # Add current user message to in-session history
    _conversation_history.append({
        "role"   : "user",
        "content": topic
    })

    # Build full message list with system prompt
    # semantic_note appended to system prompt so Mistral
    # has long-term context without cluttering the history
    messages = [
        {
            "role"   : "system",
            "content": (
                "You are Arcn, a helpful personal AI assistant. "
                "Answer concisely and clearly. "
                "No markdown, no bullet points, just plain conversational responses."
                + semantic_note
            )
        }
    ] + _conversation_history

    response = ollama.chat(
        model    = "mistral",
        messages = messages
    )

    answer = response["message"]["content"]

    # Add response to in-session history
    _conversation_history.append({
        "role"   : "assistant",
        "content": answer
    })

    # Keep history to last 20 entries
    if len(_conversation_history) > 20:
        _conversation_history = _conversation_history[-20:]

    return answer

from time_parser import parse_reminder_time

def create_reminder(entities: dict = {}):
    from state import StateManager
    state = StateManager()

    topic = entities.get("topic", "") or state.get_pending_reminder()
    raw   = entities.get("raw_text", "")

    # Restore pending date if not in current entities
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
        # Save date context too
        state.set_pending_date(entities.get("relative_time", ""))
        return "What time should I set the reminder for?"

    # Clear pending once we have everything
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
    return f"Reminder set — {topic} at {reminder_dt.strftime('%I:%M %p on %B %d')}."


# -------------------------
# TOOL REGISTRY
# -------------------------

TOOLS = {

    # WEBSITES
    "open_youtube"      : {"function": open_youtube,       "confirmation": "Opening YouTube",            "type": "website"},
    "open_google"       : {"function": open_google,        "confirmation": "Opening Google",             "type": "website"},
    "open_chatgpt"      : {"function": open_chatgpt,       "confirmation": "Opening ChatGPT",            "type": "website"},

    # APPS
    "open_terminal"     : {"function": open_terminal,      "confirmation": "Opening Terminal",           "type": "app"},
    "open_notes"        : {"function": open_notes,         "confirmation": "Opening Notes",              "type": "app"},
    "open_finder"       : {"function": open_finder,        "confirmation": "Opening Finder",             "type": "app"},
    "open_settings"     : {"function": open_settings,      "confirmation": "Opening Settings",           "type": "app"},
    "open_vscode"       : {"function": open_vscode,        "confirmation": "Opening VS Code",            "type": "app"},
    "open_spotify"      : {"function": open_spotify,       "confirmation": "Opening Spotify",            "type": "app"},

    # CONTROLS
    "close_app"         : {"function": close_app,          "confirmation": "Closing current app",        "type": "control"},
    "system_volume_up"  : {"function": increase_volume,    "confirmation": "Increasing volume",          "type": "control"},
    "system_volume_down": {"function": decrease_volume,    "confirmation": "Decreasing volume",          "type": "control"},
    "mute_volume"       : {"function": mute_volume,        "confirmation": "Muting volume",              "type": "control"},
    "lock_mac"          : {"function": lock_mac,           "confirmation": "Locking Mac",                "type": "control"},
    "system_brightness_up"  : {"function": increase_brightness, "confirmation": "Increasing brightness", "type": "control"},
    "system_brightness_down": {"function": decrease_brightness, "confirmation": "Decreasing brightness", "type": "control"},

    # SEARCHES
    "search_google"     : {"function": search_google,      "confirmation": "Searching Google",           "type": "search"},
    "search_youtube"    : {"function": search_youtube,     "confirmation": "Searching YouTube",          "type": "search"},

    # TIMER
    "set_timer"         : {"function": set_timer,          "confirmation": "Timer started",              "type": "timer"},
    "cancel_timer"      : {"function": cancel_timer,       "confirmation": "Timer cancelled",            "type": "timer"},

    # TIME + DATE
    "tell_time"         : {"function": tell_time,          "confirmation": "Checking time",              "type": "info"},
    "tell_date"         : {"function": tell_date,          "confirmation": "Checking date",              "type": "info"},

    # NOTES
    "take_note"         : {"function": take_note,          "confirmation": "Note saved",                 "type": "note"},

    # PERSONALITY
    "greet"             : {"function": greet,              "confirmation": "",                           "type": "personality"},
    "how_are_you"       : {"function": how_are_you,        "confirmation": "",                           "type": "personality"},
    "stop_cancel"       : {"function": stop_cancel,        "confirmation": "Cancelled",                  "type": "control"},

    # MODES
    "developer_mode"    : {"function": developer_mode,     "confirmation": "Entering developer workspace", "type": "mode"},
    "study_mode"        : {"function": study_mode,         "confirmation": "Entering study mode",        "type": "mode"},

    # Misallaneous / WIP / 
    "play_music"        : {"function": play_music,         "confirmation": "",                           "type": "media"},
    "pause_music"       : {"function": pause_music,        "confirmation": "",                           "type": "media"},
    "skip_song"         : {"function": skip_song,          "confirmation": "",                           "type": "media"},
    "get_weather"       : {"function": get_weather,        "confirmation": "",                           "type": "info"},
    "send_message"      : {"function": send_message,       "confirmation": "",                           "type": "message"},
    "ask_question"      : {"function": ask_question,       "confirmation": "",                           "type": "knowledge"},
    "create_reminder"   : {"function": create_reminder,    "confirmation": "",                           "type": "reminder"},
}