import re
import json
import logging
from config import CHUNK_SIZE, CHUNK_OVERLAP

def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """
    Split a long text into overlapping chunks so each fits
    within the LLM context window without losing context at boundaries.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks