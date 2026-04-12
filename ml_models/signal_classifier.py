# REAL CLASSIFIER: DistilBERT fine-tuned on AG News (Stage 5)
# Interface identical to Stage 4 stub — predict() contract unchanged

import os
import torch
from transformers import DistilBertForSequenceClassification, DistilBertTokenizerFast

# @traceable injects this local ML model into LangSmith traces.
# Without this, LangSmith only captures LLM calls — the DistilBERT
# execution would be invisible. With this, every prediction shows up
# in the LangGraph waterfall: input text, signal label, confidence, latency.
from langsmith import traceable

LABEL_MAP = {0: 'GEOPOLITICAL', 1: 'EARNINGS', 2: 'PRODUCT_LAUNCH'}
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'best_checkpoint')

class SignalClassifier:
    def __init__(self):
        self.tokenizer = DistilBertTokenizerFast.from_pretrained(MODEL_PATH)
        self.model = DistilBertForSequenceClassification.from_pretrained(MODEL_PATH)
        self.model.eval()

        # Define the traced function inside __init__ so it uses self.tokenizer
        # and self.model via closure. This prevents LangSmith from trying to
        # JSON-serialize `self` (which crashes because PyTorch models aren't serializable).
        @traceable(run_type="chain", name="DistilBERT Signal Classifier")
        def _predict_traced(text: str) -> dict:
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
        
        self._predict_traced = _predict_traced

    def predict(self, text: str) -> dict:
        return self._predict_traced(text)
