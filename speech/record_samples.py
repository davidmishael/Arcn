import os
import sys
import wave
import struct
import threading
import sounddevice as sd
import numpy as np
from pathlib import Path

#Option A — just run one more partial batch
#Pick option 1 (normal volume) and do 30 more positives, and option 5 (random sentences) for 22 more negatives. Gets you to 150/150.

# -------------------------
# Config
# -------------------------
SAMPLE_RATE  = 16000   # 16kHz — matches Whisper and what the model expects
CHANNELS     = 1       # mono
DURATION     = 2       # seconds per clip
DATA_DIR     = Path(__file__).parent / "wake_word_data"
POS_DIR      = DATA_DIR / "positive"
NEG_DIR      = DATA_DIR / "negative"


# -------------------------
# Save audio as WAV
# -------------------------
def save_wav(path: Path, audio: np.ndarray):
    # Clip to valid int16 range and convert
    audio_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)

    with wave.open(str(path), 'w') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)          # 2 bytes = int16
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_int16.tobytes())


# -------------------------
# Record a single clip
# -------------------------
def record_clip() -> np.ndarray:
    print("  Recording...", end="", flush=True)
    audio = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate = SAMPLE_RATE,
        channels   = CHANNELS,
        dtype      = "float32"
    )
    sd.wait()
    print(" done.")
    return audio.flatten()


# -------------------------
# Count existing files
# so we never overwrite
# -------------------------
def next_index(directory: Path, prefix: str) -> int:
    existing = list(directory.glob(f"{prefix}_*.wav"))
    if not existing:
        return 1
    indices = []
    for f in existing:
        try:
            idx = int(f.stem.split("_")[-1])
            indices.append(idx)
        except ValueError:
            pass
    return max(indices) + 1 if indices else 1


# -------------------------
# Record a batch of clips
# -------------------------
def record_batch(label: str, directory: Path, prefix: str, count: int, instructions: str):
    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    print(f"  {instructions}")
    print(f"  Recording {count} clips.")
    print(f"  Press ENTER to record each one. Type 'skip' to skip. Type 'done' to stop early.")
    print()

    start_idx = next_index(directory, prefix)
    recorded  = 0

    for i in range(count):
        clip_num = start_idx + i
        prompt = f"  [{recorded + 1}/{count}] Press ENTER to record (or 'skip'/'done'): "

        try:
            user_input = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Stopped.")
            break

        if user_input == "done":
            print("  Stopping batch early.")
            break

        if user_input == "skip":
            print("  Skipped.")
            continue

        audio    = record_clip()
        filename = directory / f"{prefix}_{clip_num:03d}.wav"
        save_wav(filename, audio)
        print(f"  Saved: {filename.name}")
        recorded += 1

    print(f"\n  Batch complete — {recorded} clips recorded.")
    return recorded


# -------------------------
# Main menu
# -------------------------
def main():
    print("\nArcn Wake Word — Sample Recorder")
    print("==================================")
    print(f"  Sample rate : {SAMPLE_RATE}Hz")
    print(f"  Channels    : mono")
    print(f"  Clip length : {DURATION}s")
    print(f"  Saving to   : {DATA_DIR}")
    print()

    # Show current counts
    pos_count = len(list(POS_DIR.glob("*.wav")))
    neg_count = len(list(NEG_DIR.glob("*.wav")))
    print(f"  Existing positives : {pos_count}")
    print(f"  Existing negatives : {neg_count}")
    print()

    while True:
        print("What do you want to record?")
        print("  1 — Positive clips (Hey Arcn) — normal volume")
        print("  2 — Positive clips (Hey Arcn) — quieter / tired voice")
        print("  3 — Positive clips (Hey Arcn) — faster pace")
        print("  4 — Positive clips (Hey Arcn) — slower pace")
        print("  5 — Negative clips — random sentences")
        print("  6 — Negative clips — similar phrases (Hey Arc, Hey Aaron, etc)")
        print("  7 — Negative clips — background noise only (say nothing)")
        print("  8 — Negative clips — Hey Siri / OK Google / Hey there")
        print("  9 — Show current counts")
        print("  q — Quit")
        print()

        choice = input("Choice: ").strip().lower()

        if choice == "1":
            record_batch(
                label        = "POSITIVE — Normal volume",
                directory    = POS_DIR,
                prefix       = "hey_arcn",
                count        = 30,
                instructions = "Say 'Hey Arcn' clearly at your normal volume each time."
            )

        elif choice == "2":
            record_batch(
                label        = "POSITIVE — Quiet / tired voice",
                directory    = POS_DIR,
                prefix       = "hey_arcn",
                count        = 30,
                instructions = "Say 'Hey Arcn' a bit quieter, like you're tired or it's late."
            )

        elif choice == "3":
            record_batch(
                label        = "POSITIVE — Faster pace",
                directory    = POS_DIR,
                prefix       = "hey_arcn",
                count        = 30,
                instructions = "Say 'Hey Arcn' slightly faster than normal, like you're in a hurry."
            )

        elif choice == "4":
            record_batch(
                label        = "POSITIVE — Slower pace",
                directory    = POS_DIR,
                prefix       = "hey_arcn",
                count        = 30,
                instructions = "Say 'Hey Arcn' slightly slower and more deliberate than normal."
            )

        elif choice == "5":
            record_batch(
                label        = "NEGATIVE — Random sentences",
                directory    = NEG_DIR,
                prefix       = "neg",
                count        = 40,
                instructions = "Read anything out loud — articles, random sentences, whatever. NOT 'Hey Arcn'."
            )

        elif choice == "6":
            record_batch(
                label        = "NEGATIVE — Similar phrases",
                directory    = NEG_DIR,
                prefix       = "neg",
                count        = 30,
                instructions = "Say these one per clip: 'Hey Arc', 'Hey Arch', 'Hey Aaron', 'Hey Karen', 'Arcn', 'Hey our can'. Mix them up."
            )

        elif choice == "7":
            record_batch(
                label        = "NEGATIVE — Background noise",
                directory    = NEG_DIR,
                prefix       = "neg",
                count        = 20,
                instructions = "Say nothing — just let the mic record ambient room noise each time."
            )

        elif choice == "8":
            record_batch(
                label        = "NEGATIVE — Other wake words",
                directory    = NEG_DIR,
                prefix       = "neg",
                count        = 30,
                instructions = "Say these one per clip: 'Hey Siri', 'OK Google', 'Hey Google', 'Alexa', 'Hey there', 'Hey you'."
            )

        elif choice == "9":
            pos_count = len(list(POS_DIR.glob("*.wav")))
            neg_count = len(list(NEG_DIR.glob("*.wav")))
            print(f"\n  Positives : {pos_count} / 150 target")
            print(f"  Negatives : {neg_count} / 150 target")
            print()

        elif choice == "q":
            pos_count = len(list(POS_DIR.glob("*.wav")))
            neg_count = len(list(NEG_DIR.glob("*.wav")))
            print(f"\n  Final count — Positives: {pos_count}  Negatives: {neg_count}")
            print("  Done.")
            break

        else:
            print("  Invalid choice.\n")


if __name__ == "__main__":
    main()