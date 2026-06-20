import sys
import os
import time
import threading

ROOT = os.path.dirname(os.path.abspath(__file__))

sys.path.append(os.path.join(ROOT, "nlp"))
sys.path.append(os.path.join(ROOT, "nlp", "models"))
sys.path.append(os.path.join(ROOT, "nlp", "utils"))
sys.path.append(os.path.join(ROOT, "command_center"))
sys.path.append(os.path.join(ROOT, "tools_assistant"))
sys.path.append(os.path.join(ROOT, "speech"))
sys.path.append(os.path.join(ROOT, "memory"))
sys.path.append(os.path.join(ROOT, "proactive"))  # proactive engine on path

import webview
from pynput import keyboard

from pipeline import NLPBrain
from core import CommandCenter
from registry import TOOLS
from speaker import speak
from listener import listen
from wake_word import load_wake_word_model, wait_for_wake_word
from ui.window_manager import create_window
from ui.state_server import set_last_intent, start as start_state_server, set_state_source, set_last_response, set_icon_path
import engine as proactive_engine  # proactive engine

# -------------------------
# Shared state
# -------------------------
sys.path.append(os.path.join(ROOT, "ui"))

# We need AssistantState — define it here since menu_bar.py no longer has rumps
class AssistantState:
    def __init__(self):
        import threading
        self._state = "idle"
        self._lock  = threading.Lock()
    def set(self, s):
        with self._lock: self._state = s
    def get(self):
        with self._lock: return self._state

state = AssistantState()

# -------------------------
# Wake word toggle
# Set False to disable wake word and use hotkey instead.
# Set True to re-enable wake word detection.
# -------------------------
WAKE_WORD_ON = False

# -------------------------
# Hotkey trigger
# threading.Event — hotkey listener sets it,
# assistant loop waits on it.
# Only used when WAKE_WORD_ON = False.
# Hotkey: Cmd + Shift + Space
# -------------------------
_hotkey_event = threading.Event()

def _on_hotkey():
    """Called by pynput when hotkey fires. Unblocks the assistant loop."""
    if state.get() == "idle":
        _hotkey_event.set()

def _start_hotkey_listener():
    """Starts global hotkey listener as daemon thread."""
    hotkey = keyboard.GlobalHotKeys({
        "<cmd>+<shift>+<space>": _on_hotkey
    })
    hotkey.daemon = True
    hotkey.start()

# -------------------------
# Icon path
# -------------------------
ICON_PATH = os.path.join(ROOT, "assets", "arcn_icon.png")

# -------------------------
# Boot modules
# -------------------------
nlp = NLPBrain()
cc  = CommandCenter(TOOLS)
ww_model, ww_config, ww_device = load_wake_word_model()

SHUTDOWN_WORDS = ["goodbye", "shut down", "exit arcn", "stop arcn", "quit"]

# -------------------------
# State server
# -------------------------
set_state_source(state)
start_state_server()
set_icon_path(ICON_PATH)

# -------------------------
# Assistant loop
# -------------------------
def assistant_loop():
    time.sleep(1.5)
    speak("Arcn online.")

    try:
        while True:
            state.set("idle")

            if WAKE_WORD_ON:
                # ── wake word path ──
                wait_for_wake_word(ww_model, ww_config, ww_device)
            else:
                # ── hotkey path ──
                # Block here until Cmd+Shift+Space is pressed.
                # _hotkey_event is set by _on_hotkey() on keypress.
                # Clear it immediately after waking so next press works.
                _hotkey_event.wait()
                _hotkey_event.clear()

            # ── conversation loop — stays active until silence ──
            while True:
                state.set("listening")
                text = listen()

                if not text:
                    # nothing heard — drop back to trigger
                    break

                if any(word in text for word in SHUTDOWN_WORDS):
                    speak("Shutting down.")
                    cc.shutdown()
                    import AppKit
                    AppKit.NSApplication.sharedApplication().terminate_(None)
                    return

                state.set("processing")
                packet = nlp.predict(text)
                packet["source"] = "nlp"

                if "entities" not in packet:
                    packet["entities"] = {}
                packet["entities"]["raw_text"] = text

                set_last_intent(packet.get("intent", ""))
                result = cc.handle(packet)

                response = result.get("response", "")
                if response:
                    state.set("speaking")
                    set_last_response(response)
                    speak(response)

                # stay in loop only if tool explicitly expects follow-up
                if not result.get("expects_followup", False):
                    break

                # ── stay in conversation window after response ──
                # inner while continues — listens again immediately
                # listen() timeout (4s) is the natural exit if silence

    except KeyboardInterrupt:
        print("\nInterrupted.")
        cc.shutdown()

# -------------------------
# Create pywebview window
# -------------------------
win, api = create_window(ICON_PATH)

# -------------------------
# Start assistant + proactive engine
# in background threads after webview ready
# -------------------------

def on_webview_started():
    # Start global hotkey listener — always running regardless of WAKE_WORD_ON
    # costs zero CPU, harmless when wake word is on
    _start_hotkey_listener()

    # Assistant loop — daemon thread
    t = threading.Thread(target=assistant_loop, daemon=True)
    t.start()

    # Proactive engine — daemon thread
    proactive_engine.start(state)

webview.start(on_webview_started)

# -------------------------
# pywebview owns main thread
# -------------------------