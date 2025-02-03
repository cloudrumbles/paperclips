# tests/test_database_service.py

import sqlite3
from datetime import datetime
from pathlib import Path
import pytest

from paperclips.db_service import DatabaseService  # adjust the import path as needed


def test_init_db_creates_table(tmp_path: Path) -> None:
    """
    test that initializing the db creates the completions table.
    """
    # use a temporary file as the database
    db_file = tmp_path / "test_completions.db"
    db_service = DatabaseService(db_path=str(db_file))
    
    # connect to the temporary database and check that the table exists
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='completions'"
    )
    table = cursor.fetchone()
    conn.close()
    
    assert table is not None, "completions table should be created"
    assert table[0] == "completions"


def test_log_completion_inserts_row(tmp_path: Path) -> None:
    """
    test that log_completion inserts a row with the correct prompt,
    completion, and a valid timestamp.
    """
    db_file = tmp_path / "test_completions.db"
    db_service = DatabaseService(db_path=str(db_file))
    
    # define sample prompt and completion
    prompt = "test prompt"
    completion = "test completion"
    
    # log the completion
    db_service.log_completion(prompt, completion)
    
    # connect to the database and query the completions table
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT prompt, completion, timestamp FROM completions"
    )
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None, "a row should have been inserted into completions"
    assert row[0] == prompt, "prompt should match"
    assert row[1] == completion, "completion should match"
    
    # check that the timestamp is in a valid iso format
    timestamp = row[2]
    try:
        parsed_timestamp = datetime.fromisoformat(timestamp)
    except ValueError:
        pytest.fail("timestamp is not in valid ISO format")
