"""Unit tests for configuration management."""
import pytest
from src.core.config import Settings


def test_config_defaults():
    s = Settings()
    assert s.PROJECT_NAME == "AI-Powered Student Achievement Intelligence Platform"
    assert s.APP_VERSION == "1.0.0"
    assert s.EMBEDDING_DIMENSION == 384
    assert s.WEIGHT_SEMANTIC + s.WEIGHT_SKILL + s.WEIGHT_DOMAIN + s.WEIGHT_URGENCY == pytest.approx(1.0)


def test_async_database_url_conversion():
    s = Settings(DATABASE_URL="sqlite:///test.db")
    assert s.get_async_database_url() == "sqlite+aiosqlite:///test.db"

    s_pg = Settings(DATABASE_URL="postgresql://user:pass@localhost:5432/db")
    assert s_pg.get_async_database_url() == "postgresql+asyncpg://user:pass@localhost:5432/db"
