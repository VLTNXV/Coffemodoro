import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gdk
from datetime import datetime, timezone
from pathlib import Path

from coffemodoro.core.database import Database
from coffemodoro.core.timer import Timer, TimerMode
from coffemodoro.core.notifier import Notifier
from coffemodoro.ui.window import CoffeodoroWindow
from coffemodoro.ui.tray import TrayIcon

DB_PATH = Path.home() / ".local" / "share" / "coffemodoro" / "coffemodoro.db"

_MODE_NAMES = {
    TimerMode.FOCUS: "focus",
    TimerMode.SHORT_BREAK: "short_break",
    TimerMode.LONG_BREAK: "long_break",
}


class CoffeodoroApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.coffemodoro.app")
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        icons_dir = Path(__file__).parent / "assets" / "icons"
        Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_search_path(str(icons_dir))

        css = Gtk.CssProvider()
        css.load_from_string(
            "@define-color accent_bg_color #C19A6B;"
            "@define-color accent_color #C19A6B;"
            "@define-color accent_fg_color white;"
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.db = Database(str(DB_PATH))
        self.db.init_schema()

        self.notifier = Notifier(db=self.db)

        self.timer = Timer(
            focus_duration=int(self.db.get_setting("focus_duration", "25")) * 60,
            short_break=int(self.db.get_setting("short_break", "5")) * 60,
            long_break=int(self.db.get_setting("long_break", "15")) * 60,
            sessions_before_long=int(self.db.get_setting("sessions_before_long_break", "4")),
            on_tick=self._on_tick,
            on_complete=self._on_complete,
        )

        self._session_started_at = None

        self.window = CoffeodoroWindow(app=self, timer=self.timer, db=self.db)
        self.window.present()

        self.tray = TrayIcon(on_toggle_window=self._toggle_window)

        GLib.timeout_add(1000, self._tick_timer)

    def _tick_timer(self):
        self.timer.tick()
        return True

    def _toggle_window(self):
        if self.window.is_visible():
            self.window.hide()
        else:
            self.window.present()

    def _on_tick(self, elapsed, total):
        if elapsed == 1:
            self._session_started_at = datetime.now(timezone.utc).isoformat()
        if hasattr(self, "tray"):
            self.tray.set_active(True)
        if hasattr(self, "window"):
            self.window.on_tick(elapsed, total)

    def _on_complete(self, mode, sessions_completed):
        self.notifier.notify_complete(_MODE_NAMES[mode])
        if hasattr(self, "tray"):
            self.tray.set_active(False)
        if hasattr(self, "window"):
            started_at = self._session_started_at or datetime.now(timezone.utc).isoformat()
            auto_advance = self.db.get_setting("auto_advance", "0") == "1"

            if mode == TimerMode.FOCUS:
                # Wrap on_done so that after the dialog is dismissed we can auto-start
                def on_done():
                    self.window.refresh_projects()
                    if auto_advance:
                        GLib.timeout_add(500, self._start_next_session)

                self.window.on_complete(mode, sessions_completed,
                                        started_at=started_at, on_done=on_done)
            else:
                self.window.on_complete(mode, sessions_completed, started_at=started_at)
                if auto_advance:
                    GLib.timeout_add(800, self._start_next_session)

        if hasattr(self, "window") and self.db.get_setting("focus_window_enabled", "0") == "1":
            is_focus = mode == TimerMode.FOCUS
            key = "focus_window_on_focus" if is_focus else "focus_window_on_break"
            if self.db.get_setting(key, "1") == "1":
                self.window.present()

        self._session_started_at = None

    def _start_next_session(self):
        from coffemodoro.core.timer import TimerState
        if self.timer.state == TimerState.IDLE:
            self.timer.start()
            if hasattr(self, "window"):
                self.window.on_tick(0, self.timer.total_seconds)
        return False  # don't repeat


def main():
    import sys
    app = CoffeodoroApp()
    sys.exit(app.run(sys.argv))
