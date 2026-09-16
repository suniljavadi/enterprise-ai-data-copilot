import re

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

_DOCUMENT_KEYWORDS = {"policy", "refund", "warranty", "shipping", "return", "documentation", "terms"}
_DATA_KEYWORDS = {
    "revenue", "sales", "order", "orders", "customer", "customers",
    "employee", "inventory", "campaign", "commission", "invoice", "payment", "shipment",
}
# "product"/"products" appear in both analytical questions ("top products by revenue")
# and policy questions ("refund policy for damaged products"), so they only count as a
# data signal when no document keyword is present, to avoid misrouting policy questions.
_WEAK_DATA_KEYWORDS = {"product", "products"}
_ANALYSIS_KEYWORDS = {"why", "decrease", "increase", "decline", "trend", "compare", "cause"}


def determine_intent(question: str) -> str:
    tokens = set(_TOKEN_PATTERN.findall(question.lower()))
    wants_docs = bool(tokens & _DOCUMENT_KEYWORDS)
    wants_data = bool(tokens & _DATA_KEYWORDS) or (bool(tokens & _WEAK_DATA_KEYWORDS) and not wants_docs)
    wants_analysis = bool(tokens & _ANALYSIS_KEYWORDS)

    if wants_analysis and wants_data:
        return "analysis"
    if wants_data and wants_docs:
        return "mixed"
    if wants_docs:
        return "documents"
    if wants_data:
        return "data"
    return "unknown"


def select_tools(question: str) -> list[str]:
    """Deterministic planner: decides tools from question content instead of blindly calling all of them."""
    intent = determine_intent(question)
    return {
        "data": ["sql_tool"],
        "documents": ["rag_tool"],
        "mixed": ["sql_tool", "rag_tool"],
        "analysis": ["sql_tool", "rag_tool"],
        "unknown": ["sql_tool"],
    }[intent]
