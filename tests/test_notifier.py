import os
import pytest
from unittest.mock import patch, MagicMock
from coffemodoro.core.database import Database


@pytest.fixture
def db():
    d = Database(":memory:")
    d.init_schema()
    return d


def test_notifier_uses_sound_file_setting(db):
    db.set_setting("sound_file", "chimes.ogg")
    from coffemodoro.core.notifier import Notifier, SOUNDS_DIR
    notifier = Notifier(db=db)

    played = []

    def fake_parse_launch(pipeline_str):
        played.append(pipeline_str)
        return MagicMock()

    chimes_path = os.path.abspath(os.path.join(SOUNDS_DIR, "chimes.ogg"))

    with patch("coffemodoro.core.notifier._GST_AVAILABLE", True), \
         patch("coffemodoro.core.notifier.Gst") as mock_gst, \
         patch("coffemodoro.core.notifier.os.path.exists", return_value=True):
        mock_gst.parse_launch.side_effect = fake_parse_launch
        notifier._play_sound()

    assert len(played) == 1
    assert "chimes.ogg" in played[0]


def test_notifier_falls_back_to_ding_when_file_missing(db):
    db.set_setting("sound_file", "missing.ogg")
    from coffemodoro.core.notifier import Notifier, SOUNDS_DIR
    notifier = Notifier(db=db)

    played = []

    def fake_parse_launch(pipeline_str):
        played.append(pipeline_str)
        return MagicMock()

    ding_path = os.path.abspath(os.path.join(SOUNDS_DIR, "ding.ogg"))

    def fake_exists(path):
        return path == ding_path  # missing.ogg → False, ding.ogg → True

    with patch("coffemodoro.core.notifier._GST_AVAILABLE", True), \
         patch("coffemodoro.core.notifier.Gst") as mock_gst, \
         patch("coffemodoro.core.notifier.os.path.exists", side_effect=fake_exists):
        mock_gst.parse_launch.side_effect = fake_parse_launch
        notifier._play_sound()

    assert len(played) == 1
    assert "ding.ogg" in played[0]


def test_notifier_uses_ding_by_default(db):
    from coffemodoro.core.notifier import Notifier
    notifier = Notifier(db=db)

    played = []

    def fake_parse_launch(pipeline_str):
        played.append(pipeline_str)
        return MagicMock()

    with patch("coffemodoro.core.notifier._GST_AVAILABLE", True), \
         patch("coffemodoro.core.notifier.Gst") as mock_gst, \
         patch("coffemodoro.core.notifier.os.path.exists", return_value=True):
        mock_gst.parse_launch.side_effect = fake_parse_launch
        notifier._play_sound()

    assert len(played) == 1
    assert "ding.ogg" in played[0]
