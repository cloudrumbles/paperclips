import pytest
from paperclips.app import app, service, db_service, limiter
from limits.storage import MemoryStorage  # Import MemoryStorage for type checking

def clear_rate_limiter_storage() -> None:
    """
    Clear the rate limiter storage.
    If using MemoryStorage, clear its underlying dict.
    Otherwise, use reset() if available.
    """
    if isinstance(limiter._storage, MemoryStorage):
        # Clear the underlying dictionary for in-memory storage
        limiter._storage.storage.clear()
    elif hasattr(limiter._storage, "reset"):
        limiter._storage.reset()


@pytest.fixture
def client():
    # Set testing config and disable rate limiting for most tests
    app.config["TESTING"] = True
    app.config["RATELIMIT_ENABLED"] = False
    limiter.enabled = False

    # Clear the limiter storage to remove any leftover state
    clear_rate_limiter_storage()

    with app.test_client() as client:
        yield client


def test_missing_json(client):
    response = client.post(
        "/openai-completion",
        data="not a json",
        content_type="text/plain"
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "JSON payload required"


def test_missing_prompt_field(client):
    response = client.post("/openai-completion", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "prompt field missing"


def test_successful_completion(client, monkeypatch):
    # Monkeypatch service.get_completion to return a dummy result
    def dummy_get_completion(prompt: str) -> str:
        return "dummy completion"
    monkeypatch.setattr(service, "get_completion", dummy_get_completion)

    # Track calls to db_service.log_completion in a list
    calls: list[tuple[str, str, str | None]] = []

    def dummy_log_completion(prompt: str, completion: str, user_id: str | None) -> None:
        calls.append((prompt, completion, user_id))
    monkeypatch.setattr(db_service, "log_completion", dummy_log_completion)

    payload = {"prompt": "Hello", "user_id": "user123"}
    response = client.post("/openai-completion", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["completion"] == "dummy completion"
    # Verify that our dummy logging was called correctly
    assert calls == [("Hello", "dummy completion", "user123")]


def test_service_exception(client, monkeypatch):
    # Monkeypatch service.get_completion to simulate an exception
    def dummy_get_completion(prompt: str) -> str:
        raise Exception("Test error")
    monkeypatch.setattr(service, "get_completion", dummy_get_completion)

    payload = {"prompt": "Hello"}
    response = client.post("/openai-completion", json=payload)
    assert response.status_code == 500
    data = response.get_json()
    assert data["error"] == "Test error"


def test_rate_limiting(client, monkeypatch):
    # Re-enable rate limiting for this test only
    app.config["RATELIMIT_ENABLED"] = True
    limiter.enabled = True

    # Clear the limiter storage so we start fresh
    clear_rate_limiter_storage()

    # Monkeypatch service and db_service to bypass external calls
    monkeypatch.setattr(service, "get_completion", lambda p: "dummy")
    monkeypatch.setattr(db_service, "log_completion", lambda p, c, u: None)

    # Our limit is 10 per minute, so 10 requests should pass...
    for i in range(10):
        response = client.post("/openai-completion", json={"prompt": "test"})
        assert response.status_code == 200

    # The 11th request should hit the rate limit (HTTP 429)
    response = client.post("/openai-completion", json={"prompt": "test"})
    assert response.status_code == 429
