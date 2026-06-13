import sys
import os

# -------------------------
# Add all module paths so
# Python can find each module
# regardless of where main.py
# is run from
# -------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))

sys.path.append(os.path.join(ROOT, "nlp"))
sys.path.append(os.path.join(ROOT, "nlp", "models"))
sys.path.append(os.path.join(ROOT, "nlp", "utils"))
sys.path.append(os.path.join(ROOT, "command_center"))
sys.path.append(os.path.join(ROOT, "tools_assistant"))
sys.path.append(os.path.join(ROOT, "speech"))
sys.path.append(os.path.join(ROOT, "memory"))

from pipeline import NLPBrain
from core import CommandCenter
from registry import TOOLS
from speaker import speak
from listener import listen
from wake_word import load_wake_word_model, wait_for_wake_word


# -------------------------
# Boot all modules
# -------------------------
nlp = NLPBrain()
cc  = CommandCenter(TOOLS)

# Load wake word model once at boot —
# stays in memory for the entire session
ww_model, ww_config, ww_device = load_wake_word_model()

speak("Arcn online.")

# -------------------------
# Words that trigger shutdown
# -------------------------
SHUTDOWN_WORDS = ["goodbye", "shut down", "exit arcn", "stop arcn", "quit"]


# -------------------------
# Main loop
# -------------------------
try:
    while True:

        # Wait for "Hey Arcn" before doing anything
        # Blocks here until wake word detected —
        # tone plays, then mic is released for listener
        wait_for_wake_word(ww_model, ww_config, ww_device)

        # Wake word fired — now transcribe what the user says
        text = listen()

        if not text:
            # Heard wake word but nothing after — go back to listening
            speak("I didn't catch that.")
            continue

        # Check for shutdown command
        if any(word in text for word in SHUTDOWN_WORDS):
            speak("Shutting down.")
            cc.shutdown()
            break

        # NLP processes the raw text into a structured packet
        packet = nlp.predict(text)
        packet["source"] = "nlp"

        # Ensure entities dict exists then inject raw text
        if "entities" not in packet:
            packet["entities"] = {}
        packet["entities"]["raw_text"] = text

        # Command Center routes and executes
        result = cc.handle(packet)

        # Speak the response if there is one
        response = result.get("response", "")
        if response:
            speak(response)

except KeyboardInterrupt:
    print("\nInterrupted.")
    cc.shutdown()