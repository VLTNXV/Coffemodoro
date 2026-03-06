import gi
import os
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from coffemodoro.core.database import Database
from coffemodoro.core.timer import Timer
from coffemodoro.core.notifier import SOUNDS_DIR as _SOUNDS_DIR, _GST_AVAILABLE


class SettingsView(Gtk.Box):
    _SOUNDS = [
        ("Ding",         "ding.ogg"),
        ("Chimes",       "chimes.ogg"),
        ("Chirp",        "chirp.ogg"),
        ("Doorbell",     "doorbell.ogg"),
        ("Glockenspiel", "glockenspiel.ogg"),
    ]

    def __init__(self, db: Database, timer: Timer, on_applied=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.db = db
        self.timer = timer
        self._on_applied = on_applied
        self._build_ui()

    def _build_ui(self):
        self._toast_overlay = Adw.ToastOverlay()
        self._toast_overlay.set_vexpand(True)
        self.append(self._toast_overlay)

        scroll = Gtk.ScrolledWindow()
        self._toast_overlay.set_child(scroll)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        scroll.set_child(box)

        # Durations group
        durations_group = Adw.PreferencesGroup(title="Timer Durations")
        box.append(durations_group)

        self.focus_row = self._make_spin_row("Focus", "focus_duration", 1, 120)
        self.short_row = self._make_spin_row("Short Break", "short_break", 1, 60)
        self.long_row = self._make_spin_row("Long Break", "long_break", 1, 60)
        self.sessions_row = self._make_spin_row("Sessions before long break", "sessions_before_long_break", 1, 10)

        for row in [self.focus_row, self.short_row, self.long_row, self.sessions_row]:
            durations_group.add(row)

        # Behaviour group
        behaviour_group = Adw.PreferencesGroup(title="Behaviour")
        box.append(behaviour_group)

        self.auto_advance_row = Adw.SwitchRow(title="Auto-advance sessions")
        self.auto_advance_row.set_subtitle("Start the next session automatically — you still need to acknowledge the session-complete dialog")
        self.auto_advance_row.set_active(self.db.get_setting("auto_advance", "0") == "1")
        self.auto_advance_row.connect(
            "notify::active",
            lambda r, _: self.db.set_setting("auto_advance", "1" if r.get_active() else "0"),
        )
        behaviour_group.add(self.auto_advance_row)

        self.focus_window_row = Adw.ExpanderRow(title="Focus window on complete")
        self.focus_window_row.set_subtitle("Raise the window when a session ends")
        self.focus_window_row.set_show_enable_switch(True)
        _fw_enabled = self.db.get_setting("focus_window_enabled", "0") == "1"
        self.focus_window_row.set_enable_expansion(_fw_enabled)
        self.focus_window_row.connect(
            "notify::enable-expansion",
            lambda r, _: self.db.set_setting(
                "focus_window_enabled", "1" if r.get_enable_expansion() else "0"
            ),
        )

        self.focus_child_row = Adw.SwitchRow(title="Focus sessions")
        self.focus_child_row.set_active(self.db.get_setting("focus_window_on_focus", "1") == "1")
        self.focus_child_row.connect(
            "notify::active",
            lambda r, _: self.db.set_setting(
                "focus_window_on_focus", "1" if r.get_active() else "0"
            ),
        )
        self.focus_window_row.add_row(self.focus_child_row)

        self.break_child_row = Adw.SwitchRow(title="Break sessions")
        self.break_child_row.set_active(self.db.get_setting("focus_window_on_break", "1") == "1")
        self.break_child_row.connect(
            "notify::active",
            lambda r, _: self.db.set_setting(
                "focus_window_on_break", "1" if r.get_active() else "0"
            ),
        )
        self.focus_window_row.add_row(self.break_child_row)

        behaviour_group.add(self.focus_window_row)

        # Notifications group
        notif_group = Adw.PreferencesGroup(title="Notifications")
        box.append(notif_group)

        self.notif_row = Adw.SwitchRow(title="Desktop Notifications")
        self.notif_row.set_active(self.db.get_setting("notifications_enabled", "1") == "1")
        self.notif_row.connect("notify::active", lambda r, _: self.db.set_setting("notifications_enabled", "1" if r.get_active() else "0"))
        notif_group.add(self.notif_row)

        self.sound_row = Adw.SwitchRow(title="Sound")
        self.sound_row.set_active(self.db.get_setting("sound_enabled", "1") == "1")
        self.sound_row.connect("notify::active", lambda r, _: self.db.set_setting("sound_enabled", "1" if r.get_active() else "0"))
        notif_group.add(self.sound_row)

        sound_labels = Gtk.StringList.new([label for label, _ in self._SOUNDS])
        self.sound_combo = Adw.ComboRow(title="Alert sound")
        self.sound_combo.set_model(sound_labels)

        current_file = self.db.get_setting("sound_file", "ding.ogg")
        current_idx = next((i for i, (_, f) in enumerate(self._SOUNDS) if f == current_file), 0)
        self.sound_combo.set_selected(current_idx)

        def _on_sound_selected(combo, _):
            idx = combo.get_selected()
            self.db.set_setting("sound_file", self._SOUNDS[idx][1])

        self.sound_combo.connect("notify::selected", _on_sound_selected)
        notif_group.add(self.sound_combo)

        volume_row = Adw.ActionRow(title="Volume")
        volume_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
        volume_scale.set_value(float(self.db.get_setting("sound_volume", "80")))
        volume_scale.set_size_request(150, -1)
        volume_scale.set_draw_value(False)
        volume_scale.connect("value-changed", lambda s: self.db.set_setting("sound_volume", str(int(s.get_value()))))
        volume_row.add_suffix(volume_scale)

        preview_btn = Gtk.Button(icon_name="coffemodoro-play-symbolic")
        preview_btn.add_css_class("circular")
        preview_btn.add_css_class("flat")
        preview_btn.set_valign(Gtk.Align.CENTER)
        preview_btn.set_tooltip_text("Preview sound")
        preview_btn.connect("clicked", lambda _: self._preview_sound(volume_scale.get_value()))
        volume_row.add_suffix(preview_btn)

        notif_group.add(volume_row)

        # Data group
        data_group = Adw.PreferencesGroup(title="Data")
        box.append(data_group)

        export_row = Adw.ActionRow(title="Export backup", subtitle="Save all data to a JSON file")
        export_row.set_activatable(True)
        export_row.add_suffix(Gtk.Image.new_from_icon_name("coffemodoro-save-symbolic"))
        export_row.connect("activated", self._on_export_backup)
        data_group.add(export_row)

        restore_row = Adw.ActionRow(title="Restore backup", subtitle="Replace all data from a JSON backup")
        restore_row.set_activatable(True)
        restore_row.add_suffix(Gtk.Image.new_from_icon_name("coffemodoro-revert-symbolic"))
        restore_row.connect("activated", self._on_restore_backup)
        data_group.add(restore_row)

    def _on_export_backup(self, _row):
        from datetime import date
        dialog = Gtk.FileDialog()
        dialog.set_title("Export backup")
        dialog.set_initial_name(f"coffemodoro-backup-{date.today().strftime('%Y-%m-%d')}.json")
        dialog.save(self.get_root(), None, self._on_export_backup_done)

    def _on_export_backup_done(self, dialog, result):
        from gi.repository import GLib
        try:
            file = dialog.save_finish(result)
        except GLib.GError:
            return
        path = file.get_path()
        if path is None:
            self._toast_overlay.add_toast(Adw.Toast(title="Export failed: file path unavailable"))
            return
        try:
            from coffemodoro.core.exporter import export_backup
            content = export_backup(self.db)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as exc:
            self._toast_overlay.add_toast(Adw.Toast(title=f"Export failed: {exc}"))
            return
        filename = os.path.basename(path)
        self._toast_overlay.add_toast(Adw.Toast(title=f"Backup saved to {filename}"))

    def _on_restore_backup(self, _row):
        dialog = Gtk.FileDialog()
        dialog.set_title("Restore backup")
        dialog.open(self.get_root(), None, self._on_restore_file_chosen)

    def _on_restore_file_chosen(self, dialog, result):
        from gi.repository import GLib
        try:
            file = dialog.open_finish(result)
        except GLib.GError:
            return
        path = file.get_path()
        if path is None:
            self._toast_overlay.add_toast(Adw.Toast(title="Restore failed: file path unavailable"))
            return
        filename = os.path.basename(path)
        confirm = Adw.AlertDialog(
            heading="Restore backup?",
            body=f"Restore from '{filename}'? This will replace all current projects, sessions, and settings. Restart the app after restoring to see all changes.",
        )
        confirm.add_response("cancel", "Cancel")
        confirm.add_response("restore", "Restore")
        confirm.set_response_appearance("restore", Adw.ResponseAppearance.DESTRUCTIVE)
        confirm.set_default_response("cancel")
        confirm.set_close_response("cancel")

        def on_confirm(d, response):
            if response != "restore":
                return
            try:
                from coffemodoro.core.exporter import restore_backup
                with open(path, "r", encoding="utf-8") as f:
                    restore_backup(self.db, f.read())
                toast = Adw.Toast(title="Backup restored. Restart to apply all changes.")
                toast.set_timeout(8)
                self._toast_overlay.add_toast(toast)
            except Exception as exc:
                self._toast_overlay.add_toast(Adw.Toast(title=f"Restore failed: {exc}"))

        confirm.connect("response", on_confirm)
        confirm.present(self)

    def _preview_sound(self, volume: float):
        if not _GST_AVAILABLE:
            return
        idx = self.sound_combo.get_selected()
        sound_file = self._SOUNDS[idx][1]
        path = os.path.join(_SOUNDS_DIR, sound_file)
        if not os.path.exists(path):
            self._toast_overlay.add_toast(Adw.Toast(title="Sound file not found"))
            return
        try:
            from gi.repository import Gst
            self._preview_player = Gst.parse_launch(f'playbin uri="file://{path}" volume={volume / 100.0}')
            self._preview_player.set_state(Gst.State.PLAYING)
        except Exception:
            pass

    def _make_spin_row(self, title: str, key: str, min_val: int, max_val: int) -> Adw.SpinRow:
        row = Adw.SpinRow.new_with_range(min_val, max_val, 1)
        row.set_title(title)
        row.set_value(float(self.db.get_setting(key, "25")))

        def on_changed(r):
            self.db.set_setting(key, str(int(r.get_value())))
            self._apply_timer_durations()

        row.connect("notify::value", lambda r, _: on_changed(r))
        return row

    def _apply_timer_durations(self):
        self.timer.update_durations(
            focus=int(self.db.get_setting("focus_duration", "25")) * 60,
            short=int(self.db.get_setting("short_break", "5")) * 60,
            long=int(self.db.get_setting("long_break", "15")) * 60,
            sessions_before_long=int(self.db.get_setting("sessions_before_long_break", "4")),
        )
        if self._on_applied:
            self._on_applied()
