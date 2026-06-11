import json
import time
import speech_recognition as sr
from faster_whisper import WhisperModel


# -------------------------
# Config
# -------------------------
WHISPER_MODEL    = "small"
COMPUTE_TYPE     = "int8"
ENERGY_THRESHOLD = 400
TIMEOUT          = 8
PHRASE_LIMIT     = 6
STATE_FILE       = "assistant_state.json"


# -------------------------
# Load Whisper once
# -------------------------
print("Loading Whisper model...")
model = WhisperModel(WHISPER_MODEL, compute_type=COMPUTE_TYPE)
print("  Whisper ready")

recognizer = sr.Recognizer()
recognizer.energy_threshold        = ENERGY_THRESHOLD
recognizer.dynamic_energy_threshold = False


# -------------------------
# Check listening state
# -------------------------
def is_listening_enabled() -> bool:

    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            return data.get("listening", True)
    except Exception:
        return True


# -------------------------
# Listen + transcribe
# -------------------------
def listen() -> str | None:

    if not is_listening_enabled():
        time.sleep(0.3)
        return None

    with sr.Microphone() as source:

        print("\nListening...")

        recognizer.adjust_for_ambient_noise(source, duration=0.3)

        try:
            audio = recognizer.listen(
                source,
                timeout          = TIMEOUT,
                phrase_time_limit= PHRASE_LIMIT
            )
        except sr.WaitTimeoutError:
            return None

    # Check again after recording
    if not is_listening_enabled():
        return None

    try:
        with open("audio.wav", "wb") as f:
            f.write(audio.get_wav_data())

        segments, _ = model.transcribe("audio.wav")

        import os
        os.remove("audio.wav")

        text = "".join(segment.text for segment in segments).lower().strip()

        if text:
            print(f"You: {text}")

        return text if text else None

    except Exception as e:
        print(f"Whisper error: {e}")
        return None