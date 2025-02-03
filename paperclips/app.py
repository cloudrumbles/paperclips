from flask import Flask, request, jsonify, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from paperclips.openai_service import OpenAIChatService
from paperclips.db_service import DatabaseService
from typing import List

from openai.types.chat import ChatCompletionMessageParam

app = Flask(__name__)

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="memory://",  # explicitly configure memory storage
    default_limits=["10 per minute"],  # global limit per IP
)

service = OpenAIChatService()
db_service = DatabaseService()

@app.route("/openai-completion", methods=["POST"])
@limiter.limit("10 per minute")
def openai_completion() -> tuple[Response, int]:
    if not request.is_json:
        return jsonify({"error": "JSON payload required"}), 400

    data = request.get_json()
    if "prompt" not in data:
        return jsonify({"error": "prompt field missing"}), 400

    prompt: str = data["prompt"]
    user_id: str | None = data.get("user_id")

    # Build the message history starting with the system message.
    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": service.developer_message}
    ]
    if user_id:
        try:
            conversation_history = db_service.get_conversation(user_id)
            messages.extend(conversation_history)
        except Exception as db_err:
            app.logger.error("Error fetching conversation history: %s", db_err)
            return (
                jsonify({"error": "failed to retrieve conversation history"}),
                500,
            )
    messages.append({"role": "user", "content": prompt})

    try:
        completion: str = service.get_completion_from_messages(messages)
        # Log only the current turn.
        db_service.log_completion(prompt, completion, user_id)
    except Exception as exc:
        app.logger.error("Error during OpenAI completion: %s", exc)
        return jsonify({"error": str(exc)}), 500

    return jsonify({"completion": completion}), 200

if __name__ == "__main__":
    app.run(debug=True)
