import sys
import types
import pytest
from unittest.mock import MagicMock

# Mock Redis so tests work without Redis running
@pytest.fixture(autouse=True)
def mock_redis():
    store = {}
    mock_client = MagicMock()

    def mock_get(key):
        return store.get(key)

    def mock_setex(key, ttl, value):
        store[key] = value

    def mock_keys(pattern):
        prefix = pattern.replace("*", "")
        return [k for k in store if k.startswith(prefix)]

    def mock_delete(*keys):
        for k in keys:
            store.pop(k, None)

    mock_client.get.side_effect = mock_get
    mock_client.setex.side_effect = mock_setex
    mock_client.keys.side_effect = mock_keys
    mock_client.delete.side_effect = mock_delete

    redis_stub = types.ModuleType("redis")
    redis_stub.from_url = MagicMock(return_value=mock_client)
    sys.modules["redis"] = redis_stub
    if "services.cache_service" in sys.modules:
        del sys.modules["services.cache_service"]
    yield mock_client

def test_cache_miss_returns_none():
    from services.cache_service import get_cached, clear_cache
    clear_cache()
    result = get_cached("question never asked before xyz123")
    assert result is None

def test_cache_set_and_get():
    from services.cache_service import get_cached, set_cached
    set_cached("test question", "test answer")
    result = get_cached("test question")
    assert result == "test answer"

def test_cache_different_queries_dont_collide():
    from services.cache_service import get_cached, set_cached
    set_cached("question one", "answer one")
    set_cached("question two", "answer two")
    assert get_cached("question one") == "answer one"
    assert get_cached("question two") == "answer two"

def test_clear_cache_removes_all_keys():
    from services.cache_service import get_cached, set_cached, clear_cache
    set_cached("q1", "a1")
    set_cached("q2", "a2")
    cleared = clear_cache()
    assert cleared >= 2
