import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from coffemodoro.core.timer import Timer, TimerMode
from coffemodoro.core.database import Database
from coffemodoro.ui.timer_view import TimerView
from coffemodoro.ui.projects_view import ProjectsView
from coffemodoro.ui.settings_view import SettingsView
from coffemodoro.ui.session_dialog import SessionCompleteDialog


class CoffeodoroWindow(Adw.ApplicationWindow):
    def __init__(self, app, timer: Timer, db: Database):
        super().__init__(application=app, title="Coffemodoro")
        self.timer = timer
        self.db = db
        self.set_default_size(380, 580)
        self.set_resizable(True)
        self.set_icon_name("coffemodoro-idle")

        self._build_ui()

    def _build_ui(self):
        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        header = Adw.HeaderBar()
        header.set_show_title(True)
        toolbar_view.add_top_bar(header)

        self.view_stack = Adw.ViewStack()
        toolbar_view.set_content(self.view_stack)

        switcher_bar = Adw.ViewSwitcherBar()
        switcher_bar.set_stack(self.view_stack)
        switcher_bar.set_reveal(True)
        toolbar_view.add_bottom_bar(switcher_bar)

        self.timer_view = TimerView(timer=self.timer, db=self.db)
        self.view_stack.add_titled_with_icon(self.timer_view, "brew", "Brew", "coffemodoro-mug-symbolic")

        self.projects_view = ProjectsView(db=self.db)
        self.view_stack.add_titled_with_icon(self.projects_view, "projects", "Projects", "coffemodoro-folder-symbolic")

        self.settings_view = SettingsView(db=self.db, timer=self.timer, on_applied=self.timer_view._refresh_labels)
        self.view_stack.add_titled_with_icon(self.settings_view, "settings", "Settings", "coffemodoro-settings-symbolic")

    def on_tick(self, elapsed: int, total: int):
        self.timer_view.on_tick(elapsed, total)

    def on_complete(self, mode: TimerMode, sessions_completed: int, started_at: str = None, on_done=None):
        self.timer_view.on_complete(mode, sessions_completed)
        if mode == TimerMode.FOCUS:
            from datetime import datetime, timezone
            dialog = SessionCompleteDialog(
                db=self.db,
                mode=mode,
                duration_s=self.timer._focus_duration,
                started_at=started_at or datetime.now(timezone.utc).isoformat(),
                on_done=on_done or self.refresh_projects,
            )
            dialog.present(self)

    def refresh_projects(self):
        self.projects_view.refresh()
