from app.database.inspector import clear_schema_cache, discover_schema, get_cached_schema


def setup_function():
    clear_schema_cache()


def test_discover_schema_finds_expected_business_schemas():
    snapshot = discover_schema()
    schema_names = {table.schema_name for table in snapshot.tables}
    for expected in ("catalog", "customer", "sales", "inventory", "finance", "hr", "marketing", "ai"):
        assert expected in schema_names


def test_discover_schema_excludes_system_schemas():
    snapshot = discover_schema()
    schema_names = {table.schema_name for table in snapshot.tables}
    assert "sys" not in schema_names
    assert "INFORMATION_SCHEMA" not in schema_names


def test_orders_table_has_expected_columns_and_primary_key():
    snapshot = discover_schema()
    orders = next(t for t in snapshot.tables if t.schema_name == "sales" and t.table_name == "Orders")
    assert "OrderID" in orders.primary_keys
    column_names = {c.name for c in orders.columns}
    assert "OrderDate" in column_names
    assert "TotalAmount" in column_names


def test_purchase_order_items_has_foreign_keys():
    snapshot = discover_schema()
    items = next(
        t for t in snapshot.tables if t.schema_name == "inventory" and t.table_name == "PurchaseOrderItems"
    )
    referred_tables = {fk.referred_table for fk in items.foreign_keys}
    assert "PurchaseOrders" in referred_tables
    assert "Products" in referred_tables


def test_cache_reuses_snapshot_until_refresh():
    first = get_cached_schema()
    second = get_cached_schema()
    assert first.discovered_at == second.discovered_at

    refreshed = get_cached_schema(force_refresh=True)
    assert refreshed.discovered_at >= first.discovered_at
