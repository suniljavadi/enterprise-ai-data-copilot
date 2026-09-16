from app.core import security
from app.core.config import Settings
from app.core.security import Role


def test_public_demo_key_is_viewer_only(monkeypatch):
    monkeypatch.setattr(security, "get_settings", lambda: Settings(public_demo_key="demo-viewer-2026"))

    directory = security._load_api_key_directory()

    assert directory["demo-viewer-2026"].name == "public-demo"
    assert directory["demo-viewer-2026"].role is Role.VIEWER