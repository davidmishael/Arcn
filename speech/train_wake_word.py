import os
import json
import numpy as np
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torch.optim import Adam
from torch.optim.lr_scheduler import StepLR

import librosa
from sklearn.model_selection import train_test_split


# -------------------------
# Config
# -------------------------
DATA_DIR    = Path(__file__).parent / "wake_word_data"
POS_DIR     = DATA_DIR / "positive"
NEG_DIR     = DATA_DIR / "negative"
MODEL_DIR   = Path(__file__).parent / "wake_word_model"

SAMPLE_RATE = 16000
DURATION    = 2          # seconds — must match record_samples.py
N_MELS      = 40         # mel spectrogram bins
HOP_LENGTH  = 512        # controls time resolution of spectrogram
N_FFT       = 1024

EPOCHS      = 30
BATCH_SIZE  = 16
LEARNING_RATE = 1e-3
TEST_SPLIT  = 0.2        # 20% held out for validation


# -------------------------
# Audio → mel spectrogram
# -------------------------
def audio_to_mel(path: str) -> np.ndarray:
    # Load and force to correct length
    audio, sr = librosa.load(path, sr=SAMPLE_RATE, mono=True)

    target_length = SAMPLE_RATE * DURATION

    # Pad if shorter than expected
    if len(audio) < target_length:
        audio = np.pad(audio, (0, target_length - len(audio)))

    # Trim if longer
    audio = audio[:target_length]

    # Compute mel spectrogram
    mel = librosa.feature.melspectrogram(
        y          = audio,
        sr         = sr,
        n_mels     = N_MELS,
        hop_length = HOP_LENGTH,
        n_fft      = N_FFT
    )

    # Convert to log scale — matches human hearing perception
    mel_db = librosa.power_to_db(mel, ref=np.max)

    # Normalize to [-1, 1]
    mel_db = mel_db / 80.0

    return mel_db.astype(np.float32)


# -------------------------
# PyTorch Dataset
# -------------------------
class WakeWordDataset(Dataset):

    def __init__(self, features: list, labels: list):
        self.features = features
        self.labels   = labels

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        # Add channel dim — CNN expects (channels, height, width)
        x = torch.tensor(self.features[idx]).unsqueeze(0)
        y = torch.tensor(self.labels[idx], dtype=torch.float32)
        return x, y


# -------------------------
# Tiny CNN model
# -------------------------
class WakeWordModel(nn.Module):

    def __init__(self):
        super().__init__()

        # Two conv layers to extract local patterns from spectrogram
        self.conv1 = nn.Conv2d(1, 16, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)

        # Batch norm stabilises training
        self.bn1 = nn.BatchNorm2d(16)
        self.bn2 = nn.BatchNorm2d(32)

        # Pooling reduces spatial dims after each conv
        self.pool = nn.MaxPool2d(2, 2)

        # Dropout prevents overfitting on small dataset
        self.dropout = nn.Dropout(0.3)

        # Calculate flattened size after two pool operations
        # Input mel: (N_MELS=40, time_steps)
        # After pool1: (20, time_steps//2)
        # After pool2: (10, time_steps//4)
        time_steps  = (SAMPLE_RATE * DURATION) // HOP_LENGTH + 1
        after_pool  = (N_MELS // 4) * (time_steps // 4)
        fc_in       = 32 * after_pool

        self.fc1 = nn.Linear(fc_in, 64)
        self.fc2 = nn.Linear(64, 1)   # single output — wake word probability

    def forward(self, x):
        # Conv block 1
        x = self.pool(F.relu(self.bn1(self.conv1(x))))

        # Conv block 2
        x = self.pool(F.relu(self.bn2(self.conv2(x))))

        # Flatten
        x = x.view(x.size(0), -1)

        # Fully connected
        x = self.dropout(F.relu(self.fc1(x)))
        x = self.fc2(x)

        return x.squeeze(1)   # shape: (batch,)


# -------------------------
# Load all audio files
# and extract features
# -------------------------
def load_dataset():
    print("Loading audio files and extracting mel spectrograms...")

    features = []
    labels   = []
    errors   = 0

    # Positive — label 1
    pos_files = sorted(POS_DIR.glob("*.wav"))
    print(f"  Positives : {len(pos_files)} files")

    for path in pos_files:
        try:
            mel = audio_to_mel(str(path))
            features.append(mel)
            labels.append(1)
        except Exception as e:
            print(f"  Error loading {path.name}: {e}")
            errors += 1

    # Negative — label 0
    neg_files = sorted(NEG_DIR.glob("*.wav"))
    print(f"  Negatives : {len(neg_files)} files")

    for path in neg_files:
        try:
            mel = audio_to_mel(str(path))
            features.append(mel)
            labels.append(0)
        except Exception as e:
            print(f"  Error loading {path.name}: {e}")
            errors += 1

    if errors:
        print(f"  Skipped {errors} files due to errors")

    print(f"  Total loaded: {len(features)} samples")
    return features, labels


# -------------------------
# Training loop
# -------------------------
def train():

    # Load data
    features, labels = load_dataset()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Train / validation split
    X_train, X_val, y_train, y_val = train_test_split(
        features, labels,
        test_size    = TEST_SPLIT,
        random_state = 42,
        stratify     = labels   # keeps class balance in both splits
    )

    print(f"\n  Train : {len(X_train)} samples")
    print(f"  Val   : {len(X_val)} samples")

    # Datasets and loaders
    train_dataset = WakeWordDataset(X_train, y_train)
    val_dataset   = WakeWordDataset(X_val,   y_val)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader   = DataLoader(val_dataset,   batch_size=BATCH_SIZE, shuffle=False)

    # Model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n  Device: {device}")

    model = WakeWordModel().to(device)

    # Loss — binary cross entropy for 0/1 classification
    import numpy as np

    num_neg = (np.array(labels) == 0).sum()
    num_pos = (np.array(labels) == 1).sum()
    pos_weight = torch.tensor([num_neg / num_pos], dtype=torch.float32).to(device)
    criterion = nn.BCEWithLogitsLoss()

    # Optimizer + scheduler
    optimizer = Adam(model.parameters(), lr=LEARNING_RATE)
    scheduler = StepLR(optimizer, step_size=10, gamma=0.5)  # halve LR every 10 epochs

    print("\nTraining...\n")

    best_val_acc  = 0.0
    best_model_state = None

    for epoch in range(EPOCHS):

        # -------------------------
        # Train
        # -------------------------
        model.train()
        train_loss    = 0.0
        train_correct = 0

        for X_batch, y_batch in train_loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)

            optimizer.zero_grad()
            logits = model(X_batch)
            loss   = criterion(logits, y_batch)
            loss.backward()
            optimizer.step()

            train_loss    += loss.item()
            preds          = (torch.sigmoid(logits) >= 0.5).float()
            train_correct += (preds == y_batch).sum().item()

        scheduler.step()

        # -------------------------
        # Validate
        # -------------------------
        model.eval()
        val_loss    = 0.0
        val_correct = 0

        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch = X_batch.to(device)
                y_batch = y_batch.to(device)

                logits      = model(X_batch)
                loss        = criterion(logits, y_batch)
                val_loss   += loss.item()
                preds       = (torch.sigmoid(logits) >= 0.5).float()
                val_correct += (preds == y_batch).sum().item()

        train_acc = train_correct / len(X_train)
        val_acc   = val_correct   / len(X_val)

        print(
            f"  Epoch {epoch+1:02d}/{EPOCHS}  "
            f"train loss: {train_loss/len(train_loader):.4f}  "
            f"train acc: {train_acc:.3f}  "
            f"val loss: {val_loss/len(val_loader):.4f}  "
            f"val acc: {val_acc:.3f}"
        )

        # Save best model by validation accuracy
        if val_acc > best_val_acc:
            best_val_acc     = val_acc
            best_model_state = {k: v.clone() for k, v in model.state_dict().items()}

    # -------------------------
    # Save model + config
    # -------------------------
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Save best weights
    torch.save(best_model_state, MODEL_DIR / "wake_word.pt")

    # Save config so wake_word.py knows the exact params used
    config = {
        "sample_rate" : SAMPLE_RATE,
        "duration"    : DURATION,
        "n_mels"      : N_MELS,
        "hop_length"  : HOP_LENGTH,
        "n_fft"       : N_FFT
    }
    with open(MODEL_DIR / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n  Best val accuracy : {best_val_acc:.3f}")
    print(f"  Model saved to    : {MODEL_DIR}")
    print("  Training complete.")


if __name__ == "__main__":
    train()