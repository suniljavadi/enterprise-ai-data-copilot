import os
from urllib.parse import quote

import requests
import streamlit as st


def _config(key: str, default: str = "") -> str:
    """Reads from Streamlit Cloud secrets first, then falls back to env vars (local/Docker)."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError, st.errors.StreamlitAPIException):
        return os.getenv(key, default)


API_BASE_URL = _config("API_BASE_URL", "http://localhost:8000")
PUBLIC_DEMO_VIEWER_KEY = "demo-viewer-2026"
ACCESS_REQUEST_EMAIL = "javadisunil@gmail.com"

st.set_page_config(page_title="Enterprise AI Data Copilot", layout="wide")
st.title("Enterprise AI Data Copilot")
st.caption("Ask Data for business metrics, Ask Documents for policies, or Agent Mode for questions that need both.")

with st.sidebar:
    st.subheader("Access")
    api_key = st.text_input(
        "API Key", value=_config("API_KEY", ""), type="password",
        help="This is the application access key that determines your role. It is not an LLM or OpenAI key.",
    )
    with st.expander("How to access this app"):
        st.markdown(
            "This is a role-based application. To use it, request an access key from the app owner for the role "
            "you need: **Viewer** for business questions, **Analyst** for data and schema tools, or **Admin** for "
            "management actions.\n\n"
            "If your key is rejected, confirm that you received the correct role-based key and that it was copied "
            "without extra spaces."
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
            "This is a role-based application. Ask the app owner for an access key that matches the role you need, "
            "then check that it was copied without extra spaces."
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


tab_data, tab_docs, tab_agent, tab_demo, tab_request = st.tabs(
    ["Ask Data", "Ask Documents", "Agent Mode", "Demo Access", "Request Access"]
)

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
    if st.button("Re-index documents (Admin only)", key="rag_ingest", help="Only admin access keys can refresh the document index."):
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

with tab_demo:
    st.subheader("Public Demo Access")
    st.info("This Viewer key is intentionally public for testing the demo with synthetic data.")
    st.code(PUBLIC_DEMO_VIEWER_KEY)
    st.caption("It can ask business and document questions, but cannot access schema, raw SQL, or management actions.")

with tab_request:
    st.subheader("Request Role-Based Access")
    st.write("Request an access key for the role you need. The app owner reviews each request before issuing a key.")
    with st.form("access_request_form"):
        requester_name = st.text_input("Name")
        requester_email = st.text_input("Email address")
        requested_role = st.selectbox(
            "Requested role",
            ["Viewer - business questions", "Analyst - data and schema tools", "Admin - management actions"],
        )
        request_reason = st.text_area("Why do you need access?", placeholder="Briefly describe your testing or business need.")
        request_submitted = st.form_submit_button("Prepare Access Request")

    if request_submitted:
        if not requester_name.strip() or "@" not in requester_email or not request_reason.strip():
            st.error("Enter your name, a valid email address, and a brief reason for access.")
        else:
            subject = quote(f"Enterprise AI Data Copilot access request - {requested_role.split(' - ')[0]}")
            body = quote(
                f"Name: {requester_name.strip()}\n"
                f"Email: {requester_email.strip()}\n"
                f"Requested role: {requested_role}\n\n"
                f"Reason for access:\n{request_reason.strip()}"
            )
            st.success("Your request is ready to send to the app owner.")
            st.link_button("Email Access Request", f"mailto:{ACCESS_REQUEST_EMAIL}?subject={subject}&body={body}")
