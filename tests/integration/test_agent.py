from app.agents.agent import run_agent
from app.rag.retriever import ingest_directory, reset_index


def setup_module():
    reset_index()
    ingest_directory("data/documents")


def test_data_question_uses_sql_tool_only():
    state = run_agent("What is the total revenue?")
    assert state.selected_tools == ["sql_tool"]
    assert len(state.tool_results) == 1
    assert state.tool_results[0]["tool"] == "sql_tool"
    assert state.tool_results[0]["row_count"] == 1
    assert not state.errors


def test_document_question_uses_rag_tool_only():
    state = run_agent("What is the refund policy for damaged products?")
    assert state.selected_tools == ["rag_tool"]
    assert state.tool_results[0]["tool"] == "rag_tool"
    assert state.tool_results[0]["citations"]


def test_analysis_question_uses_both_tools_and_merges_answer():
    state = run_agent("Why did revenue decrease and what is the refund policy?")
    tool_names = {r["tool"] for r in state.tool_results}
    assert tool_names == {"sql_tool", "rag_tool"}
    assert state.final_answer


def test_agent_never_crashes_on_out_of_scope_question():
    state = run_agent("Tell me a joke")
    assert state.final_answer
    assert state.errors
    assert "sql_tool failed" in state.errors[0]


def test_agent_records_reasoning_summary_and_latency():
    state = run_agent("What is the total revenue?")
    assert state.reasoning_summary
    assert state.execution_time_ms > 0
