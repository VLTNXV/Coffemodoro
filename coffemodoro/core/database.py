import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    type        TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    ended_at    TEXT NOT NULL,
    duration_s  INTEGER NOT NULL,
    completed   INTEGER NOT NULL DEFAULT 1,
    description TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

DEFAULT_SETTINGS = {
    "focus_duration": "25",
    "short_break": "5",
    "long_break": "15",
    "sessions_before_long_break": "4",
    "notifications_enabled": "1",
    "sound_enabled": "1",
    "sound_volume": "80",
}


class Database:
    def __init__(self, path: str):
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")

    def init_schema(self):
        self._conn.executescript(SCHEMA)
        for key, value in DEFAULT_SETTINGS.items():
            self._conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value)
            )
        self._conn.commit()
        try:
            self._conn.execute("ALTER TABLE sessions ADD COLUMN description TEXT")
            self._conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self._conn.execute(sql, params)

    def create_project(self, name: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO projects (name, created_at) VALUES (?, datetime('now'))", (name,)
        )
        self._conn.commit()
        return cur.lastrowid

    def rename_project(self, project_id: int, name: str) -> None:
        self._conn.execute(
            "UPDATE projects SET name = ? WHERE id = ?", (name, project_id)
        )
        self._conn.commit()

    def get_projects(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM projects ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_project_by_id(self, project_id: int) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return dict(row) if row else None

    def log_session(
        self,
        project_id: int | None,
        session_type: str,
        started_at: str,
        ended_at: str,
        duration_s: int,
        completed: bool,
        description: str | None = None,
    ) -> int:
        cur = self._conn.execute(
            """INSERT INTO sessions
               (project_id, type, started_at, ended_at, duration_s, completed, description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (project_id, session_type, started_at, ended_at, duration_s, int(completed), description),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_sessions(self, project_id: int | None = None) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM sessions WHERE project_id IS ? ORDER BY started_at DESC",
            (project_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_sessions(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM sessions ORDER BY started_at"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_settings(self) -> dict:
        rows = self._conn.execute("SELECT key, value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}

    def restore_from_backup(self, projects: list[dict], sessions: list[dict], settings: dict) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM sessions")
            self._conn.execute("DELETE FROM projects")
            for p in projects:
                self._conn.execute(
                    "INSERT INTO projects (id, name, created_at) VALUES (?, ?, ?)",
                    (p["id"], p["name"], p["created_at"]),
                )
            project_ids = {p["id"] for p in projects}
            for s in sessions:
                pid = s["project_id"] if s["project_id"] in project_ids else None
                self._conn.execute(
                    """INSERT INTO sessions
                       (id, project_id, type, started_at, ended_at, duration_s, completed, description)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (s["id"], pid, s["type"], s["started_at"], s["ended_at"],
                     s["duration_s"], s["completed"], s.get("description")),
                )
            for key, value in settings.items():
                self._conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    (key, value),
                )

    def get_project_total_seconds(self, project_id: int) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(SUM(duration_s), 0) FROM sessions WHERE project_id = ? AND completed = 1",
            (project_id,),
        ).fetchone()
        return row[0]

    def update_session_project(self, session_id: int, project_id: int | None):
        self._conn.execute(
            "UPDATE sessions SET project_id = ? WHERE id = ?", (project_id, session_id)
        )
        self._conn.commit()

    def update_session_description(self, session_id: int, description: str | None) -> None:
        self._conn.execute(
            "UPDATE sessions SET description = ? WHERE id = ?", (description, session_id)
        )
        self._conn.commit()

    def delete_session(self, session_id: int) -> None:
        self._conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self._conn.commit()

    def delete_project(self, project_id: int, delete_sessions: bool) -> None:
        with self._conn:
            if delete_sessions:
                self._conn.execute("DELETE FROM sessions WHERE project_id = ?", (project_id,))
            self._conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    def get_setting(self, key: str, default: str = "") -> str:
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str):
        self._conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )
        self._conn.commit()

    def close(self):
        self._conn.close()
