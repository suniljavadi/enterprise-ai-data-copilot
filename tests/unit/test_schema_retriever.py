from app.text_to_sql.schema_retriever import format_schema_context, select_relevant_tables


def test_selects_tables_relevant_to_revenue_question():
    tables = select_relevant_tables("What is the total revenue from orders?")
    names = {f"{t.schema_name}.{t.table_name}" for t in tables}
    assert "sales.Orders" in names


def test_revenue_synonym_matches_totalamount_column_without_literal_orders_keyword():
    tables = select_relevant_tables("What is the total revenue?")
    names = {f"{t.schema_name}.{t.table_name}" for t in tables}
    assert "sales.Orders" in names


def test_region_synonym_matches_shippingstate_column():
    tables = select_relevant_tables("Show revenue by region.")
    names = {f"{t.schema_name}.{t.table_name}" for t in tables}
    assert "sales.Orders" in names


def test_selects_tables_relevant_to_customer_question():
    tables = select_relevant_tables("Which customers have the highest loyalty tier?")
    names = {f"{t.schema_name}.{t.table_name}" for t in tables}
    assert "customer.Customers" in names


def test_returns_empty_for_blank_question():
    assert select_relevant_tables("") == []


def test_format_schema_context_includes_columns_and_foreign_keys():
    tables = select_relevant_tables("orders and order items revenue")
    context = format_schema_context(tables)
    assert "sales.Orders(" in context or "sales.OrderItems(" in context
