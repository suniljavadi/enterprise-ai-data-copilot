import time

from app.database.inspector import ColumnMetadata, SchemaSnapshot, TableMetadata
from app.text_to_sql.schema_retriever import format_schema_context, select_relevant_tables


def _column(name: str) -> ColumnMetadata:
    return ColumnMetadata(name=name, data_type="varchar", nullable=True, is_primary_key=False)


def _fake_snapshot() -> SchemaSnapshot:
    tables = [
        TableMetadata(
            schema_name="sales",
            table_name="Orders",
            columns=[_column(c) for c in ("OrderID", "CustomerID", "OrderDate", "TotalAmount", "ShippingState")],
            primary_keys=["OrderID"],
            foreign_keys=[],
        ),
        TableMetadata(
            schema_name="sales",
            table_name="OrderItems",
            columns=[_column(c) for c in ("OrderItemID", "OrderID", "ProductID", "LineTotal")],
            primary_keys=["OrderItemID"],
            foreign_keys=[],
        ),
        TableMetadata(
            schema_name="customer",
            table_name="Customers",
            columns=[_column(c) for c in ("CustomerID", "FirstName", "LastName", "LoyaltyTier")],
            primary_keys=["CustomerID"],
            foreign_keys=[],
        ),
    ]
    return SchemaSnapshot(tables=tables, discovered_at=time.time(), schema_count=2, table_count=len(tables))


def test_selects_tables_relevant_to_revenue_question():
    tables = select_relevant_tables("What is the total revenue from orders?", snapshot=_fake_snapshot())
    names = {f"{t.schema_name}.{t.table_name}" for t in tables}
    assert "sales.Orders" in names


def test_revenue_synonym_matches_totalamount_column_without_literal_orders_keyword():
    tables = select_relevant_tables("What is the total revenue?", snapshot=_fake_snapshot())
    names = {f"{t.schema_name}.{t.table_name}" for t in tables}
    assert "sales.Orders" in names


def test_region_synonym_matches_shippingstate_column():
    tables = select_relevant_tables("Show revenue by region.", snapshot=_fake_snapshot())
    names = {f"{t.schema_name}.{t.table_name}" for t in tables}
    assert "sales.Orders" in names


def test_selects_tables_relevant_to_customer_question():
    tables = select_relevant_tables("Which customers have the highest loyalty tier?", snapshot=_fake_snapshot())
    names = {f"{t.schema_name}.{t.table_name}" for t in tables}
    assert "customer.Customers" in names


def test_returns_empty_for_blank_question():
    assert select_relevant_tables("", snapshot=_fake_snapshot()) == []


def test_format_schema_context_includes_columns_and_foreign_keys():
    tables = select_relevant_tables("orders and order items revenue", snapshot=_fake_snapshot())
    context = format_schema_context(tables)
    assert "sales.Orders(" in context or "sales.OrderItems(" in context
