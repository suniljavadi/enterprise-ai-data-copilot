from pydantic import BaseModel

from app.rag.pipeline import answer_query


class RAGToolInput(BaseModel):
    question: str


def rag_tool(tool_input: RAGToolInput) -> dict:
    result = answer_query(tool_input.question)
    return {
        "tool": "rag_tool",
        "answer": result.answer,
        "citations": [c.model_dump() for c in result.citations],
        "evidence_count": result.evidence_count,
    }
