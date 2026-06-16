import threading
import sounddevice as sd
from kokoro import KPipeline


# -------------------------
# Config — change voice here
# -------------------------
VOICE       = "af_heart"  # options: af_heart, af_bella, af_sarah, am_adam, am_michael
LANG_CODE   = "a"         # "a" = American English, "b" = British English
SAMPLE_RATE = 24000


# -------------------------
# Global audio lock
# Prevents the assistant loop and proactive engine
# from opening the audio device simultaneously.
# Any call to speak() blocks until the current one finishes.
# -------------------------
_audio_lock = threading.Lock()


# -------------------------
# Load Kokoro pipeline once
# at import time — avoids
# reloading on every speak()
# -------------------------
print("Loading Kokoro TTS...")
_pipeline = KPipeline(lang_code=LANG_CODE)
print("  Kokoro ready")


# -------------------------
# Public speak function
# -------------------------
def speak(text: str):

    if not text or not text.strip():
        return

    print(f"Arcn: {text}")

    import numpy as np

    # Acquire lock before touching audio device.
    # If proactive engine is speaking, assistant waits.
    # If assistant is speaking, proactive engine waits.
    with _audio_lock:

        generator = _pipeline(text, voice=VOICE)
        buffer = []

        for gs, ps, audio in generator:
            buffer.append(audio)

            # Play in small batches of 3 chunks
            # balances latency vs blip prevention
            if len(buffer) >= 3:
                sd.play(np.concatenate(buffer), samplerate=SAMPLE_RATE)
                sd.wait()
                buffer = []

        # Play any remaining chunks
        if buffer:
            sd.play(np.concatenate(buffer), samplerate=SAMPLE_RATE)
            sd.wait()