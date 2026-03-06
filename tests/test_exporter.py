import json
import pytest
from coffemodoro.core.database import Database
from coffemodoro.core.exporter import export_project_markdown, export_backup, restore_backup


@pytest.fixture
def db():
    d = Database(":memory:")
    d.init_schema()
    return d


@pytest.fixture
def db_with_project(db):
    pid = db.create_project("My Project")
    db.log_session(pid, "focus", "2026-02-28T10:00:00+00:00", "2026-02-28T10:25:00+00:00",
                   1500, True, description="Wrote the intro")
    db.log_session(pid, "focus", "2026-02-27T14:00:00+00:00", "2026-02-27T14:25:00+00:00",
                   1500, True, description=None)
    db.log_session(pid, "short_break", "2026-02-28T10:25:00+00:00", "2026-02-28T10:30:00+00:00",
                   300, True, description=None)
    return db, pid


def test_markdown_contains_project_name(db_with_project):
    db, pid = db_with_project
    md = export_project_markdown(db, pid)
    assert "# My Project" in md


def test_markdown_contains_session_count(db_with_project):
    db, pid = db_with_project
    md = export_project_markdown(db, pid)
    assert "3 sessions" in md


def test_markdown_contains_total_duration(db_with_project):
    db, pid = db_with_project
    md = export_project_markdown(db, pid)
    assert "55m total" in md


def test_markdown_contains_description(db_with_project):
    db, pid = db_with_project
    md = export_project_markdown(db, pid)
    assert "Wrote the intro" in md


def test_markdown_placeholder_for_no_description(db_with_project):
    db, pid = db_with_project
    md = export_project_markdown(db, pid)
    assert "*(no note)*" in md


def test_markdown_invalid_project_raises(db):
    with pytest.raises(ValueError):
        export_project_markdown(db, 9999)


def test_backup_is_valid_json(db_with_project):
    db, _ = db_with_project
    result = export_backup(db)
    data = json.loads(result)
    assert data["version"] == 1
    assert "exported_at" in data
    assert isinstance(data["projects"], list)
    assert isinstance(data["sessions"], list)
    assert isinstance(data["settings"], dict)


def test_backup_contains_all_projects(db_with_project):
    db, _ = db_with_project
    data = json.loads(export_backup(db))
    assert any(p["name"] == "My Project" for p in data["projects"])


def test_backup_contains_all_sessions(db_with_project):
    db, _ = db_with_project
    data = json.loads(export_backup(db))
    assert len(data["sessions"]) == 3


def test_restore_roundtrip(db_with_project):
    db, _ = db_with_project
    backup_json = export_backup(db)

    db2 = Database(":memory:")
    db2.init_schema()
    restore_backup(db2, backup_json)

    assert len(db2.get_projects()) == 1
    assert db2.get_projects()[0]["name"] == "My Project"
    assert len(db2.get_all_sessions()) == 3


def test_restore_bad_version_raises(db):
    bad = json.dumps({"version": 99, "projects": [], "sessions": [], "settings": {}})
    with pytest.raises(ValueError, match="Unsupported backup version"):
        restore_backup(db, bad)


def test_markdown_includes_all_session_types(db_with_project):
    db, pid = db_with_project
    md = export_project_markdown(db, pid)
    # All completed sessions (focus + breaks) are included
    assert "Short Break" in md
    assert "Focus" in md


def test_restore_missing_key_raises_value_error(db):
    bad = json.dumps({"version": 1, "projects": [], "sessions": []})  # missing "settings"
    with pytest.raises(ValueError, match="Invalid backup format"):
        restore_backup(db, bad)


def test_markdown_singular_session(db):
    pid = db.create_project("Solo")
    db.log_session(pid, "focus", "2026-02-28T10:00:00+00:00", "2026-02-28T10:25:00+00:00",
                   1500, True, description=None)
    md = export_project_markdown(db, pid)
    assert "1 session" in md
    assert "1 sessions" not in md
