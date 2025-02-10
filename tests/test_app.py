# tests/test_app.py
from typing import Any, Dict
import pytest
from flask import Flask
from flask.testing import FlaskClient
from unittest.mock import patch, MagicMock

# We'll import the factory function and db from your code
from paperclips.app import create_app, db
from paperclips.models import RequestLog, ResponseLog


@pytest.fixture(scope="module")
def test_app() -> Flask:
    """
    Create a fresh Flask app with a test config. 
    We'll use SQLite in-memory for DB tests.
    """
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "RATELIMIT_ENABLED": False  # disable rate limiting for most tests
    })
    
    # create tables in memory
    with app.app_context():
        db.create_all()
    
    yield app
    
    # teardown
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(test_app: Flask) -> FlaskClient:
    """
    This gives us a test client to send requests to the Flask app.
    """
    return test_app.test_client()


@pytest.fixture
def mock_openai_success() -> MagicMock:
    """
    A fixture to mock a successful OpenAI ChatCompletion call.
    """
    with patch("paperclips.openai_client.client.chat.completions.create") as mock_create:
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Mock completion response"))
        ]
        mock_create.return_value = mock_response
        yield mock_create


def test_valid_request(client: FlaskClient, mock_openai_success: MagicMock) -> None:
    payload = {"prompt": "Hello from test"}
    resp = client.post("/openai-completion", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.get_json()
    assert "completion" in data, "Response should include 'completion'"
    assert "request_id" in data, "Response should include 'request_id'"
    
    # check the DB
    with client.application.app_context():
        req_logs = RequestLog.query.all()
        assert len(req_logs) == 1, "Should have 1 request logged"
        resp_logs = ResponseLog.query.all()
        assert len(resp_logs) == 1, "Should have 1 response logged"


def test_missing_prompt(client: FlaskClient) -> None:
    resp = client.post("/openai-completion", json={"foo": "bar"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_invalid_prompt_type(client: FlaskClient) -> None:
    resp = client.post("/openai-completion", json={"prompt": 12345})
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_user_id_handling(client: FlaskClient, mock_openai_success: MagicMock) -> None:
    payload = {"prompt": "Hello user", "user_id": "testUser123"}
    resp = client.post("/openai-completion", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    request_id = data.get("request_id")
    with client.application.app_context():
        req_log = RequestLog.query.filter_by(id=request_id).first()
        assert req_log is not None
        assert req_log.user_id == "testUser123"


@patch("paperclips.openai_client.client.chat.completions.create", side_effect=Exception("API Error"))
def test_openai_error(mock_create: MagicMock, client: FlaskClient) -> None:
    resp = client.post("/openai-completion", json={"prompt": "trigger error"})
    assert resp.status_code == 500
    data = resp.get_json()
    assert "error" in data


def test_rate_limit(client: FlaskClient, test_app: Flask) -> None:
    """
    Demonstrate how you'd test rate limiting.
    We'll re-enable rate limiting here and make multiple requests quickly.
    """
    test_app.config["RATELIMIT_ENABLED"] = True
    test_app.config["RATELIMIT_DEFAULT"] = "2 per minute"
    
    # first request
    resp1 = client.post("/openai-completion", json={"prompt": "test1"})
    assert resp1.status_code in (200, 429)
    
    # second request
    resp2 = client.post("/openai-completion", json={"prompt": "test2"})
    assert resp2.status_code in (200, 429)
    
    # third request should fail if the first two succeeded (2/min limit)
    resp3 = client.post("/openai-completion", json={"prompt": "test3"})
    if resp1.status_code == 200 and resp2.status_code == 200:
        # we expect a 429 on the 3rd
        assert resp3.status_code == 429
    else:
        # if first or second was already 429, the third might be 429 or 200 
        # depending on how limiter handled them
        pass
