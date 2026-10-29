import logging

from app.observability import telemetry


def test_observability_failures_do_not_log_exception_details(monkeypatch, caplog):
    def fail_session():
        raise RuntimeError("sensitive connection detail")

    monkeypatch.setattr(telemetry, "get_session", fail_session)

    with caplog.at_level(logging.WARNING, logger="app.observability.telemetry"):
        assert telemetry._safe_execute("SELECT 1", {}) is None

    assert "RuntimeError" in caplog.text
    assert "sensitive connection detail" not in caplog.text
