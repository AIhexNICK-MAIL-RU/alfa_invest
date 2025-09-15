from __future__ import annotations

import threading
from typing import Tuple

import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer


_lock = threading.RLock()
_model: T5ForConditionalGeneration | None = None
_tokenizer: T5Tokenizer | None = None


def load_model(model_name: str = "t5-small") -> Tuple[T5ForConditionalGeneration, T5Tokenizer]:
    global _model, _tokenizer
    with _lock:
        if _model is None or _tokenizer is None:
            _tokenizer = T5Tokenizer.from_pretrained(model_name)
            _model = T5ForConditionalGeneration.from_pretrained(model_name)
            _model.eval()
            _model.config.use_cache = True
    return _model, _tokenizer


def generate_paraphrase(text: str, prefix: str = "paraphrase: ") -> str:
    model, tokenizer = load_model()
    input_text = f"{prefix}{text}"
    input_ids = tokenizer.encode(
        input_text, return_tensors="pt", max_length=512, truncation=True
    )
    with torch.no_grad():
        outputs = model.generate(
            input_ids,
            max_length=180,
            num_beams=5,
            num_return_sequences=1,
            temperature=0.8,
            repetition_penalty=3.0,
            early_stopping=True,
        )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)


