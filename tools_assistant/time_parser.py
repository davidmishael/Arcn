import datetime
import re


# -------------------------
# Vague time defaults
# -------------------------
VAGUE_TIMES = {
    "morning"   : (9, 0),
    "afternoon" : (14, 0),
    "evening"   : (19, 0),
    "night"     : (21, 0),
    "noon"      : (12, 0),
    "midnight"  : (0, 0)
}


# -------------------------
# Day name → offset from today
# -------------------------
DAY_NAMES = {
    "monday"    : 0,
    "tuesday"   : 1,
    "wednesday" : 2,
    "thursday"  : 3,
    "friday"    : 4,
    "saturday"  : 5,
    "sunday"    : 6
}

WORD_TO_NUM = {
    "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8",
    "nine": "9", "ten": "10", "eleven": "11", "twelve": "12"
}

def _normalize_text(text: str) -> str:
    for word, num in WORD_TO_NUM.items():
        text = re.sub(rf'\b{word}\b', num, text)
    return text

# -------------------------
# Parse exact time string
# e.g. "6pm", "8:30am", "14:00"
# -------------------------
def _parse_exact_time(time_str: str):
    time_str = time_str.strip().lower()
    # Normalize "6 p.m." → "6pm", "8 a.m." → "8am"
    time_str = re.sub(r'\s*p\.m\.', 'pm', time_str)
    time_str = re.sub(r'\s*a\.m\.', 'am', time_str)
    time_str = re.sub(r'\s*p\.m', 'pm', time_str)
    time_str = re.sub(r'\s*a\.m', 'am', time_str)


    # "6pm", "8am"
    match = re.match(r'^(\d{1,2})(am|pm)$', time_str)
    if match:
        hour = int(match.group(1))
        period = match.group(2)
        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0
        return datetime.time(hour, 0)
    # "632pm", "1230am" — no separator
    match = re.match(r'^(\d{1,2})(\d{2})(am|pm)$', time_str)
    if match:
        hour   = int(match.group(1))
        minute = int(match.group(2))
        period = match.group(3)
        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0
        return datetime.time(hour, minute)

    # "8:30am", "6:45pm"
    match = re.match(r'^(\d{1,2}):(\d{2})(am|pm)$', time_str)
    if match:
        hour   = int(match.group(1))
        minute = int(match.group(2))
        period = match.group(3)
        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0
        return datetime.time(hour, minute)

    # "14:00" 24hr
    match = re.match(r'^(\d{1,2}):(\d{2})$', time_str)
    if match:
        return datetime.time(int(match.group(1)), int(match.group(2)))

    return None


# -------------------------
# Parse relative time
# e.g. "in 30 minutes", "in 2 hours"
# -------------------------
def _parse_relative(text: str):
    text = text.lower()

    match = re.search(
        r'in\s+(\d+)\s*(s|sec|secs|seconds?|m|min|mins|minutes?|h|hr|hrs|hours?)',
        text
    )
    if match:
        amount = int(match.group(1))
        unit   = match.group(2)
        now    = datetime.datetime.now()

        if any(u in unit for u in ["s", "sec"]):
            return now + datetime.timedelta(seconds=amount)
        elif any(u in unit for u in ["m", "min"]):
            return now + datetime.timedelta(minutes=amount)
        elif any(u in unit for u in ["h", "hr", "hour"]):
            return now + datetime.timedelta(hours=amount)

    return None


# -------------------------
# Resolve date from entities
# -------------------------
def _resolve_date(entities: dict):
    today    = datetime.date.today()
    relative = entities.get("relative_time", "").lower()
    date_ent = entities.get("date", "").lower()

    # "tomorrow"
    if "tomorrow" in relative or "tomorrow" in date_ent:
        return today + datetime.timedelta(days=1)

    # Named day — next occurrence
    for day_name, day_num in DAY_NAMES.items():
        if day_name in relative or day_name in date_ent:
            days_ahead = (day_num - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return today + datetime.timedelta(days=days_ahead)

    # Default to today
    return today


# -------------------------
# Main parse function
# Returns datetime or None
# Also returns needs_clarification flag
# -------------------------
def parse_reminder_time(entities: dict, raw_text: str):
    raw_text = raw_text.strip(" .")
    raw_text = _normalize_text(raw_text.lower())
    raw_text = re.sub(r'\s*p\.m\.?', 'pm', raw_text)
    raw_text = re.sub(r'\s*a\.m\.?', 'am', raw_text)
    raw_text = re.sub(r'\b(\d{1,2})\s+(\d{2})\s*(am|pm)', r'\1:\2\3', raw_text)
    # Normalize "6.32pm" → "6:32pm"
    raw_text = re.sub(r'\b(\d{1,2})\.(\d{2})\s*(am|pm)', r'\1:\2\3', raw_text)

    if "time" in entities:
        entities["time"] = entities["time"].strip(" .")
        entities["time"] = re.sub(r'\s*p\.m\.?', 'pm', entities["time"])
        entities["time"] = re.sub(r'\s*a\.m\.?', 'am', entities["time"])
        entities["time"] = re.sub(r'\b(\d{1,2})\s+(\d{2})\s*(am|pm)', r'\1:\2\3', entities["time"])
        entities["time"] = _normalize_text(entities["time"].lower())
        entities["time"] = re.sub(r'\b(\d{1,2})\.(\d{2})\s*(am|pm)', r'\1:\2\3', entities["time"])

    # Case 0 — raw_text itself might just be a time ("6pm", "6 p.m.")
    direct = _parse_exact_time(raw_text.strip())
    if direct:
        
        date = _resolve_date(entities)
        return datetime.datetime.combine(date, direct), False 

    # Case 1 — relative time ("in 30 minutes")
    relative_dt = _parse_relative(raw_text)
    if relative_dt:
        return relative_dt, False

    # Case 2 — exact time given
    time_str = entities.get("time", "")
    if time_str:
        parsed_time = _parse_exact_time(time_str)
        if parsed_time:
            date = _resolve_date(entities)
            return datetime.datetime.combine(date, parsed_time), False

    # Case 3 — vague time ("morning", "evening")
    relative = entities.get("relative_time", "").lower()
    for word, (hour, minute) in VAGUE_TIMES.items():
        if word in relative or word in raw_text.lower():
            # We have a vague time — prompt for exact
            return None, True

    # Case 4 — no time at all — prompt
    return None, True