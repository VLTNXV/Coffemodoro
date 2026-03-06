import gi
import os
gi.require_version("Notify", "0.7")
from gi.repository import Notify

try:
    gi.require_version("Gst", "1.0")
    from gi.repository import Gst
    Gst.init(None)
    _GST_AVAILABLE = True
except Exception:
    _GST_AVAILABLE = False

SOUNDS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "sounds")


class Notifier:
    def __init__(self, db):
        self.db = db
        Notify.init("Coffemodoro")
        self._player = None

    def notify_complete(self, mode: str):
        if self.db.get_setting("notifications_enabled", "1") == "1":
            messages = {
                "focus": ("Focus session complete!", "Time for a break. ☕"),
                "short_break": ("Break over!", "Back to work."),
                "long_break": ("Long break over!", "Ready for another round?"),
            }
            title, body = messages.get(mode, ("Timer complete!", ""))
            n = Notify.Notification.new(title, body, "dialog-information")
            try:
                n.show()
            except Exception:
                pass

        if self.db.get_setting("sound_enabled", "1") == "1":
            self._play_sound()

    def _play_sound(self):
        if not _GST_AVAILABLE:
            return
        sound_file = self.db.get_setting("sound_file", "ding.ogg")
        sound_path = os.path.abspath(os.path.join(SOUNDS_DIR, sound_file))
        if not os.path.exists(sound_path):
            sound_path = os.path.abspath(os.path.join(SOUNDS_DIR, "ding.ogg"))
        if not os.path.exists(sound_path):
            return
        volume = float(self.db.get_setting("sound_volume", "80")) / 100.0
        pipeline_str = f'playbin uri="file://{sound_path}" volume={volume}'
        try:
            player = Gst.parse_launch(pipeline_str)
            player.set_state(Gst.State.PLAYING)
            self._player = player
        except Exception:
            pass
