import os
os.environ["OPENAI_API_KEY"] = "fakekey"  # set key before importing app

import sqlite3
import json
import time
import pytest

import paperclips.app as paperclips_app  # added import to patch module-level variables
from paperclips.app import limiter
from limits.storage import MemoryStorage
# Assumes that the DatabaseService uses "completions.db" in the working directory

class FakeService:
    def get_completion(self, prompt: str) -> str:
        return "fake integration completion"

def clear_rate_limiter_storage() -> None:
    """Clear the rate limiter storage between tests."""
    if isinstance(limiter._storage, MemoryStorage):
        limiter._storage.storage.clear()
    elif hasattr(limiter._storage, "reset"):
        limiter._storage.reset()

# Use Flask test client for integration tests
@pytest.fixture(scope="function")  # changed from "module" to "function"
def client():
    # Disable rate limiting for integration tests
    paperclips_app.app.config["TESTING"] = True
    paperclips_app.app.config["RATELIMIT_ENABLED"] = False
    limiter.enabled = False
    
    # Clear any existing rate limit data
    clear_rate_limiter_storage()
    
    with paperclips_app.app.test_client() as client:
        yield client

def get_latest_log():
    # waits briefly to allow the DB write to complete
    time.sleep(0.5)
    conn = sqlite3.connect("completions.db")
    cursor = conn.cursor()
    cursor.execute("SELECT prompt, completion, timestamp FROM completions ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row

def test_invalid_json(client):
    response = client.post("/openai-completion", data="not a json", content_type="text/plain")
    assert response.status_code == 400
    assert response.get_json()["error"] == "JSON payload required"

def test_missing_prompt(client):
    response = client.post("/openai-completion", json={"text": "hello"})
    assert response.status_code == 400
    assert response.get_json()["error"] == "prompt field missing"

def test_valid_completion(monkeypatch, client):
    test_prompt = "Integration test: say this is a test"
    monkeypatch.setattr(paperclips_app, "service", FakeService())  # patch module-level variable
    monkeypatch.setattr(paperclips_app.db_service, "log_completion", lambda *args, **kwargs: None)  # bypass DB logging
    response = client.post("/openai-completion", json={"prompt": test_prompt})
    assert response.status_code == 200
    data = response.get_json()
    assert "completion" in data
    # Verify that the completion was logged in the database.
    log = get_latest_log()
    assert log is not None
    logged_prompt, logged_completion, _ = log
    assert logged_prompt == test_prompt
    assert isinstance(logged_completion, str) and len(logged_completion) > 0
