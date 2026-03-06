import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from coffemodoro.core.database import Database


class ReassignDialog(Adw.Dialog):
    def __init__(self, db: Database, session_id: int, current_project_id: int | None, on_done=None):
        super().__init__()
        self.db = db
        self.session_id = session_id
        self.current_project_id = current_project_id
        self.on_done = on_done
        self._build_ui()

    def _build_ui(self):
        self.set_title("Move Session")
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

        label = Gtk.Label(label="Move this session to:")
        label.add_css_class("body")
        box.append(label)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.add_css_class("boxed-list")
        self.list_box.connect("row-selected", self._on_row_selected)
        box.append(self.list_box)

        # Unassigned row (project_id = None)
        unassigned_row = Gtk.ListBoxRow()
        unassigned_row.proj_id = None
        unassigned_row.set_child(
            Gtk.Label(label="Unassigned", xalign=0, margin_start=12, margin_top=8, margin_bottom=8)
        )
        self.list_box.append(unassigned_row)

        # One row per project, alphabetical (get_projects returns them sorted by name)
        projects = self.db.get_projects()
        for proj in projects:
            row = Gtk.ListBoxRow()
            row.proj_id = proj["id"]
            row.set_child(
                Gtk.Label(label=proj["name"], xalign=0, margin_start=12, margin_top=8, margin_bottom=8)
            )
            self.list_box.append(row)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.add_css_class("flat")
        cancel_btn.connect("clicked", lambda _: self.close())
        buttons.append(cancel_btn)

        self._move_btn = Gtk.Button(label="Move")
        self._move_btn.add_css_class("suggested-action")
        self._move_btn.set_sensitive(False)
        self._move_btn.connect("clicked", self._on_move)
        buttons.append(self._move_btn)

        box.append(buttons)

        # Pre-select the current project row
        self._pre_select_current()

    def _pre_select_current(self):
        i = 0
        while True:
            row = self.list_box.get_row_at_index(i)
            if row is None:
                break
            if row.proj_id == self.current_project_id:
                self.list_box.select_row(row)
                break
            i += 1

    def _on_row_selected(self, _list_box, row):
        if row is None:
            self._move_btn.set_sensitive(False)
            return
        # Enable Move only when the selection differs from current
        self._move_btn.set_sensitive(row.proj_id != self.current_project_id)

    def _on_move(self, _btn):
        selected = self.list_box.get_selected_row()
        if selected is None:
            return
        self.db.update_session_project(self.session_id, selected.proj_id)
        self.close()
        if self.on_done:
            self.on_done()
