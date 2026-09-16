import hashlib
import math
import re

DIMENSIONS = 512

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "of", "in", "on", "at", "to", "for", "and", "or", "but", "if", "with",
    "what", "which", "who", "whom", "this", "that", "these", "those", "it",
    "do", "does", "did", "can", "could", "will", "would", "should", "may",
    "i", "you", "he", "she", "we", "they", "them", "their", "its", "as",
    "not", "no", "so", "than", "then", "there", "here", "how", "why", "when",
}


def embed(text: str) -> list[float]:
    """Deterministic local embedding (hashed bag-of-words) so RAG works offline with no model download.

    Swappable later for a real embedding provider by changing EMBEDDING_MODEL and this module.
    """
    vector = [0.0] * DIMENSIONS
    for token in _TOKEN_PATTERN.findall(text.lower()):
        if token in _STOPWORDS:
            continue
        index = int(hashlib.sha256(token.encode()).hexdigest(), 16) % DIMENSIONS
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))
