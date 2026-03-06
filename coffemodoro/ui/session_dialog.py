import gi
from datetime import datetime, timezone
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from coffemodoro.core.database import Database
from coffemodoro.core.timer import TimerMode


def _format_session_date(iso_str: str) -> str:
    dt = datetime.fromisoformat(iso_str).astimezone()
    today = datetime.now(timezone.utc).astimezone().date()
    if dt.date() == today:
        return f"Today at {dt.strftime('%H:%M')}"
    return dt.strftime("%-d %b at %H:%M")


class SessionCompleteDialog(Adw.Dialog):
    def __init__(self, db: Database, mode: TimerMode, duration_s: int, started_at: str, on_done=None):
        super().__init__()
        self.db = db
        self.mode = mode
        self.duration_s = duration_s
        self.on_done = on_done
        self._started_at = started_at  # passed in, not captured here
        self.desc_entry = None
        self._build_ui()

    def _build_ui(self):
        self.set_title("Session Complete")
        self.set_content_width(340)

        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)
        self.set_child(toolbar_view)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        toolbar_view.set_content(box)

        date_label = Gtk.Label(label=_format_session_date(self._started_at))
        date_label.add_css_class("caption")
        date_label.add_css_class("dim-label")
        date_label.set_halign(Gtk.Align.CENTER)
        box.append(date_label)

        label = Gtk.Label(label="Assign this session to a project?")
        label.add_css_class("body")
        box.append(label)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.add_css_class("boxed-list")
        box.append(self.list_box)

        active_id_str = self.db.get_setting("active_project_id", "")
        active_id = int(active_id_str) if active_id_str else None

        projects = self.db.get_projects()
        for proj in projects:
            row = Gtk.ListBoxRow()
            row.proj_id = proj["id"]
            row.set_child(Gtk.Label(label=proj["name"], xalign=0, margin_start=12, margin_top=8, margin_bottom=8))
            self.list_box.append(row)
            if proj["id"] == active_id:
                self.list_box.select_row(row)

        # New project row
        new_row = Gtk.ListBoxRow()
        new_row.proj_id = "new"
        new_row.set_child(Gtk.Label(label="+ New Project", xalign=0, margin_start=12, margin_top=8, margin_bottom=8))
        self.list_box.append(new_row)

        desc_list = Gtk.ListBox()
        desc_list.set_selection_mode(Gtk.SelectionMode.NONE)
        desc_list.add_css_class("boxed-list")
        self.desc_entry = Adw.EntryRow()
        self.desc_entry.set_title("What did you work on?")
        desc_list.append(self.desc_entry)
        box.append(desc_list)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)

        skip_btn = Gtk.Button(label="Skip")
        skip_btn.add_css_class("flat")
        skip_btn.connect("clicked", lambda _: self._save_session(project_id=None))
        buttons.append(skip_btn)

        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save)
        buttons.append(save_btn)

        box.append(buttons)

    def _on_save(self, _btn):
        selected = self.list_box.get_selected_row()
        if selected is None:
            self._save_session(project_id=None)
            return

        if selected.proj_id == "new":
            self._prompt_new_project()
        else:
            self._save_session(project_id=selected.proj_id)

    def _prompt_new_project(self):
        dialog = Adw.AlertDialog(heading="New Project", body="Enter a project name:")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("create", "Create")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        entry = Gtk.Entry()
        entry.set_placeholder_text("Project name")
        dialog.set_extra_child(entry)

        def on_response(d, response):
            if response == "create":
                name = entry.get_text().strip()
                if name:
                    try:
                        pid = self.db.create_project(name)
                        self._save_session(project_id=pid)
                    except Exception:
                        self._save_session(project_id=None)
            else:
                self._save_session(project_id=None)

        dialog.connect("response", on_response)
        dialog.present(self)

    def _save_session(self, project_id):
        ended_at = datetime.now(timezone.utc).isoformat()
        mode_map = {
            TimerMode.FOCUS: "focus",
            TimerMode.SHORT_BREAK: "short_break",
            TimerMode.LONG_BREAK: "long_break",
        }
        description = self.desc_entry.get_text().strip() or None
        self.db.log_session(
            project_id=project_id,
            session_type=mode_map[self.mode],
            started_at=self._started_at,
            ended_at=ended_at,
            duration_s=self.duration_s,
            completed=True,
            description=description,
        )
        self.close()
        if self.on_done:
            self.on_done()
