from pydantic import BaseModel

from app.core.config import get_settings
from app.rag.retriever import search

NO_EVIDENCE = "I could not find sufficient evidence in the indexed documents to answer this question."

_SIMILARITY_THRESHOLD = 0.12


class Citation(BaseModel):
    document_name: str
    chunk_id: str
    score: float


class RAGResult(BaseModel):
    question: str
    answer: str
    citations: list[Citation]
    evidence_count: int


def _compose_deterministic_answer(question: str, evidence: list[dict]) -> str:
    """Never fabricates: only concatenates the exact retrieved chunk text as the answer body."""
    return "Based on the indexed documents:\n\n" + "\n\n".join(item["text"] for item in evidence[:3])


def _compose_llm_answer(question: str, evidence: list[dict]) -> str | None:
    settings = get_settings()
    if not settings.llm_api_key:
        return None
    try:
        from app.llm.factory import get_llm_provider

        context = "\n\n".join(f"[{i + 1}] {item['text']}" for i, item in enumerate(evidence))
        prompt = (
            "Answer the question using ONLY the numbered context below. "
            "If the context does not contain the answer, say you don't know. "
            "Do not invent citations beyond the numbered context provided.\n\n"
            f"Context:\n{context}\n\nQuestion: {question}\n"
        )
        return get_llm_provider().generate(prompt)
    except Exception:
        return None


def answer_query(question: str, top_k: int = 5) -> RAGResult:
    results = search(question, top_k=top_k)
    useful = [r for r in results if r["score"] >= _SIMILARITY_THRESHOLD]

    if not useful:
        return RAGResult(question=question, answer=NO_EVIDENCE, citations=[], evidence_count=0)

    answer = _compose_llm_answer(question, useful) or _compose_deterministic_answer(question, useful)
    citations = [
        Citation(document_name=item["document_name"], chunk_id=item["chunk_id"], score=item["score"])
        for item in useful
    ]
    return RAGResult(question=question, answer=answer, citations=citations, evidence_count=len(useful))
