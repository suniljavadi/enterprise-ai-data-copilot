from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import Role, require_role
from app.observability.telemetry import record_feedback

router = APIRouter(tags=["feedback"])


class FeedbackRequest(BaseModel):
    query_id: int
    rating: int | None = Field(default=None, ge=1, le=5)
    is_correct: bool | None = None
    comment: str | None = Field(default=None, max_length=1000)


@router.post("/feedback", dependencies=[Depends(require_role(Role.ADMIN, Role.ANALYST, Role.VIEWER))])
def submit_feedback(request: FeedbackRequest) -> dict:
    recorded = record_feedback(request.query_id, request.rating, request.is_correct, request.comment)
    if not recorded:
        raise HTTPException(status_code=503, detail="Feedback storage is currently unavailable")
    return {"status": "recorded", "query_id": request.query_id}
