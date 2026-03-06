import sqlite3
import pytest
from coffemodoro.core.database import Database

@pytest.fixture
def db():
    d = Database(":memory:")
    d.init_schema()
    return d

def test_init_schema_creates_tables(db):
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    names = {row[0] for row in tables}
    assert {"projects", "sessions", "settings"} <= names

def test_create_project(db):
    project_id = db.create_project("My Thesis")
    assert isinstance(project_id, int)

def test_get_projects_empty(db):
    assert db.get_projects() == []

def test_get_projects_returns_created(db):
    db.create_project("Alpha")
    db.create_project("Beta")
    projects = db.get_projects()
    assert len(projects) == 2
    assert projects[0]["name"] == "Alpha"

def test_create_project_duplicate_raises(db):
    db.create_project("Alpha")
    with pytest.raises(sqlite3.IntegrityError):
        db.create_project("Alpha")

def test_log_session(db):
    session_id = db.log_session(
        project_id=None,
        session_type="focus",
        started_at="2026-02-19T10:00:00",
        ended_at="2026-02-19T10:25:00",
        duration_s=1500,
        completed=True,
    )
    assert isinstance(session_id, int)

def test_get_sessions_for_project(db):
    pid = db.create_project("Work")
    db.log_session(pid, "focus", "2026-02-19T10:00:00", "2026-02-19T10:25:00", 1500, True)
    sessions = db.get_sessions(project_id=pid)
    assert len(sessions) == 1
    assert sessions[0]["type"] == "focus"

def test_get_project_total_seconds(db):
    pid = db.create_project("Work")
    db.log_session(pid, "focus", "2026-02-19T10:00:00", "2026-02-19T10:25:00", 1500, True)
    db.log_session(pid, "focus", "2026-02-19T11:00:00", "2026-02-19T11:25:00", 1500, True)
    assert db.get_project_total_seconds(pid) == 3000

def test_get_set_setting(db):
    db.set_setting("focus_duration", "25")
    assert db.get_setting("focus_duration") == "25"

def test_get_setting_default(db):
    assert db.get_setting("nonexistent", default="42") == "42"

def test_get_unassigned_sessions(db):
    db.log_session(None, "focus", "2026-02-19T10:00:00", "2026-02-19T10:25:00", 1500, True)
    sessions = db.get_sessions(project_id=None)
    assert len(sessions) == 1

def test_get_project_total_seconds_excludes_incomplete(db):
    pid = db.create_project("Work")
    db.log_session(pid, "focus", "2026-02-19T10:00:00", "2026-02-19T10:25:00", 1500, True)
    db.log_session(pid, "focus", "2026-02-19T11:00:00", "2026-02-19T11:25:00", 900, False)  # incomplete
    assert db.get_project_total_seconds(pid) == 1500  # only the completed one

def test_get_sessions_isolates_by_project(db):
    pid_a = db.create_project("A")
    pid_b = db.create_project("B")
    db.log_session(pid_a, "focus", "2026-02-19T10:00:00", "2026-02-19T10:25:00", 1500, True)
    db.log_session(pid_b, "focus", "2026-02-19T11:00:00", "2026-02-19T11:25:00", 1500, True)
    assert len(db.get_sessions(project_id=pid_a)) == 1
    assert len(db.get_sessions(project_id=pid_b)) == 1

def test_assigned_session_not_in_unassigned(db):
    pid = db.create_project("Work")
    db.log_session(pid, "focus", "2026-02-19T10:00:00", "2026-02-19T10:25:00", 1500, True)
    assert db.get_sessions(project_id=None) == []

def test_update_session_project_to_project(db):
    pid = db.create_project("Work")
    sid = db.log_session(None, "focus", "2026-02-19T10:00:00", "2026-02-19T10:25:00", 1500, True)
    db.update_session_project(sid, pid)
    sessions = db.get_sessions(project_id=pid)
    assert len(sessions) == 1
    assert sessions[0]["id"] == sid

def test_update_session_project_to_unassigned(db):
    pid = db.create_project("Work")
    sid = db.log_session(pid, "focus", "2026-02-19T10:00:00", "2026-02-19T10:25:00", 1500, True)
    db.update_session_project(sid, None)
    assert db.get_sessions(project_id=pid) == []
    unassigned = db.get_sessions(project_id=None)
    assert any(s["id"] == sid for s in unassigned)

def test_delete_session_removes_it(db):
    sid = db.log_session(None, "focus", "2026-02-19T10:00:00", "2026-02-19T10:25:00", 1500, True)
    db.delete_session(sid)
    assert db.get_sessions(project_id=None) == []

def test_delete_session_only_removes_target(db):
    sid_a = db.log_session(None, "focus", "2026-02-19T10:00:00", "2026-02-19T10:25:00", 1500, True)
    sid_b = db.log_session(None, "focus", "2026-02-19T11:00:00", "2026-02-19T11:25:00", 900, True)
    db.delete_session(sid_a)
    remaining = db.get_sessions(project_id=None)
    assert len(remaining) == 1
    assert remaining[0]["id"] == sid_b

def test_delete_project_removes_project(db):
    pid = db.create_project("Work")
    db.delete_project(pid, delete_sessions=False)
    assert db.get_projects() == []

def test_delete_project_moves_sessions_to_unassigned(db):
    pid = db.create_project("Work")
    sid = db.log_session(pid, "focus", "2026-02-19T10:00:00", "2026-02-19T10:25:00", 1500, True)
    db.delete_project(pid, delete_sessions=False)
    unassigned = db.get_sessions(project_id=None)
    assert len(unassigned) == 1
    assert unassigned[0]["id"] == sid

def test_delete_project_deletes_sessions(db):
    pid = db.create_project("Work")
    sid = db.log_session(pid, "focus", "2026-02-19T10:00:00", "2026-02-19T10:25:00", 1500, True)
    db.delete_project(pid, delete_sessions=True)
    assert db.get_projects() == []
    all_sessions = db.execute("SELECT id FROM sessions WHERE id = ?", (sid,)).fetchall()
    assert all_sessions == []

def test_delete_project_nonexistent_is_noop(db):
    db.delete_project(9999, delete_sessions=False)  # should not raise

def test_delete_project_deletes_only_own_sessions(db):
    pid_a = db.create_project("A")
    pid_b = db.create_project("B")
    sid_b = db.log_session(pid_b, "focus", "2026-02-19T10:00:00", "2026-02-19T10:25:00", 1500, True)
    db.log_session(pid_a, "focus", "2026-02-19T11:00:00", "2026-02-19T11:25:00", 900, True)
    db.delete_project(pid_a, delete_sessions=True)
    assert len(db.get_sessions(project_id=pid_b)) == 1
    assert db.get_sessions(project_id=pid_b)[0]["id"] == sid_b


def test_log_session_with_description(db):
    sid = db.log_session(
        project_id=None,
        session_type="focus",
        started_at="2026-02-27T10:00:00",
        ended_at="2026-02-27T10:25:00",
        duration_s=1500,
        completed=True,
        description="Wrote the intro chapter",
    )
    sessions = db.get_sessions(project_id=None)
    assert sessions[0]["description"] == "Wrote the intro chapter"


def test_log_session_no_description(db):
    db.log_session(None, "focus", "2026-02-27T10:00:00", "2026-02-27T10:25:00", 1500, True)
    sessions = db.get_sessions(project_id=None)
    assert sessions[0]["description"] is None


def test_update_session_description(db):
    sid = db.log_session(None, "focus", "2026-02-27T10:00:00", "2026-02-27T10:25:00", 1500, True)
    db.update_session_description(sid, "Fixed the login bug")
    sessions = db.get_sessions(project_id=None)
    assert sessions[0]["description"] == "Fixed the login bug"


def test_update_session_description_to_none(db):
    sid = db.log_session(
        None, "focus", "2026-02-27T10:00:00", "2026-02-27T10:25:00", 1500, True,
        description="Old note",
    )
    db.update_session_description(sid, None)
    sessions = db.get_sessions(project_id=None)
    assert sessions[0]["description"] is None


def test_get_all_sessions_returns_all(db):
    pid = db.create_project("Work")
    db.log_session(None, "focus", "2026-02-19T10:00:00", "2026-02-19T10:25:00", 1500, True)
    db.log_session(pid, "focus", "2026-02-19T11:00:00", "2026-02-19T11:25:00", 1500, True)
    all_sessions = db.get_all_sessions()
    assert len(all_sessions) == 2
    assert all_sessions[0]["started_at"] < all_sessions[1]["started_at"]

def test_get_all_settings_returns_dict(db):
    from coffemodoro.core.database import DEFAULT_SETTINGS
    settings = db.get_all_settings()
    assert isinstance(settings, dict)
    assert set(DEFAULT_SETTINGS.keys()) <= set(settings.keys())

def test_restore_from_backup_orphaned_session_becomes_unassigned(db):
    db.restore_from_backup(
        projects=[],
        sessions=[{"id": 1, "project_id": 99, "type": "focus",
                   "started_at": "2026-01-01T10:00:00",
                   "ended_at": "2026-01-01T10:25:00",
                   "duration_s": 1500, "completed": 1, "description": None}],
        settings={},
    )
    sessions = db.get_all_sessions()
    assert len(sessions) == 1
    assert sessions[0]["project_id"] is None

def test_restore_from_backup_replaces_data(db):
    db.create_project("Old")
    db.restore_from_backup(
        projects=[{"id": 1, "name": "New", "created_at": "2026-01-01T00:00:00"}],
        sessions=[],
        settings={"focus_duration": "30"},
    )
    projects = db.get_projects()
    assert len(projects) == 1
    assert projects[0]["name"] == "New"
    assert db.get_setting("focus_duration") == "30"

def test_restore_from_backup_preserves_unmentioned_settings(db):
    # Settings not in backup keep their existing values
    db.restore_from_backup(
        projects=[],
        sessions=[{"id": 1, "project_id": None, "type": "focus",
                   "started_at": "2026-01-01T10:00:00",
                   "ended_at": "2026-01-01T10:25:00",
                   "duration_s": 1500, "completed": 1, "description": None}],
        settings={"focus_duration": "45"},
    )
    assert db.get_setting("short_break") == "5"  # default still present
    assert len(db.get_all_sessions()) == 1


def test_migration_adds_description_column(tmp_path):
    db_path = str(tmp_path / "old.db")
    # Simulate a pre-description database (no description column)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER,
            type        TEXT NOT NULL,
            started_at  TEXT NOT NULL,
            ended_at    TEXT NOT NULL,
            duration_s  INTEGER NOT NULL,
            completed   INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()

    d = Database(db_path)
    d.init_schema()

    cols = d.execute("PRAGMA table_info(sessions)").fetchall()
    col_names = [c[1] for c in cols]
    assert "description" in col_names
    d.close()
