import json
from datetime import datetime, date, timezone


def _fmt_dur(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _fmt_dt(iso_str: str) -> str:
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().strftime("%-d %b %H:%M")


def export_project_markdown(db, project_id: int) -> str:
    project = db.get_project_by_id(project_id)
    if project is None:
        raise ValueError(f"Project {project_id} not found")

    sessions = db.get_sessions(project_id=project_id)
    completed = [s for s in sessions if s["completed"]]

    total_s = sum(s["duration_s"] for s in completed)
    n = len(completed)
    generated = date.today().strftime("%-d %b %Y")

    lines = [
        f"# {project['name']}",
        f"Generated: {generated} · {n} session{'s' if n != 1 else ''} · {_fmt_dur(total_s)} total",
        "",
        "---",
        "",
    ]

    for s in completed:
        session_type = s["type"].replace("_", " ").title()
        lines.append(f"### {_fmt_dt(s['started_at'])} · {_fmt_dur(s['duration_s'])} · {session_type}")
        desc = (s.get("description") or "").strip()
        lines.append(desc if desc else "*(no note)*")
        lines.append("")

    return "\n".join(lines)


def export_backup(db) -> str:
    data = {
        "version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "projects": db.get_projects(),
        "sessions": db.get_all_sessions(),
        "settings": db.get_all_settings(),
    }
    return json.dumps(data, indent=2)


def restore_backup(db, json_str: str) -> None:
    data = json.loads(json_str)
    if data.get("version") != 1:
        raise ValueError(f"Unsupported backup version: {data.get('version')}")
    try:
        db.restore_from_backup(
            projects=data["projects"],
            sessions=data["sessions"],
            settings=data["settings"],
        )
    except KeyError as e:
        raise ValueError(f"Invalid backup format: missing key {e}") from e
