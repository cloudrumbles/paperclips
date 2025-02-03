import sqlite3
from datetime import datetime, timezone
from typing import Optional, List, Dict

class DatabaseService:
    def __init__(self, db_path: str = "completions.db") -> None:
        self.db_path = db_path
        self.init_db()

    def init_db(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS completions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        prompt TEXT NOT NULL,
                        completion TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        user_id TEXT
                    )
                    """
                )
        except sqlite3.Error as e:
            raise RuntimeError("Failed to initialize database") from e

    def log_completion(
        self, prompt: str, completion: str, user_id: Optional[str] = None
    ) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO completions (prompt, completion, timestamp, user_id) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        prompt,
                        completion,
                        datetime.now(timezone.utc).isoformat(),
                        user_id,
                    ),
                )
        except sqlite3.Error as e:
            raise RuntimeError("Failed to log completion") from e

    def get_conversation(self, user_id: str) -> List[Dict[str, str]]:
        """
        Retrieve conversation history for a given user_id as a list of messages.
        Each turn consists of a user message and an assistant message.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT prompt, completion FROM completions "
                    "WHERE user_id = ? ORDER BY timestamp ASC",
                    (user_id,),
                )
                rows = cursor.fetchall()
        except sqlite3.Error as e:
            raise RuntimeError("Failed to retrieve conversation history") from e

        messages: List[Dict[str, str]] = []
        for row in rows:
            user_prompt, assistant_completion = row
            messages.append({"role": "user", "content": user_prompt})
            messages.append(
                {"role": "assistant", "content": assistant_completion}
            )
        return messages

if __name__ == "__main__":
    db_service = DatabaseService()
    # Example usage (will likely be empty initially)
    conversation = db_service.get_conversation("example_user")
    print(conversation)