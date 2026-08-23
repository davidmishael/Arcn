import subprocess
import threading
import time


# -------------------------
# Config
# -------------------------
ARCN_SPEAKER_MAC   = "48-d6-d5-f4-11-43"
ARCN_SPEAKER_NAME  = "ARCN speaker"
MAC_SPEAKERS_NAME  = "MacBook Pro Speakers"

CHECK_INTERVAL_SECONDS = 30

# -------------------------
# Tracks consecutive "Bluetooth off" cycles so we don't spam
# the same log line every 30s — only logs on the transition
# into the off state, not every check while it stays off.
# -------------------------
_bluetooth_was_off = False

# -------------------------
# Bluetooth power check —
# If Bluetooth itself is off, there's no radio to talk to at all.
# Checking this first avoids blueutil --connect hanging until timeout
# on every single cycle when Bluetooth is deliberately turned off.
# -------------------------
def _bluetooth_is_powered_on() -> bool:
    try:
        result = subprocess.run(
            ["blueutil", "--power"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() == "1"
    except Exception:
        return False  # assume off if we can't tell — avoids hanging elsewhere



# -------------------------
# Reconnect check —
# Uses blueutil to see if ARCN speaker is currently connected.
# If not, issues a connect attempt. blueutil fails fast and
# silently if the device isn't reachable — safe to call repeatedly.
# -------------------------
def _try_reconnect_speaker():
    global _bluetooth_was_off

    if not _bluetooth_is_powered_on():
        if not _bluetooth_was_off:
            print("[bt_watcher] Bluetooth is off — pausing reconnect attempts until it's back on.")
            _bluetooth_was_off = True
        return

    if _bluetooth_was_off:
        print("[bt_watcher] Bluetooth is back on — resuming reconnect checks.")
        _bluetooth_was_off = False

    try:
        result = subprocess.run(
            ["blueutil", "--is-connected", ARCN_SPEAKER_MAC],
            capture_output=True, text=True, timeout=5
        )
        is_connected = result.stdout.strip() == "1"

        if not is_connected:
            print("[bt_watcher] ARCN speaker not connected — attempting reconnect...")
            connect_result = subprocess.run(
                ["blueutil", "--connect", ARCN_SPEAKER_MAC],
                capture_output=True, text=True, timeout=10
            )
            if connect_result.returncode == 0:
                print("[bt_watcher] Reconnect attempt sent successfully.")
            else:
                print(f"[bt_watcher] Reconnect failed: {connect_result.stderr.strip()}")

    except subprocess.TimeoutExpired:
        print("[bt_watcher] blueutil call timed out.")
    except FileNotFoundError:
        print("[bt_watcher] blueutil not found — is it installed via brew?")
    except Exception as e:
        print(f"[bt_watcher] reconnect check error: {e}")


# -------------------------
# System default output check —
# If macOS silently switched the system-wide default output to
# ARCN speaker (which it does automatically on Bluetooth connect),
# revert it back to Mac speakers. Arcn's own audio ignores the
# system default entirely (speaker.py targets by device name), so
# this only affects everything ELSE on the Mac — YouTube, Spotify, etc.
# Requires switchaudio-osx (`brew install switchaudio-osx`).
# -------------------------
def _revert_system_default_if_needed():
    try:
        result = subprocess.run(
            ["SwitchAudioSource", "-c"],
            capture_output=True, text=True, timeout=5
        )
        current_default = result.stdout.strip()

        if current_default == ARCN_SPEAKER_NAME:
            print("[bt_watcher] System default output was switched to ARCN speaker — reverting.")
            subprocess.run(
                ["SwitchAudioSource", "-s", MAC_SPEAKERS_NAME],
                capture_output=True, text=True, timeout=5
            )

    except subprocess.TimeoutExpired:
        print("[bt_watcher] SwitchAudioSource call timed out.")
    except FileNotFoundError:
        print("[bt_watcher] SwitchAudioSource not found — is switchaudio-osx installed via brew?")
    except Exception as e:
        print(f"[bt_watcher] default-output check error: {e}")


# -------------------------
# Main loop
# -------------------------
def _watcher_loop():
    # Small boot delay — let the system settle after Arcn starts
    time.sleep(10)

    while True:
        try:
            _try_reconnect_speaker()
            _revert_system_default_if_needed()
        except Exception as e:
            # Watcher must never crash Arcn — same pattern as proactive/engine.py
            print(f"[bt_watcher] error: {e}")

        time.sleep(CHECK_INTERVAL_SECONDS)


def start():
    """Call this from main.py, same pattern as proactive_engine.start()."""
    t = threading.Thread(target=_watcher_loop, daemon=True)
    t.name = "bt-watcher"
    t.start()
    print("[bt_watcher] started")