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

        import time

        # NLP processes
        t0 = time.time()
        packet = nlp.predict(text)
        print(f"NLP: {time.time() - t0:.2f}s")

        packet["source"] = "nlp"
        if "entities" not in packet:
            packet["entities"] = {}
        packet["entities"]["raw_text"] = text  # always inject, outside the if

        # CC handles
        t1 = time.time()
        result = cc.handle(packet)
        print(f"CC + tool: {time.time() - t1:.2f}s")

        # Speak the response
        t2 = time.time()
        response = result.get("response", "")
        if response:
            speak(response)
        print(f"TTS: {time.time() - t2:.2f}s")
        print(f"Total: {time.time() - t0:.2f}s")

        """
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
            """

except KeyboardInterrupt:
    print("\nInterrupted.")
    cc.shutdown()