"""
LangGraph persistence Checkpointer (SqliteSaver singleton).

Usage:
    from storage.checkpointer import get_checkpointer
    checkpointer = get_checkpointer()

Depends on: pip install langgraph-checkpoint-sqlite
Falls back to MemorySaver if package is not installed.
"""
import os
import sqlite3

_checkpointer = None


def get_checkpointer():
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    from configs.path_config import OTHER_PATH
    db_path = OTHER_PATH["checkpoint_db"]
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
        _checkpointer = SqliteSaver(conn)
    except ImportError:
        from langgraph.checkpoint.memory import MemorySaver
        _checkpointer = MemorySaver()
        print(
            "[Checkpointer] Warning: langgraph-checkpoint-sqlite not installed, using MemorySaver.\n"
            "  Install with: pip install langgraph-checkpoint-sqlite"
        )

    return _checkpointer
