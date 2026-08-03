import threading
import sounddevice as sd
from kokoro import KPipeline


# -------------------------
# Config — change voice here
# -------------------------
VOICE       = "am_michael"  # options: *af_heart, af_bella, af_sarah, *am_adam, am_michael
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

    with _audio_lock:
        try:
            generator = _pipeline(text, voice=VOICE)

            with sd.OutputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32"
            ) as stream:

                for result in generator:
                    audio = result.output.audio
                    audio = audio.detach().cpu().numpy()
                    audio = np.clip(audio, -1.0, 1.0).astype(np.float32)

                    stream.write(audio)

        except Exception as e:
            print(f"[speaker] TTS failed: {e}")