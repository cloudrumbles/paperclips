import os
import logging
from typing import Any, Optional, List

from dotenv import load_dotenv
import openai
from openai import APIConnectionError, APIStatusError, APIError, RateLimitError
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env
load_dotenv(override=True)


class OpenAIChatService:
    """
    service that wraps the openai chat completion api.

    usage:
        service = OpenAIChatService()
        response = service.get_completion("hello, world!")
        print(response)
    """

    def __init__(
        self,
        model: Optional[str] = None,
        developer_message: Optional[str] = None,
        client: Optional[Any] = None,
    ) -> None:
        # Use provided client or initialize using the API key from environment
        if client is not None:
            self.client = client
        else:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("openai api key must be set in the environment")
            openai.api_key = api_key
            self.client = openai

        # Set model and developer message with defaults if not provided
        self.model = model or "gpt-4o-mini"
        self.developer_message = developer_message or "you are a helpful assistant."

    def get_completion_from_messages(self, messages: List[ChatCompletionMessageParam]) -> str:
        """
        get a chat completion using the provided list of messages.

        :param messages: list of messages, each with a 'role' and 'content'.
        :return: generated text response.
        :raises ValueError: if messages list is empty.
        :raises RuntimeError: if response format is unexpected or openai api errors occur.
        """
        if not messages:
            raise ValueError("messages list cannot be empty")

        try:
            chat_completion: ChatCompletion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
        except (APIConnectionError, RateLimitError, APIStatusError, APIError) as exc:
            error_message = self._parse_api_exception(exc)
            logger.error("openai api error: %s", error_message, exc_info=True)
            raise RuntimeError(error_message) from exc

        if not chat_completion.choices:
            raise RuntimeError("no choices returned from openai chat completion")

        try:
            result = chat_completion.choices[0].message.content
        except (IndexError, KeyError, AttributeError) as exc:
            logger.error("unexpected response format from openai chat completion", exc_info=True)
            raise RuntimeError(
                "unexpected response format from openai chat completion"
            ) from exc
        if not result:
            raise RuntimeError("empty response from openai chat completion")
        return result

    def get_completion(self, prompt: str) -> str:
        """
        get a chat completion using the provided prompt.

        :param prompt: user prompt to send to the openai chat completion api.
        :return: generated text response.
        :raises ValueError: if prompt is empty.
        :raises RuntimeError: if response format is unexpected or openai api errors occur.
        """
        if not prompt:
            raise ValueError("prompt cannot be empty")

        try:
            chat_completion: ChatCompletion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "developer", "content": self.developer_message},
                    {"role": "user", "content": prompt},
                ],
            )
        except (APIConnectionError, RateLimitError, APIStatusError, APIError) as exc:
            error_message: str = self._parse_api_exception(exc)
            logger.error("openai api error: %s", error_message, exc_info=True)
            raise RuntimeError(error_message) from exc

        if not chat_completion.choices:
            raise RuntimeError("no choices returned from openai chat completion")

        try:
            result: Any = chat_completion.choices[0].message.content
        except (IndexError, KeyError, AttributeError) as exc:
            logger.error("unexpected response format from openai chat completion", exc_info=True)
            raise RuntimeError(
                "unexpected response format from openai chat completion"
            ) from exc

        return result

    def _parse_api_exception(self, exc: Exception) -> str:
        """
        parse api exceptions into a user-friendly error message.
        """
        if isinstance(exc, APIConnectionError):
            return "failed to connect to openai api"
        elif isinstance(exc, RateLimitError):
            return "rate limit exceeded for openai api"
        elif isinstance(exc, APIStatusError):
            return f"openai api error: {exc.status_code} - {exc.response.json()}"
        elif isinstance(exc, APIError):
            return "an openai api error occurred"
        return "an unknown openai api error occurred"


if __name__ == "__main__":
    service = OpenAIChatService()
    try:
        output = service.get_completion("say this is a test")
        print(output)
    except RuntimeError as err:
        logger.error("error occurred: %s", err)
        print(f"error occurred: {err}")
