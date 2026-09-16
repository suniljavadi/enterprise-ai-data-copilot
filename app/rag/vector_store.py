import faiss
import numpy as np

from app.rag.embeddings import DIMENSIONS


class VectorStore:
    """Thin FAISS wrapper; swappable for Chroma or another backend behind this same interface."""

    def __init__(self, dimensions: int = DIMENSIONS):
        self.dimensions = dimensions
        self._index = faiss.IndexFlatIP(dimensions)
        self._metadata: list[dict] = []

    def add(self, vectors: list[list[float]], metadatas: list[dict]) -> None:
        if not vectors:
            return
        matrix = np.array(vectors, dtype="float32")
        self._index.add(matrix)
        self._metadata.extend(metadatas)

    def search(self, query_vector: list[float], k: int = 5) -> list[tuple[dict, float]]:
        if self._index.ntotal == 0:
            return []
        query_matrix = np.array([query_vector], dtype="float32")
        scores, indices = self._index.search(query_matrix, min(k, self._index.ntotal))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append((self._metadata[idx], float(score)))
        return results

    def clear(self) -> None:
        self._index = faiss.IndexFlatIP(self.dimensions)
        self._metadata = []

    @property
    def size(self) -> int:
        return self._index.ntotal
