from pathlib import Path

from app.rag.chunker import chunk_text
from app.rag.embeddings import _STOPWORDS, embed
from app.rag.loader import list_documents, load_document
from app.rag.vector_store import VectorStore

_store = VectorStore()


def get_vector_store() -> VectorStore:
    return _store


def ingest_document(path: str | Path) -> dict:
    text, metadata = load_document(path)
    chunks = chunk_text(text)

    vectors = [embed(chunk["text"]) for chunk in chunks]
    metadatas = [
        {**metadata, "chunk_id": f"{metadata['document_name']}::{chunk['chunk_index']}", "text": chunk["text"]}
        for chunk in chunks
    ]
    _store.add(vectors, metadatas)
    return {"document_name": metadata["document_name"], "chunks_indexed": len(chunks)}


def ingest_directory(directory: str | Path | None = None) -> list[dict]:
    directory = directory or "data/documents"
    results = []
    for file_path in list_documents(directory):
        results.append(ingest_document(file_path))
    return results


def search(question: str, top_k: int = 5) -> list[dict]:
    """Hybrid retrieval: semantic (embedding cosine) blended with lexical keyword overlap."""
    query_vector = embed(question)
    question_tokens = {t for t in question.lower().split() if t not in _STOPWORDS}

    raw_results = _store.search(query_vector, k=max(top_k * 2, top_k))
    scored = []
    for metadata, semantic_score in raw_results:
        chunk_tokens = {t for t in metadata["text"].lower().split() if t not in _STOPWORDS}
        lexical_score = len(question_tokens & chunk_tokens) / max(len(question_tokens), 1)
        blended_score = 0.7 * semantic_score + 0.3 * lexical_score
        scored.append({**metadata, "score": round(blended_score, 4)})

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def reset_index() -> None:
    _store.clear()
