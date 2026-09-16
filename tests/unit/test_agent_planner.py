from app.agents.planner import determine_intent, select_tools


def test_data_question_routes_to_sql_tool():
    assert select_tools("What is the total revenue from orders?") == ["sql_tool"]


def test_document_question_routes_to_rag_tool():
    assert select_tools("What is the refund policy?") == ["rag_tool"]


def test_document_question_mentioning_products_still_routes_to_rag_only():
    assert select_tools("What is the refund policy for damaged products?") == ["rag_tool"]


def test_pure_product_data_question_routes_to_sql_tool():
    assert select_tools("Which products need reorder?") == ["sql_tool"]


def test_mixed_question_routes_to_both_tools():
    tools = select_tools("What is the refund policy and total revenue?")
    assert set(tools) == {"sql_tool", "rag_tool"}


def test_analysis_question_routes_to_both_tools():
    tools = select_tools("Why did revenue decrease last month?")
    assert set(tools) == {"sql_tool", "rag_tool"}


def test_unknown_question_defaults_to_sql_tool():
    assert determine_intent("hello there") == "unknown"
    assert select_tools("hello there") == ["sql_tool"]
