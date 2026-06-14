import os
import speech_recognition as sr
from faster_whisper import WhisperModel


# -------------------------
# Config
# -------------------------
WHISPER_MODEL    = "small"
COMPUTE_TYPE     = "int8"
ENERGY_THRESHOLD = 600  # raised from 400 — filters ambient noise
TIMEOUT          = 4    # raised from 5 per session fix
PHRASE_LIMIT     = 6


# -------------------------
# Load Whisper once
# -------------------------
print("Loading Whisper model...")
model = WhisperModel(WHISPER_MODEL, compute_type=COMPUTE_TYPE)
print("  Whisper ready")

recognizer = sr.Recognizer()
recognizer.energy_threshold         = ENERGY_THRESHOLD
recognizer.dynamic_energy_threshold = False


# -------------------------
# Listen + transcribe
# -------------------------
def listen() -> str | None:

    with sr.Microphone() as source:
        print("\nListening...")
        recognizer.adjust_for_ambient_noise(source, duration=0.3)

        try:
            audio = recognizer.listen(
                source,
                timeout           = TIMEOUT,
                phrase_time_limit = PHRASE_LIMIT
            )
        except sr.WaitTimeoutError:
            return None
        except KeyboardInterrupt:
            raise  # let main.py handle shutdown cleanly

    try:
        wav_path = "audio.wav"
        with open(wav_path, "wb") as f:
            f.write(audio.get_wav_data())

        try:
            segments, _ = model.transcribe(wav_path)
            text = "".join(segment.text for segment in segments).lower().strip()
        except KeyboardInterrupt:
            # Whisper interrupted mid-inference — clean up and propagate
            if os.path.exists(wav_path):
                os.remove(wav_path)
            raise
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

        if text:
            print(f"You: {text}")

        return text if text else None

    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"Whisper error: {e}")
        return None