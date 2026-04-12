import pytest
import os
import sys
import types
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

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

    mock_instance = MagicMock()
    mock_instance.query.return_value = {
        "report": "Test report content",
        "cache_hit": False,
        "signal_label": "EARNINGS",
        "signal_confidence": 0.87,
        "contexts": [],
    }
    rag_stub = types.ModuleType("services.rag_service")
    rag_stub.BasicRAGService = MagicMock(return_value=mock_instance)
    sys.modules["services.rag_service"] = rag_stub

    pine_stub = types.ModuleType("pinecone")
    pine_stub.Pinecone = MagicMock()
    sys.modules["pinecone"] = pine_stub

    from main import app
    return TestClient(app)

@pytest.fixture
def auth_headers():
    return {"X-API-Key": "test-api-key"}
