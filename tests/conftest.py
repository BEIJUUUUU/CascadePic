import pytest


@pytest.fixture(autouse=True)
def _disable_real_vlc(monkeypatch):
    """Keep the real libVLC runtime out of unit tests.

    Widget tests construct MainWindow and VideoPlayer, which would otherwise
    create and tear down real VLC instances; that is flaky under offscreen
    Qt. Player logic is covered with a fake backend instead.
    """
    monkeypatch.setattr("waterfall_viewer.ui.video_player.vlc", None)
