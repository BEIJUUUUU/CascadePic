from waterfall_viewer import app


def test_parse_args_separates_smoke_and_media() -> None:
    assert app._parse_args(["folder", "--smoke", "out.png", "extra"]) == (
        "out.png",
        ["folder", "extra"],
    )


def test_parse_args_accepts_plain_media_path() -> None:
    assert app._parse_args([r"D:\pics"]) == (None, [r"D:\pics"])


def test_frozen_runtime_points_vlc_at_bundled_library(tmp_path, monkeypatch) -> None:
    base = tmp_path / "bin"
    base.mkdir()
    (base / "libvlc.dll").touch()
    (base / "plugins").mkdir()
    monkeypatch.setattr(app.sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        app.sys, "executable", str(base / "WaterfallMediaViewer.exe"), raising=False
    )
    monkeypatch.delenv("PYTHON_VLC_LIB_PATH", raising=False)
    monkeypatch.delenv("PYTHON_VLC_MODULE_PATH", raising=False)

    app._configure_frozen_runtime()

    assert app.os.environ["PYTHON_VLC_LIB_PATH"] == str(base / "libvlc.dll")
    assert app.os.environ["PYTHON_VLC_MODULE_PATH"] == str(base / "plugins")


def test_frozen_runtime_leaves_env_untouched_when_not_frozen(monkeypatch) -> None:
    monkeypatch.setattr(app.sys, "frozen", False, raising=False)
    monkeypatch.delenv("PYTHON_VLC_LIB_PATH", raising=False)

    app._configure_frozen_runtime()

    assert "PYTHON_VLC_LIB_PATH" not in app.os.environ
