import os

import requests
import streamlit as st


def _config(key: str, default: str = "") -> str:
    """Reads from Streamlit Cloud secrets first, then falls back to env vars (local/Docker)."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError, st.errors.StreamlitAPIException):
        return os.getenv(key, default)


API_BASE_URL = _config("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Enterprise AI Data Copilot", layout="wide")
st.title("Enterprise AI Data Copilot")

with st.sidebar:
    st.subheader("Access")
    api_key = st.text_input(
        "API Key", value=_config("API_KEY", ""), type="password",
        help="This is the application access key that determines your role. It is not an LLM or OpenAI key.",
    )
    with st.expander("How to access this app"):
        st.markdown(
            "**Hosted app**\n\n"
            "Use a deployment access key provided by the app owner. Local `dev-...` keys do not work here.\n\n"
            "**Local development**\n\n"
            "Copy `.env.example` to `.env`, then use its `dev-viewer-key`, `dev-analyst-key`, or `dev-admin-key`.\n\n"
            "**Invalid API key?**\n\n"
            "Check that you used the correct environment's key and that no spaces were copied before or after it."
        )
    st.caption("Use the least-privileged key for your task. Never share access keys in questions or screenshots.")


def call_api(method: str, path: str, json: dict | None = None) -> tuple[int, dict]:
    try:
        response = requests.request(
            method, f"{API_BASE_URL}{path}", json=json, timeout=60,
            headers={"X-API-Key": api_key} if api_key else {},
        )
        return response.status_code, response.json()
    except requests.RequestException as exc:
        return 0, {"detail": f"Could not reach API at {API_BASE_URL}: {exc}"}


def render_api_error(status: int, body: dict) -> None:
    if status == 401:
        st.error("Access key not recognized")
        st.info(
            "This hosted app requires a deployment access key. Local `dev-...` keys work only when running the "
            "project locally. Check for copied spaces, then ask the app owner for the correct hosted-app key."
        )
    elif status == 403:
        st.error("Your access key does not have permission for this action")
        st.info("Use a key with the required role, or choose a viewer-supported workflow such as Ask Data or Ask Documents.")
    elif status == 503:
        st.error("The database is temporarily unavailable")
        st.info("Azure SQL may be resuming from idle state. Wait a moment and try again.")
    else:
        st.error(body.get("detail", "Request failed"))


def render_feedback(query_id: int | None) -> None:
    if query_id is None:
        return
    st.caption("Was this answer correct?")
    cols = st.columns(6)
    for i, col in enumerate(cols[:5]):
        if col.button(f"{i + 1}⭐", key=f"rate-{query_id}-{i + 1}"):
            status, _ = call_api("POST", "/feedback", {"query_id": query_id, "rating": i + 1})
            if status == 200:
                st.success("Feedback recorded")
            else:
                st.warning("Feedback could not be recorded")


tab_data, tab_docs, tab_agent = st.tabs(["Ask Data", "Ask Documents", "Agent Mode"])

with tab_data:
    st.subheader("Ask a question about your business data")
    question = st.text_input("Question", placeholder="What is the total revenue?", key="sql_question")
    if st.button("Run Query", key="sql_run") and question:
        status, body = call_api("POST", "/sql/query", {"question": question})
        if status != 200:
            render_api_error(status, body)
        else:
            st.markdown("**Generated SQL**")
            st.code(body["sql"], language="sql")
            st.caption(body["explanation"])

            st.markdown("**Results**")
            if body["rows"]:
                st.dataframe(body["rows"], use_container_width=True)
            else:
                st.info("No rows returned")

            metric_cols = st.columns(3)
            metric_cols[0].metric("Rows returned", body["row_count"])
            metric_cols[1].metric("Execution time (ms)", body["execution_time_ms"])
            metric_cols[2].metric("Tables used", len(body["tables_used"]))

            render_feedback(body.get("query_id"))

with tab_docs:
    st.subheader("Ask a question about indexed documents")
    if st.button("Re-index documents", key="rag_ingest"):
        status, body = call_api("POST", "/rag/ingest")
        if status == 200:
            st.success(f"Indexed {body['total_chunks']} chunk(s) across {len(body['documents_indexed'])} document(s)")
        else:
            render_api_error(status, body)

    doc_question = st.text_input(
        "Question", placeholder="What is the refund policy for damaged products?", key="rag_question"
    )
    if st.button("Ask", key="rag_run") and doc_question:
        status, body = call_api("POST", "/rag/query", {"question": doc_question})
        if status != 200:
            render_api_error(status, body)
        else:
            st.markdown("**Answer**")
            st.write(body["answer"])

            st.markdown("**Sources**")
            if body["citations"]:
                for citation in body["citations"]:
                    st.caption(f"{citation['document_name']} (score: {citation['score']})")
            else:
                st.info("No supporting evidence found")

with tab_agent:
    st.subheader("Ask the agent (it decides which tools to use)")
    agent_question = st.text_input(
        "Question", placeholder="Why did revenue decrease and what is the refund policy?", key="agent_question"
    )
    if st.button("Ask Agent", key="agent_run") and agent_question:
        status, body = call_api("POST", "/agent/query", {"question": agent_question})
        if status != 200:
            render_api_error(status, body)
        else:
            st.markdown(f"**Intent:** {body['intent']} · **Tools used:** {', '.join(body['selected_tools'])}")
            st.markdown("**Answer**")
            st.write(body["final_answer"])

            with st.expander("Reasoning and tool details"):
                st.caption(body["reasoning_summary"])
                for result in body["tool_results"]:
                    st.json(result)
                if body["errors"]:
                    st.warning("\n".join(body["errors"]))
                st.caption(f"Execution time: {body['execution_time_ms']} ms")
