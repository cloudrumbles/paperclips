# app.py
from flask import Flask, request, jsonify, Response, make_response
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from paperclips.config import Config
from paperclips.models import db, RequestLog, ResponseLog
from paperclips.openai_client import get_chat_completion
from typing import Any, Dict

def create_app() -> Flask:
    app: Flask = Flask(__name__)
    app.config.from_object(Config)

    # Initialize database and migrations
    db.init_app(app)
    Migrate(app, db)

    # Set up rate limiting
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=[Config.RATELIMIT_DEFAULT],
    )

    @app.route("/openai-completion", methods=["POST"])
    @limiter.limit("5 per minute")
    def openai_completion() -> Response: #type: ignore
        if not request.is_json:
            return make_response(jsonify({"error": "Request must be JSON"}), 400)

        data: Dict[str, Any] = request.get_json()
        prompt: Any = data.get("prompt")
        user_id: Any = data.get("user_id")

        if not isinstance(prompt, str):
            response = jsonify({"error": "Missing or invalid 'prompt' in request data"})
            response.status_code = 400
            return response

        # Log the incoming request
        req_log: RequestLog = RequestLog(
            prompt=prompt,
            user_id=str(user_id) if user_id is not None else None
        )
        db.session.add(req_log)
        db.session.commit()  # commit to generate the request id

        try:
            completion_text: str = get_chat_completion(prompt)
        except Exception as e:
            return make_response(jsonify({"error": str(e)}), 500)

        # Log the OpenAI response
        resp_log: ResponseLog = ResponseLog(request_id=req_log.id, completion=completion_text)
        db.session.add(resp_log)
        db.session.commit()

        return jsonify({
            "completion": completion_text,
            "request_id": req_log.id
        })

    return app

if __name__ == "__main__":
    app_instance: Flask = create_app()
    app_instance.run(host="0.0.0.0", port=5000, debug=True)
