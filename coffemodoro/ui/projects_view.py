import os
import re

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from coffemodoro.core.database import Database
from coffemodoro.ui.reassign_dialog import ReassignDialog


def _format_duration(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _format_session_date(iso_str: str) -> str:
    from datetime import datetime, timezone
    dt = datetime.fromisoformat(iso_str).astimezone()
    today = datetime.now(timezone.utc).astimezone().date()
    if dt.date() == today:
        return f"Today {dt.strftime('%H:%M')}"
    return dt.strftime("%-d %b %H:%M")


class ProjectsView(Gtk.Box):
    def __init__(self, db: Database):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.db = db
        self._build_ui()

    def _build_ui(self):
        # Header with add button
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        add_btn = Gtk.Button(icon_name="coffemodoro-add-symbolic")
        add_btn.add_css_class("flat")
        add_btn.connect("clicked", self._on_add_project)
        header.pack_end(add_btn)
        self.append(header)

        # Scrollable project list
        self._toast_overlay = Adw.ToastOverlay()
        self._toast_overlay.set_vexpand(True)
        self.append(self._toast_overlay)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._toast_overlay.set_child(scroll)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.add_css_class("boxed-list")
        self.list_box.set_margin_top(12)
        self.list_box.set_margin_bottom(12)
        self.list_box.set_margin_start(16)
        self.list_box.set_margin_end(16)
        scroll.set_child(self.list_box)

        self.refresh()

    def refresh(self):
        while child := self.list_box.get_first_child():
            self.list_box.remove(child)

        projects = self.db.get_projects()

        # Unassigned row
        unassigned_sessions = self.db.get_sessions(project_id=None)
        unassigned_seconds = sum(s["duration_s"] for s in unassigned_sessions if s["completed"])
        self._add_project_row(None, "Unassigned", unassigned_seconds, unassigned_sessions)

        for proj in projects:
            total_s = self.db.get_project_total_seconds(proj["id"])
            sessions = self.db.get_sessions(project_id=proj["id"])
            self._add_project_row(proj["id"], proj["name"], total_s, sessions)

    def _add_project_row(self, project_id, name: str, total_seconds: int, sessions: list):
        expander = Adw.ExpanderRow()
        expander.set_title(name)
        expander.set_subtitle(_format_duration(total_seconds))

        if project_id is not None:
            export_btn = Gtk.Button(icon_name="coffemodoro-save-symbolic")
            export_btn.add_css_class("flat")
            export_btn.set_valign(Gtk.Align.CENTER)
            export_btn.set_tooltip_text("Export summary")
            export_btn.connect("clicked", self._make_export_handler(project_id, name))
            expander.add_suffix(export_btn)

            del_btn = Gtk.Button(icon_name="coffemodoro-trash-symbolic")
            del_btn.add_css_class("flat")
            del_btn.set_valign(Gtk.Align.CENTER)
            del_btn.set_tooltip_text("Delete project")
            del_btn.connect("clicked", self._make_delete_project_handler(project_id, name))
            expander.add_suffix(del_btn)

        for session in sessions[:10]:  # show last 10
            row = Adw.ActionRow()
            stype = session["type"].replace("_", " ").title()
            row.set_title(stype)
            date_str = f"{_format_session_date(session['started_at'])} · {_format_duration(session['duration_s'])}"
            desc = (session.get("description") or "").strip()
            row.set_subtitle(f"{date_str}\n{desc}" if desc else date_str)

            edit_btn = Gtk.Button(icon_name="coffemodoro-edit-symbolic")
            edit_btn.add_css_class("flat")
            edit_btn.set_valign(Gtk.Align.CENTER)
            edit_btn.set_tooltip_text("Edit note")
            edit_btn.connect(
                "clicked",
                self._make_edit_description_handler(session["id"], session.get("description") or ""),
            )
            row.add_suffix(edit_btn)

            btn = Gtk.Button(icon_name="coffemodoro-select-symbolic")
            btn.add_css_class("flat")
            btn.set_valign(Gtk.Align.CENTER)
            btn.set_tooltip_text("Reassign session")
            btn.connect(
                "clicked",
                self._make_reassign_handler(session["id"], session["project_id"]),
            )
            row.add_suffix(btn)

            del_btn = Gtk.Button(icon_name="coffemodoro-trash-symbolic")
            del_btn.add_css_class("flat")
            del_btn.set_valign(Gtk.Align.CENTER)
            del_btn.set_tooltip_text("Delete session")
            del_btn.connect("clicked", self._make_delete_handler(session["id"]))
            row.add_suffix(del_btn)

            expander.add_row(row)

        if not sessions:
            empty = Adw.ActionRow()
            empty.set_title("No sessions yet")
            expander.add_row(empty)

        self.list_box.append(expander)

    def _make_reassign_handler(self, session_id: int, project_id: int | None):
        def handler(_btn):
            dialog = ReassignDialog(
                db=self.db,
                session_id=session_id,
                current_project_id=project_id,
                on_done=self.refresh,
            )
            dialog.present(self)
        return handler

    def _make_edit_description_handler(self, session_id: int, current: str):
        def handler(_btn):
            dialog = Adw.AlertDialog(
                heading="Edit Note",
                body="Add or update the note for this session.",
            )
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("save", "Save")
            dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
            dialog.set_default_response("save")
            dialog.set_close_response("cancel")

            entry = Gtk.Entry()
            entry.set_text(current)
            entry.set_placeholder_text("What did you work on?")
            dialog.set_extra_child(entry)

            def on_response(d, response):
                if response == "save":
                    text = entry.get_text().strip() or None
                    self.db.update_session_description(session_id, text)
                    self.refresh()

            dialog.connect("response", on_response)
            dialog.present(self)
        return handler

    def _make_delete_handler(self, session_id: int):
        def handler(_btn):
            dialog = Adw.AlertDialog(
                heading="Delete Session?",
                body="This action cannot be undone.",
            )
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("delete", "Delete")
            dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.set_default_response("cancel")
            dialog.set_close_response("cancel")

            def on_response(d, response):
                if response == "delete":
                    self.db.delete_session(session_id)
                    self.refresh()

            dialog.connect("response", on_response)
            dialog.present(self)
        return handler

    def _make_delete_project_handler(self, project_id: int, name: str):
        def handler(_btn):
            dialog = Adw.AlertDialog(
                heading=f"Delete {name}?",
                body="What should happen to its sessions?",
            )
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("move", "Move to Unassigned")
            dialog.add_response("delete_all", "Delete All")
            dialog.set_response_appearance("delete_all", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.set_response_appearance("move", Adw.ResponseAppearance.SUGGESTED)
            dialog.set_default_response("cancel")
            dialog.set_close_response("cancel")

            def on_response(d, response):
                if response == "move":
                    self.db.delete_project(project_id, delete_sessions=False)
                    self.refresh()
                elif response == "delete_all":
                    self.db.delete_project(project_id, delete_sessions=True)
                    self.refresh()

            dialog.connect("response", on_response)
            dialog.present(self)
        return handler

    def _make_export_handler(self, project_id: int, name: str):
        def handler(_btn):
            from datetime import date
            dialog = Gtk.FileDialog()
            dialog.set_title("Export project summary")
            slug = name.lower().replace(" ", "-")
            slug = re.sub(r"[^\w\-]", "-", slug)
            slug = re.sub(r"-{2,}", "-", slug).strip("-") or "project"
            dialog.set_initial_name(f"{slug}-{date.today().strftime('%Y-%m-%d')}.md")
            dialog.save(self.get_root(), None, self._on_export_done, project_id)
        return handler

    def _on_export_done(self, dialog, result, project_id):
        from gi.repository import GLib
        try:
            file = dialog.save_finish(result)
        except GLib.GError:
            return  # user cancelled or dismissed
        path = file.get_path()
        if path is None:
            self._toast_overlay.add_toast(Adw.Toast(title="Export failed: file path unavailable"))
            return
        try:
            from coffemodoro.core.exporter import export_project_markdown
            content = export_project_markdown(self.db, project_id)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as exc:
            self._toast_overlay.add_toast(Adw.Toast(title=f"Export failed: {exc}"))
            return
        filename = os.path.basename(path)
        self._toast_overlay.add_toast(Adw.Toast(title=f"Exported to {filename}"))

    def _on_add_project(self, _btn):
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
                        self.db.create_project(name)
                        self.refresh()
                    except Exception:
                        pass  # duplicate name — ignore silently

        dialog.connect("response", on_response)
        dialog.present(self)
