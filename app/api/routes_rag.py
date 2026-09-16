from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.security import Role, require_role
from app.rag.pipeline import RAGResult, answer_query
from app.rag.retriever import get_vector_store, ingest_directory

router = APIRouter(prefix="/rag", tags=["rag"])


class RAGQueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class IngestResponse(BaseModel):
    documents_indexed: list[dict]
    total_chunks: int


@router.post("/ingest", response_model=IngestResponse, dependencies=[Depends(require_role(Role.ADMIN))])
def ingest() -> IngestResponse:
    documents = ingest_directory()
    return IngestResponse(documents_indexed=documents, total_chunks=get_vector_store().size)


@router.post("/query", response_model=RAGResult, dependencies=[Depends(require_role(Role.ADMIN, Role.ANALYST, Role.VIEWER))])
def query(request: RAGQueryRequest) -> RAGResult:
    return answer_query(request.question, top_k=request.top_k)
