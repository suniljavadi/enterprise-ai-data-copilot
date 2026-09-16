from app.text_to_sql.validator import validate_sql


def test_allows_select_query():
    result = validate_sql("SELECT TOP 10 * FROM sales.Orders")
    assert result.valid
    assert result.errors == []


def test_allows_cte_query():
    result = validate_sql("WITH recent AS (SELECT 1 AS a) SELECT * FROM recent")
    assert result.valid


def test_rejects_delete():
    result = validate_sql("DELETE FROM sales.Orders")
    assert not result.valid
    assert any("not allowed" in e for e in result.errors)


def test_rejects_drop():
    result = validate_sql("DROP TABLE sales.Orders")
    assert not result.valid


def test_rejects_multiple_statements():
    result = validate_sql("SELECT * FROM sales.Orders; DROP TABLE sales.Orders")
    assert not result.valid
    assert any("single SQL statement" in e for e in result.errors)


def test_rejects_comments():
    result = validate_sql("SELECT * FROM sales.Orders -- drop everything")
    assert not result.valid
    assert any("comments" in e.lower() for e in result.errors)


def test_rejects_system_schema_access():
    result = validate_sql("SELECT * FROM sys.tables")
    assert not result.valid
    assert any("system schema" in e for e in result.errors)


def test_rejects_dangerous_function():
    result = validate_sql("EXEC xp_cmdshell 'dir'")
    assert not result.valid


def test_rejects_empty_sql():
    result = validate_sql("   ")
    assert not result.valid
    assert result.errors == ["Generated SQL is empty"]
