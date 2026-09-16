from pydantic import BaseModel


class AgentState(BaseModel):
    question: str
    intent: str
    selected_tools: list[str] = []
    tool_calls: list[dict] = []
    tool_results: list[dict] = []
    reasoning_summary: str = ""
    final_answer: str = ""
    errors: list[str] = []
    execution_time_ms: float = 0.0
