import json
import time
import numpy as np
import sounddevice as sd
import torch
import torch.nn as nn
import torch.nn.functional as F
import librosa
from pathlib import Path


# -------------------------
# Config
# -------------------------
MODEL_DIR         = Path(__file__).parent / "wake_word_model"
THRESHOLD         = 0.90     # confidence required to trigger
CONFIRMATION_TONE = True     # set False to disable the hum sound on trigger
TONE_DURATION   = 0.25       # slightly longer for a rounder feel
TONE_FREQ_START = 180        # Hz — low warm hum
TONE_FREQ_END   = 260        # Hz — gentle rise, not a whir
SAMPLE_RATE_OUT = 24000


# -------------------------
# Same tiny CNN from training
# Must match train_wake_word.py
# exactly — architecture is fixed
# -------------------------
class WakeWordModel(nn.Module):

    def __init__(self, fc_in: int):
        super().__init__()

        self.conv1   = nn.Conv2d(1, 16, kernel_size=3, padding=1)
        self.conv2   = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        self.bn1     = nn.BatchNorm2d(16)
        self.bn2     = nn.BatchNorm2d(32)
        self.pool    = nn.MaxPool2d(2, 2)
        self.dropout = nn.Dropout(0.3)
        self.fc1     = nn.Linear(fc_in, 64)
        self.fc2     = nn.Linear(64, 1)

    def forward(self, x):
        x = self.pool(F.relu(self.bn1(self.conv1(x))))
        x = self.pool(F.relu(self.bn2(self.conv2(x))))
        x = x.view(x.size(0), -1)
        x = self.dropout(F.relu(self.fc1(x)))
        x = self.fc2(x)
        return x.squeeze(1)


# -------------------------
# Generate ascending tone
# in code — no audio files needed
# -------------------------
def _play_confirmation_tone():
    if not CONFIRMATION_TONE:
        return

    t    = np.linspace(0, TONE_DURATION, int(SAMPLE_RATE_OUT * TONE_DURATION))
    freq = np.linspace(TONE_FREQ_START, TONE_FREQ_END, len(t))

    # Primary sine + soft harmonic for warmth
    tone = 0.7 * np.sin(2 * np.pi * freq * t) + \
           0.3 * np.sin(2 * np.pi * freq * 2 * t)

    # Longer fade in, sharper fade out — feels more intentional
    fade_in_samples          = int(SAMPLE_RATE_OUT * 0.06)
    fade_out_samples         = int(SAMPLE_RATE_OUT * 0.04)
    tone[:fade_in_samples]  *= np.linspace(0, 1, fade_in_samples)
    tone[-fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)

    tone = (tone * 0.35).astype(np.float32)
    sd.play(tone, samplerate=SAMPLE_RATE_OUT)
    sd.wait()

# -------------------------
# Audio chunk → mel → tensor
# -------------------------
def _preprocess(audio: np.ndarray, config: dict) -> torch.Tensor:
    sample_rate   = config["sample_rate"]
    duration      = config["duration"]
    n_mels        = config["n_mels"]
    hop_length    = config["hop_length"]
    n_fft         = config["n_fft"]
    target_length = sample_rate * duration

    if len(audio) < target_length:
        audio = np.pad(audio, (0, target_length - len(audio)))
    audio = audio[:target_length]

    mel    = librosa.feature.melspectrogram(
        y          = audio,
        sr         = sample_rate,
        n_mels     = n_mels,
        hop_length = hop_length,
        n_fft      = n_fft
    )
    mel_db = librosa.power_to_db(mel, ref=np.max)
    mel_db = mel_db / 80.0

    return torch.tensor(mel_db, dtype=torch.float32).unsqueeze(0).unsqueeze(0)


# -------------------------
# Load model once at boot
# Call this in main.py and
# pass the result into
# wait_for_wake_word()
# -------------------------
def load_wake_word_model():
    config_path = MODEL_DIR / "config.json"
    model_path  = MODEL_DIR / "wake_word.pt"

    if not config_path.exists() or not model_path.exists():
        raise FileNotFoundError(
            "Wake word model not found. "
            "Run speech/train_wake_word.py first."
        )

    with open(config_path, "r") as f:
        config = json.load(f)

    sample_rate = config["sample_rate"]
    duration    = config["duration"]
    n_mels      = config["n_mels"]
    hop_length  = config["hop_length"]

    # Calculate fc_in to match training exactly
    time_steps = (sample_rate * duration) // hop_length + 1
    after_pool = (n_mels // 4) * (time_steps // 4)
    fc_in      = 32 * after_pool

    device = torch.device("cpu")
    model  = WakeWordModel(fc_in=fc_in).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    print(f"Wake word model loaded — threshold: {THRESHOLD}")

    return model, config, device


# -------------------------
# Main detector loop
# Blocks until wake word fires
# then returns so listener.py
# can take over the mic
# -------------------------
def wait_for_wake_word(model, config, device):
    sample_rate   = config["sample_rate"]
    duration      = config["duration"]
    chunk_samples = sample_rate * duration
    hop_samples   = sample_rate // 2     # 0.5s hop — overlapping windows

    print("Waiting for wake word...")

    # Rolling buffer — holds one full 2s window
    buffer = np.zeros(chunk_samples, dtype=np.float32)

    def callback(indata, frames, time_info, status):
        nonlocal buffer
        chunk  = indata[:, 0]
        buffer = np.roll(buffer, -len(chunk))
        buffer[-len(chunk):] = chunk

    with sd.InputStream(
        samplerate = sample_rate,
        channels   = 1,
        dtype      = "float32",
        blocksize  = hop_samples,
        callback   = callback
    ):
        time.sleep(2.0)  # flush hardware buffer and TTS tail before detection starts

        while True:
            time.sleep(0.5)

            tensor = _preprocess(buffer.copy(), config)

            with torch.no_grad():
                logit      = model(tensor.to(device))
                confidence = torch.sigmoid(logit).item()

            # Confidence threshold
            if confidence >= THRESHOLD:
                print(f"Wake word detected — confidence: {confidence:.3f}")
                _play_confirmation_tone()
                time.sleep(0.3)  # let audio device release before TTS opens
                return   # hand off to listener.py