import json
import torch
from pathlib import Path
from transformers import (
    DistilBertTokenizerFast,
    DistilBertForSequenceClassification
)
import torch.nn.functional as F


# -------------------------
# Config
# -------------------------
MODEL_DIR = Path(__file__).parent.parent / "models" / "intent_model"

class IntentClassifier:

    def __init__(self):

        print("Loading intent classifier...")

        # Load tokenizer + model
        self.tokenizer = DistilBertTokenizerFast.from_pretrained(MODEL_DIR)
        self.model     = DistilBertForSequenceClassification.from_pretrained(MODEL_DIR)
        self.model.eval()

        # Load label maps
        with open(MODEL_DIR / "label_map.json", "r") as f:
            maps = json.load(f)

        self.label_map = maps["label_map"]   # intent → id
        self.id_map    = {
            int(k): v
            for k, v in maps["id_map"].items()
        }                                     # id → intent

        # Device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

        print(f"  Loaded {len(self.label_map)} intents")
        print(f"  Device: {self.device}")

    # -------------------------
    # Predict intent
    # -------------------------
    def predict(self, text: str):

        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors = "pt",
            truncation     = True,
            padding        = True,
            max_length     = 64
        )

        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Inference
        with torch.no_grad():
            outputs = self.model(**inputs)

        # Softmax → probabilities
        probs = F.softmax(outputs.logits, dim=-1)

        # Top prediction
        top_prob, top_idx = torch.max(probs, dim=-1)

        intent     = self.id_map[top_idx.item()]
        confidence = round(top_prob.item(), 3)

        # Confidence routing
        if confidence < 0.55:
            intent = "unknown_intent"

        requires_clarification = (
            0.55 <= confidence < 0.70
        )

        return {
            "intent"                : intent,
            "confidence"            : confidence,
            "requires_clarification": requires_clarification
        }