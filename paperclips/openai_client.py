# services/openai_client.py
from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam  # type for chat completion response
from paperclips.config import Config
from typing import List

# Create the OpenAI client
client = OpenAI(api_key=Config.OPENAI_API_KEY)

def get_chat_completion(prompt: str) -> str:
    """
    Calls OpenAI's Chat Completion API with the given prompt.
    Returns the assistant's completion text.
    """
    try:
        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ]
        response: ChatCompletion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
        )
        # Extract the completion text from the response.
        completion: str = response.choices[0].message.content or ""
        return completion
    except Exception as e:
        raise RuntimeError(f"Error calling OpenAI API: {e}") from e
