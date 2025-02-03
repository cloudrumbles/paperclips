# tests/functional/test_openai_integration.py

import pytest
from openai import APIConnectionError
from paperclips.openai_service import OpenAIChatService


# --- fake classes for simulating openai client behavior ---

class FakeChatCompletionChoice:
    def __init__(self, content: str) -> None:
        self.message = type("FakeMessage", (), {"content": content})


class FakeChatCompletion:
    def __init__(self, choices) -> None:
        self.choices = choices


class FakeChatCompletions:
    @staticmethod
    def create(model: str, messages: list[dict[str, str]]) -> FakeChatCompletion:
        # simulate a successful response by returning a fake chat completion
        return FakeChatCompletion([FakeChatCompletionChoice("test response")])


class FakeClientSuccess:
    # a fake openai client that returns a successful chat completion
    chat = type("FakeChat", (), {"completions": FakeChatCompletions})


class FakeClientAPIConnectionError:
    # a fake openai client that simulates an APIConnectionError
    class FakeChat:
        class FakeCompletions:
            @staticmethod
            def create(model: str, messages: list[dict[str, str]]) -> None:
                # raise with a dummy request argument as APIConnectionError requires it.
                raise APIConnectionError(request="dummy")
        completions = FakeCompletions
    chat = FakeChat


# --- functional tests ---

def test_get_completion_success() -> None:
    """
    test that a valid prompt returns the expected response using
    a fake successful client.
    """
    service = OpenAIChatService(client=FakeClientSuccess())
    result = service.get_completion("test prompt")
    assert result == "test response"


def test_get_completion_empty_prompt() -> None:
    """
    test that calling get_completion with an empty prompt raises a ValueError.
    """
    service = OpenAIChatService(client=FakeClientSuccess())
    with pytest.raises(ValueError) as excinfo:
        service.get_completion("")
    assert "prompt cannot be empty" in str(excinfo.value)


def test_get_completion_api_connection_error() -> None:
    """
    test that a simulated APIConnectionError is caught and re-raised as
    a RuntimeError with an appropriate message.
    """
    service = OpenAIChatService(client=FakeClientAPIConnectionError())
    with pytest.raises(RuntimeError) as excinfo:
        service.get_completion("test prompt")
    # our _parse_api_exception returns "failed to connect to openai api" for APIConnectionError
    assert "failed to connect" in str(excinfo.value)


def test_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    test that if the OPENAI_API_KEY is missing from the environment,
    the service constructor raises a ValueError.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError) as excinfo:
        OpenAIChatService()
    assert "openai api key must be set" in str(excinfo.value)
