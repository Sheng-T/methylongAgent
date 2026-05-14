"""
User / Session / Message persistence (SQLite).

Table structure:
  users    — user_name (primary key), uid (internal integer ID), password_hash, lang, created_at
  sessions — session_id, user_name, name, thread_id, created_at
  messages — id, session_id, role, content, thinking, created_at

Notes:
- user_name: the login name entered by the user
- uid: internal auto-increment integer ID, used for filesystem directory naming
- thread_id format: "{user_name}::{session_id}"
"""

import hashlib
import hmac
import os
import secrets
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List, Optional


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return salt.hex() + ":" + key.hex()


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, key_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
        return hmac.compare_digest(key.hex(), key_hex)
    except Exception:
        return False


class SessionStore:
    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._db_path = db_path
        self._conn = self._new_conn()
        self._init_tables()

    def _new_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def __del__(self):
        self.close()

    def _reconnect(self):
        try:
            self._conn.close()
        except Exception:
            pass
        self._conn = self._new_conn()

    def _init_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_name     TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL DEFAULT '',
                lang          TEXT DEFAULT 'zh_CN',
                uid           INTEGER UNIQUE,
                created_at    TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_name  TEXT NOT NULL,
                name       TEXT NOT NULL,
                thread_id  TEXT UNIQUE NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_name) REFERENCES users(user_name)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                thinking   TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
        """)
        self._conn.commit()

        try:
            self._conn.execute("SELECT uid FROM users LIMIT 1")
        except sqlite3.OperationalError:
            print("[SessionStore] add uid to users table...")
            self._conn.execute("ALTER TABLE users ADD COLUMN uid INTEGER")
            self._conn.commit()

        self._conn.execute("UPDATE users SET uid = rowid WHERE uid IS NULL")
        self._conn.commit()
        self._conn.execute("UPDATE users SET uid = rowid WHERE uid IS NULL OR uid = 0")
        self._conn.commit()

        try:
            self._conn.execute("SELECT metadata FROM messages LIMIT 1")
        except sqlite3.OperationalError:
            self._conn.execute("ALTER TABLE messages ADD COLUMN metadata TEXT DEFAULT ''")
            self._conn.commit()

    # ── User ──────────────────────────────────────────────────────────────────

    def get_or_create_user(self, user_name: str) -> str:
        self._conn.execute(
            "INSERT OR IGNORE INTO users (user_name) VALUES (?)", (user_name,)
        )
        self._conn.commit()
        return user_name

    def get_user_uid(self, user_name: str) -> Optional[int]:
        row = self._conn.execute(
            "SELECT uid FROM users WHERE user_name=?", (user_name,)
        ).fetchone()
        return row["uid"] if row else None

    def verify_login(self, user_name: str, password: str) -> bool:
        row = self._conn.execute(
            "SELECT password_hash FROM users WHERE user_name=?", (user_name,)
        ).fetchone()
        if not row:
            return False
        return _verify_password(password, row["password_hash"])

    def set_user_password(self, user_name: str, password: str):
        self._conn.execute(
            "UPDATE users SET password_hash=? WHERE user_name=?",
            (_hash_password(password), user_name),
        )
        self._conn.commit()

    def seed_default_users(self, defaults: dict[str, str]):
        for user_name, password in defaults.items():
            row = self._conn.execute(
                "SELECT user_name, password_hash, uid FROM users WHERE user_name=?",
                (user_name,)
            ).fetchone()

            if not row:
                print(f"[SessionStore] Create default user: {user_name}")
                cursor = self._conn.execute(
                    "INSERT INTO users (user_name, password_hash) VALUES (?, ?)",
                    (user_name, _hash_password(password))
                )
                self._conn.execute(
                    "UPDATE users SET uid = ? WHERE user_name = ?",
                    (cursor.lastrowid, user_name)
                )
            elif row["uid"] is None or row["uid"] == 0:
                self._conn.execute(
                    "UPDATE users SET uid = rowid WHERE user_name = ?",
                    (user_name,)
                )
            elif not row["password_hash"] or row["password_hash"] == '':
                print(f"[SessionStore] Reset password for user {user_name}")
                self._conn.execute(
                    "UPDATE users SET password_hash=? WHERE user_name=?",
                    (_hash_password(password), user_name)
                )
            else:
                print(f"[SessionStore] User {user_name} already exists and has a password. Skipping")

        self._conn.commit()

    def get_user_lang(self, user_name: str) -> str:
        from configs.i18n_config import DEFAULT_LANG
        row = self._conn.execute(
            "SELECT lang FROM users WHERE user_name=?", (user_name,)
        ).fetchone()
        return row["lang"] if row and row["lang"] else DEFAULT_LANG

    def set_user_lang(self, user_name: str, lang: str):
        self._conn.execute(
            "UPDATE users SET lang=? WHERE user_name=?", (lang, user_name)
        )
        self._conn.commit()

    def list_users(self) -> List[str]:
        rows = self._conn.execute(
            "SELECT user_name FROM users ORDER BY created_at"
        ).fetchall()
        return [r["user_name"] for r in rows]

    # ── Session ───────────────────────────────────────────────────────────────

    def create_session(self, user_name: str, name: str = "") -> Dict:
        session_id = uuid.uuid4().hex[:10]
        thread_id = f"{user_name}::{session_id}"
        if not name:
            name = f"session {datetime.now().strftime('%m-%d %H:%M')}"
        self._conn.execute(
            "INSERT INTO sessions (session_id, user_name, name, thread_id) VALUES (?,?,?,?)",
            (session_id, user_name, name, thread_id),
        )
        self._conn.commit()
        return {"session_id": session_id, "name": name, "thread_id": thread_id}

    def get_user_sessions(self, user_name: str) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT session_id, name, thread_id, created_at "
            "FROM sessions WHERE user_name=? ORDER BY created_at DESC",
            (user_name,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_session(self, session_id: str) -> Optional[Dict]:
        row = self._conn.execute(
            "SELECT session_id, name, thread_id FROM sessions WHERE session_id=?",
            (session_id,)
        ).fetchone()
        return dict(row) if row else None

    def rename_session(self, session_id: str, name: str):
        self._conn.execute(
            "UPDATE sessions SET name=? WHERE session_id=?", (name, session_id)
        )
        self._conn.commit()

    def delete_session(self, session_id: str):
        self._conn.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
        self._conn.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))
        self._conn.commit()

    # ── Messages ──────────────────────────────────────────────────────────────

    def append_message(self, session_id: str, role: str, content: str,
                       thinking: str = "", metadata: dict = None):
        import json
        meta_str = json.dumps(metadata, ensure_ascii=False) if metadata else ""
        for attempt in range(2):
            try:
                self._conn.execute(
                    "INSERT INTO messages (session_id, role, content, thinking, metadata) VALUES (?,?,?,?,?)",
                    (session_id, role, content, thinking, meta_str),
                )
                self._conn.commit()
                return
            except sqlite3.OperationalError as e:
                if attempt == 0:
                    print(f"[SessionStore] append_message failed, reconnecting: {e}")
                    self._reconnect()
                else:
                    raise

    def get_messages(self, session_id: str) -> List[Dict]:
        import json
        rows = self._conn.execute(
            "SELECT role, content, thinking, metadata FROM messages "
            "WHERE session_id=? ORDER BY id",
            (session_id,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["metadata"] = json.loads(d["metadata"]) if d.get("metadata") else {}
            result.append(d)
        return result

    def message_count(self, session_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) as n FROM messages WHERE session_id=?", (session_id,)
        ).fetchone()
        return row["n"]


_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    global _store
    if _store is None:
        from configs.path_config import OTHER_PATH
        _store = SessionStore(OTHER_PATH["session_db"])
    return _store
