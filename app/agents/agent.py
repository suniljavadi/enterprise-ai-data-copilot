import time

from app.agents.planner import determine_intent, select_tools
from app.agents.state import AgentState
from app.agents.tools.rag_tool import RAGToolInput, rag_tool
from app.agents.tools.sql_tool import SQLToolInput, sql_tool
from app.core.exceptions import AppError

_TOOL_REGISTRY = {
    "sql_tool": lambda question: sql_tool(SQLToolInput(question=question)),
    "rag_tool": lambda question: rag_tool(RAGToolInput(question=question)),
}

_MAX_ITERATIONS = 3


def _summarize(tool_results: list[dict]) -> str:
    parts = []
    for result in tool_results:
        if result["tool"] == "sql_tool":
            parts.append(f"Data analysis returned {result['row_count']} row(s) using {', '.join(result['tables_used'])}.")
        elif result["tool"] == "rag_tool":
            parts.append(result["answer"])
    return "\n\n".join(parts) if parts else "I could not safely answer this question with the available tools."


def run_agent(question: str) -> AgentState:
    started = time.perf_counter()
    intent = determine_intent(question)
    tools = select_tools(question)

    state = AgentState(question=question, intent=intent, selected_tools=tools)

    for tool_name in tools[:_MAX_ITERATIONS]:
        tool_fn = _TOOL_REGISTRY.get(tool_name)
        if tool_fn is None:
            state.errors.append(f"Unknown tool requested: {tool_name}")
            continue

        state.tool_calls.append({"tool": tool_name, "input": {"question": question}})
        try:
            result = tool_fn(question)
            state.tool_results.append(result)
        except AppError as exc:
            state.errors.append(f"{tool_name} failed: {exc.detail}")
        except Exception as exc:
            state.errors.append(f"{tool_name} failed: {exc.__class__.__name__}")

    state.reasoning_summary = (
        f"Selected {', '.join(tools)} based on intent '{intent}'; "
        f"{len(state.tool_results)} succeeded, {len(state.errors)} failed."
    )
    state.final_answer = _summarize(state.tool_results)
    state.execution_time_ms = round((time.perf_counter() - started) * 1000, 2)
    return state
