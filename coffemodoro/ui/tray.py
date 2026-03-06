import os

ICONS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "hicolor", "scalable", "apps")
)
IDLE_ICON = os.path.join(ICONS_DIR, "coffemodoro-idle.svg")
ACTIVE_ICON = os.path.join(ICONS_DIR, "coffemodoro-active.svg")


class TrayIcon:
    def __init__(self, on_toggle_window):
        self._on_toggle_window = on_toggle_window
        self._indicator = None
        self._available = False
        self._setup()

    def _setup(self):
        try:
            import gi
            gi.require_version("AyatanaAppIndicator3", "0.1")
            from gi.repository import AyatanaAppIndicator3 as AppIndicator3
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk as Gtk3

            self._indicator = AppIndicator3.Indicator.new(
                "coffemodoro",
                IDLE_ICON,
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            )
            self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

            menu = Gtk3.Menu()
            toggle_item = Gtk3.MenuItem(label="Show / Hide")
            toggle_item.connect("activate", lambda _: self._on_toggle_window())
            menu.append(toggle_item)

            quit_item = Gtk3.MenuItem(label="Quit")
            quit_item.connect("activate", lambda _: self._quit())
            menu.append(quit_item)

            menu.show_all()
            self._indicator.set_menu(menu)
            self._available = True
        except Exception as e:
            print(f"[Coffemodoro] Tray icon unavailable: {e}")

    def set_active(self, active: bool):
        if not self._available or self._indicator is None:
            return
        icon = ACTIVE_ICON if active else IDLE_ICON
        self._indicator.set_icon_full(icon, "Coffemodoro")

    def _quit(self):
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk
        app = Gtk.Application.get_default()
        if app:
            app.quit()
