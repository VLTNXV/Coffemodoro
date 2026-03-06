import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Pango

from coffemodoro.core.timer import Timer, TimerState, TimerMode
from coffemodoro.core.database import Database
from coffemodoro.ui.animation import CoffeeAnimation


class TimerView(Gtk.Box):
    def __init__(self, timer: Timer, db: Database, on_session_complete=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.timer = timer
        self.db = db
        self.on_session_complete = on_session_complete
        self._build_ui()
        self._refresh_labels()
        self._refresh_project_label()

    def _build_ui(self):
        self.set_margin_top(16)
        self.set_margin_bottom(8)
        self.set_margin_start(16)
        self.set_margin_end(16)

        # Coffee animation
        self.animation = CoffeeAnimation()
        self.animation.set_vexpand(True)
        self.append(self.animation)

        # Mode label
        self.mode_label = Gtk.Label()
        self.mode_label.add_css_class("caption")
        self.mode_label.set_margin_top(12)
        self.append(self.mode_label)

        # Time display
        self.time_label = Gtk.Label()
        self.time_label.add_css_class("title-1")
        attrs = Pango.AttrList()
        attrs.insert(Pango.attr_font_features_new("tnum"))
        self.time_label.set_attributes(attrs)
        self.time_label.set_margin_top(4)
        self.append(self.time_label)

        # Session dots
        self.dots_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.dots_box.set_halign(Gtk.Align.CENTER)
        self.dots_box.set_margin_top(8)
        self.append(self.dots_box)

        # Active project selector
        self.project_btn = Gtk.Button()
        self.project_btn.add_css_class("flat")
        self.project_btn.set_halign(Gtk.Align.CENTER)
        self.project_btn.set_margin_top(16)
        project_inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        project_inner.append(Gtk.Image.new_from_icon_name("coffemodoro-folder-symbolic"))
        self.project_name_label = Gtk.Label()
        self.project_name_label.add_css_class("caption")
        project_inner.append(self.project_name_label)
        self.project_btn.set_child(project_inner)
        self.project_btn.connect("clicked", self._on_project_clicked)
        self.append(self.project_btn)

        # Start/Pause button — centred on its own row
        self.start_btn = Gtk.Button()
        self.start_btn.add_css_class("suggested-action")
        self.start_btn.add_css_class("pill")
        self.start_btn.set_halign(Gtk.Align.CENTER)
        self.start_btn.set_size_request(120, -1)
        self.start_btn.set_margin_top(8)
        self.start_btn.connect("clicked", self._on_start_pause)
        self.append(self.start_btn)

        # Secondary controls row
        secondary = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        secondary.set_halign(Gtk.Align.CENTER)
        secondary.set_margin_top(8)
        secondary.set_margin_bottom(8)

        self.full_reset_btn = Gtk.Button(icon_name="coffemodoro-restart-symbolic")
        self.full_reset_btn.add_css_class("circular")
        self.full_reset_btn.set_tooltip_text("Restart cycle")
        self.full_reset_btn.connect("clicked", self._on_full_reset)
        secondary.append(self.full_reset_btn)

        self.reset_btn = Gtk.Button(icon_name="coffemodoro-undo-symbolic")
        self.reset_btn.add_css_class("circular")
        self.reset_btn.set_tooltip_text("Reset timer")
        self.reset_btn.connect("clicked", self._on_reset)
        secondary.append(self.reset_btn)

        self.skip_btn = Gtk.Button(icon_name="coffemodoro-skip-symbolic")
        self.skip_btn.add_css_class("circular")
        self.skip_btn.set_tooltip_text("Skip to next session")
        self.skip_btn.connect("clicked", self._on_skip)
        secondary.append(self.skip_btn)

        self.append(secondary)

    def _refresh_project_label(self):
        active_id_str = self.db.get_setting("active_project_id", "")
        if active_id_str:
            proj = self.db.get_project_by_id(int(active_id_str))
            if proj:
                self.project_name_label.set_text(proj["name"])
                return
            else:
                self.db.set_setting("active_project_id", "")
        self.project_name_label.set_text("No project")

    def _on_project_clicked(self, _btn):
        dialog = Adw.AlertDialog(
            heading="Active Project",
            body="Sessions will be assigned to this project.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("select", "Select")
        dialog.set_response_appearance("select", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("select")
        dialog.set_close_response("cancel")

        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        list_box.add_css_class("boxed-list")

        none_row = Gtk.ListBoxRow()
        none_row.proj_id = None
        none_row.set_child(Gtk.Label(label="No project", xalign=0, margin_start=12, margin_top=8, margin_bottom=8))
        list_box.append(none_row)

        active_id_str = self.db.get_setting("active_project_id", "")
        active_id = int(active_id_str) if active_id_str else None

        for proj in self.db.get_projects():
            row = Gtk.ListBoxRow()
            row.proj_id = proj["id"]
            row.set_child(Gtk.Label(label=proj["name"], xalign=0, margin_start=12, margin_top=8, margin_bottom=8))
            list_box.append(row)
            if proj["id"] == active_id:
                list_box.select_row(row)

        if active_id is None:
            list_box.select_row(none_row)

        dialog.set_extra_child(list_box)

        def on_response(d, response):
            if response == "select":
                selected = list_box.get_selected_row()
                if selected:
                    pid = selected.proj_id
                    self.db.set_setting("active_project_id", str(pid) if pid is not None else "")
                    self._refresh_project_label()

        dialog.connect("response", on_response)
        dialog.present(self)

    def _refresh_labels(self):
        remaining = self.timer.remaining_seconds
        minutes, seconds = divmod(remaining, 60)
        self.time_label.set_text(f"{minutes:02d}:{seconds:02d}")

        mode_names = {
            TimerMode.FOCUS: "Focus",
            TimerMode.SHORT_BREAK: "Short Break",
            TimerMode.LONG_BREAK: "Long Break",
        }
        self.mode_label.set_text(mode_names[self.timer.mode])

        if self.timer.state == TimerState.RUNNING:
            self.start_btn.set_label("Pause")
            self.start_btn.set_tooltip_text("Pause the timer")
        else:
            self.start_btn.set_label("Start")
            self.start_btn.set_tooltip_text("Start the timer")

        self._refresh_dots()

    def _refresh_dots(self):
        while child := self.dots_box.get_first_child():
            self.dots_box.remove(child)

        total = self.timer._sessions_before_long
        completed = self.timer.sessions_completed % total
        for i in range(total):
            dot = Gtk.Label(label="●" if i < completed else "○")
            dot.add_css_class("caption-heading")
            self.dots_box.append(dot)

    def on_tick(self, elapsed: int, total: int):
        self._refresh_labels()
        is_break = self.timer.mode != TimerMode.FOCUS
        self.animation.set_progress(self.timer.progress, is_break=is_break)
        self.animation.set_running(self.timer.state == TimerState.RUNNING)

    def on_complete(self, mode: TimerMode, sessions_completed: int):
        self._refresh_labels()
        self.animation.set_running(False)
        self.animation.pulse_complete()

    def _on_start_pause(self, _btn):
        if self.timer.state == TimerState.RUNNING:
            self.timer.pause()
        elif self.timer.state == TimerState.PAUSED:
            self.timer.resume()
        else:
            self.timer.start()
        self._refresh_labels()
        self.animation.set_running(self.timer.state == TimerState.RUNNING)

    def _on_full_reset(self, _btn):
        self.timer.full_reset()
        self.animation.set_progress(0.0, is_break=False)
        self.animation.set_running(False)
        self._refresh_labels()

    def _on_reset(self, _btn):
        self.timer.reset()
        is_break = self.timer.mode != TimerMode.FOCUS
        self.animation.set_progress(0.0, is_break=is_break)
        self.animation.set_running(False)
        self._refresh_labels()

    def _on_skip(self, _btn):
        self.timer.skip()
        is_break = self.timer.mode != TimerMode.FOCUS
        self.animation.set_progress(0.0, is_break=is_break)
        self.animation.set_running(False)
        self._refresh_labels()
