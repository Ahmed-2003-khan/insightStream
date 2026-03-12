# REAL CLASSIFIER: DistilBERT fine-tuned on AG News (Stage 5)
# Interface identical to Stage 4 stub — predict() contract unchanged

import os
import torch
from transformers import DistilBertForSequenceClassification, DistilBertTokenizerFast

LABEL_MAP = {0: 'GEOPOLITICAL', 1: 'EARNINGS', 2: 'PRODUCT_LAUNCH'}
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'best_checkpoint')

class SignalClassifier:
    def __init__(self):
        self.tokenizer = DistilBertTokenizerFast.from_pretrained(MODEL_PATH)
        self.model = DistilBertForSequenceClassification.from_pretrained(MODEL_PATH)
        self.model.eval()

    def predict(self, text: str) -> dict:
        inputs = self.tokenizer(
            text,
            return_tensors='pt',
            truncation=True,
            max_length=128,
            padding=True
        )
        with torch.no_grad():
            logits = self.model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)
        confidence, predicted_class = torch.max(probs, dim=-1)
        return {
            'label': LABEL_MAP[predicted_class.item()],
            'confidence': round(confidence.item(), 4)
        }
