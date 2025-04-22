"""
sentiment.py

This module provides a function to analyze the sentiment of a given text
using a pre-trained sentiment analysis model. It determines if the text
expresses frustration based on a specified confidence threshold.
"""
# sentiment.py

from transformers import pipeline

_analyzer = pipeline("sentiment-analysis",
                     model="distilbert-base-uncased-finetuned-sst-2-english")

def is_frustrated(text: str, threshold: float = 0.5) -> bool:
    """
    Returns True if the text is classified as NEGATIVE with confidence ≥ threshold.
    """
    result = _analyzer(text, truncation=True)[0]
    return (result["label"] == "NEGATIVE") and (result["score"] >= threshold)