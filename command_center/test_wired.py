import sys
import os

sys.path.append(os.path.abspath("../nlp"))
sys.path.append(os.path.abspath("../tools_assistant"))
sys.path.append(os.path.abspath("../speech"))

os.chdir(os.path.abspath("../nlp"))

from pipeline import NLPBrain
from core import CommandCenter
from registry import TOOLS
from speaker import speak
from listener import listen

# Boot
nlp = NLPBrain()
cc  = CommandCenter(TOOLS)

speak("Arcn online.")

# Live loop
try:
    while True:

        text = listen()

        if not text:
            continue

        # Shutdown commands
        SHUTDOWN_WORDS = ["goodbye", "shut down", "exit arcn", "stop arcn", "quit"]

        if any(word in text for word in SHUTDOWN_WORDS):
            speak("Shutting down.")
            cc.shutdown()
            break

        # NLP processes
        packet = nlp.predict(text)
        packet["source"] = "nlp"
        if "entities" not in packet:
            packet["entities"] = {}
        packet["entities"]["raw_text"] = text  # always inject, outside the if

        # CC handles
        result = cc.handle(packet)

        # Speak the response
        response = result.get("response", "")
        if response:
            speak(response)

except KeyboardInterrupt:
    print("\nInterrupted.")
    cc.shutdown()