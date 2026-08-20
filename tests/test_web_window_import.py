def test_web_window_imports_cleanly():
    """Smoke test: the pywebview window module must import on any platform the
    release CI builds (windows-latest, ubuntu-latest). Guards against accidental
    Windows-only module-level imports breaking the Linux build."""
    import ui.web_window as web_window

    assert callable(web_window.create_window)
    assert "patch" in web_window._API_WHITELIST


def test_web_window_create_window_calls_webview_start():
    """create_window() must reach webview.start() with the window and the
    _on_started hook, proving the drop-listener registration path is wired."""
    from unittest.mock import MagicMock, patch

    import webview
    import ui.web_window as web_window

    with (
        patch.object(webview, "create_window", return_value=MagicMock()),
        patch.object(webview, "start") as mstart,
    ):
        web_window.create_window()

    assert mstart.called
    assert callable(mstart.call_args.kwargs["func"])
