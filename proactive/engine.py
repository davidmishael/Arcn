import time
import subprocess
import datetime
import threading
import psutil

# _speak imported as alias — same pattern as registry.py
from speaker import speak as _speak

# -------------------------
# Cooldown tracker
# Prevents the same alert firing repeatedly.
# Key: alert name (string)
# Value: timestamp of last fire (float)
# -------------------------
_last_fired = {}
_lock = threading.Lock()

# -------------------------
# State reference — injected
# from main.py via start().
# Engine only speaks when
# assistant is idle.
# -------------------------
_state_ref = None


def _cooldown_ok(key: str, seconds: int) -> bool:
    """Returns True if enough time has passed since this alert last fired."""
    with _lock:
        last = _last_fired.get(key, 0)
        if time.time() - last >= seconds:
            _last_fired[key] = time.time()
            return True
        return False


def _safe_speak(text: str):
    """
    Only speaks if the assistant is idle.
    If assistant is listening, processing, or speaking —
    wait until it returns to idle, then speak.
    Timeout after 30s to prevent infinite blocking.
    """
    if _state_ref is None:
        _speak(text)
        return

    deadline = time.time() + 30  # max wait 30s

    while time.time() < deadline:
        if _state_ref.get() == "idle":
            _speak(text)
            return
        time.sleep(0.5)  # check every 0.5s

    # timed out — assistant never returned to idle, skip this alert
    print(f"[proactive] skipped (assistant busy): {text[:50]}")


# -------------------------
# 1. CPU HOG ALERT
# Polls every 60s. Speaks if any process holds >80% CPU
# on two consecutive checks (avoids brief spike false positives).
# Cooldown: 5 min per offending process name.
# -------------------------
_cpu_previous_offenders = set()  # processes that were high last check

def _check_cpu():
    global _cpu_previous_offenders
    current_offenders = set()

    for proc in psutil.process_iter(["name", "cpu_percent"]):
        try:
            if proc.info["cpu_percent"] is not None and proc.info["cpu_percent"] > 80:
                current_offenders.add(proc.info["name"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Only alert if process was high LAST check too (two consecutive)
    persistent = current_offenders & _cpu_previous_offenders
    for name in persistent:
        key = f"cpu_{name}"
        if _cooldown_ok(key, 300):  # 5 min cooldown per process
            _safe_speak(f"{name} has been pegging the CPU. You might want to check that.")

    _cpu_previous_offenders = current_offenders


# -------------------------
# 2. RAM PRESSURE ALERT
# Speaks if available RAM drops below 1GB.
# Cooldown: 10 min.
# -------------------------
def _check_ram():
    available_gb = psutil.virtual_memory().available / (1024 ** 3)
    if available_gb < 1.0:
        if _cooldown_ok("ram", 600):  # 10 min cooldown
            _safe_speak(f"RAM's running low — only {available_gb:.1f} GB free. Might be worth closing something.")


# -------------------------
# 3. BATTERY WARNING
# Uses pmset — macOS native, no extra deps.
# Two thresholds: 20% and 10%.
# Cooldown: 15 min per threshold (so both can fire independently).
# Skips if charging.
# -------------------------
def _check_battery():
    try:
        result = subprocess.run(
            ["pmset", "-g", "batt"],
            capture_output=True, text=True, timeout=3
        )
        output = result.stdout

        # Skip if charging
        if "AC Power" in output or "charging" in output.lower():
            return

        # Extract percentage — pmset outputs something like "72%; discharging"
        import re
        match = re.search(r"(\d+)%", output)
        if not match:
            return

        pct = int(match.group(1))

        if pct <= 10 and _cooldown_ok("battery_10", 900):
            _safe_speak(f"Battery at {pct}%. Plug in soon.")
        elif pct <= 20 and _cooldown_ok("battery_20", 900):
            _safe_speak(f"Battery at {pct}%. Worth plugging in.")

    except Exception:
        pass  # pmset failure is silent — not worth alerting


# -------------------------
# 4. WATER REMINDER
# Fires every 45 minutes during active hours (8am–11pm).
# No cooldown needed — the interval IS the timer.
# -------------------------
_last_water = 0.0

def _check_water():
    global _last_water
    now = datetime.datetime.now()
    hour = now.hour

    # Only during active hours
    if not (8 <= hour < 23):
        return

    elapsed = time.time() - _last_water
    if elapsed >= 2700:  # 45 min = 2700s
        _last_water = time.time()
        _safe_speak("Drink some water.")


# -------------------------
# 5. MORNING BRIEFING
# Fires once per day between 6am and 12pm on first boot.
# Calls get_weather() internally for live data.
# -------------------------
# NEW — persists across restarts
def _check_morning_briefing():
    import db
    now = datetime.datetime.now()

    if not (6 <= now.hour < 12):
        return

    today = str(now.date())
    if db.get_briefing_date() == today:
        return

    db.set_briefing_date(today)

    time_str = now.strftime("%I:%M %p").lstrip("0")

    try:
        from registry import get_weather
        weather = get_weather({})
    except Exception:
        weather = None

    if weather:
        _safe_speak(f"Good morning. It's {time_str}. {weather}")
    else:
        _safe_speak(f"Good morning. It's {time_str}.")


# -------------------------
# MAIN LOOP
# Single daemon thread, runs all checks on their own cadence.
# CPU + RAM + battery + water + briefing checked every 60s.
# Each check self-gates via cooldowns or date tracking.
# -------------------------
def _engine_loop():
    # Boot delay — let assistant finish booting and speaking "Arcn online"
    time.sleep(20)

    # Water: set _last_water to now so first reminder fires 45min from boot
    global _last_water
    _last_water = time.time()

    while True:
        try:
            _check_cpu()
            _check_ram()
            _check_battery()
            _check_water()
            _check_morning_briefing()
        except Exception as e:
            # Proactive engine must never crash the assistant
            print(f"[proactive] error: {e}")

        time.sleep(60)  # poll every 60 seconds


def start(state=None):
    """
    Call this from main.py after pywebview starts.
    Pass the AssistantState object so the engine
    can gate on it before speaking.
    """
    global _state_ref
    _state_ref = state

    t = threading.Thread(target=_engine_loop, daemon=True)
    t.name = "proactive-engine"
    t.start()