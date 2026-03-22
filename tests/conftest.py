import pytest
import os
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

os.environ["OPENAI_API_KEY"]      = "test-key"
os.environ["PINECONE_API_KEY"]    = "test-key"
os.environ["PINECONE_INDEX_NAME"] = "test-index"
os.environ["API_SECRET_KEY"]      = "test-api-key"
os.environ["TAVILY_API_KEY"]      = "test-key"
os.environ["LANGCHAIN_API_KEY"]   = "test-key"
os.environ["DATABASE_URL"]        = "sqlite:///./test.db"
os.environ["REDIS_URL"]           = "redis://localhost:6379"

@pytest.fixture(scope="session")
def client():
    # Create test DB tables for SQLite before importing the app
    from sqlalchemy import create_engine
    from core_backend.models import Base
    engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    # Mock heavy dependencies before importing app
    with patch("services.rag_service.BasicRAGService") as mock_rag, \
         patch("pinecone.Pinecone") as mock_pinecone:

        mock_rag.return_value.query.return_value = {
            "report": "Test report content",
            "cache_hit": False,
            "signal_label": "EARNINGS",
            "signal_confidence": 0.87
        }

        from main import app
        return TestClient(app)

@pytest.fixture
def auth_headers():
    return {"X-API-Key": "test-api-key"}
