import contextlib
import os
from unittest.mock import patch


def _run_patch_track_js(patcher_result: bool):
    from ui import actions

    sent: list[str] = []
    with (
        patch("patch.patcher", return_value=patcher_result),
        patch("ui.output_bridge.send_js", side_effect=lambda js: sent.append(js)),
        patch("ui.modal_shared.show_progress"),
        patch("ui.modal_shared.hide_progress"),
        patch("ui.actions._set_locked"),
    ):
        actions._run_patch()
    return sent


def test_run_patch_sends_patch_end_on_completion():
    sent = _run_patch_track_js(True)
    assert "window.__patchEnd()" in sent


def test_run_patch_sends_patch_cancelled_on_abort():
    sent = _run_patch_track_js(False)
    assert "window.__patchCancelled()" in sent
    assert "window.__patchEnd()" not in sent


def test_patcher_cancels_and_prompts_mods_with_settings_without_setup_script():
    from core import base, constants
    from patch import patcher

    config_file = os.path.join(base.config_dir, "Mute Sounds config.json")
    setup_script = os.path.join(base.mods_dir, "Mute Sounds", "script_setup.py")

    def fake_exists(path):
        if str(path) == config_file:
            return False
        if str(path) == setup_script:
            return False
        return True

    with (
        patch("ui.actions.interactive_lock", return_value=contextlib.nullcontext()),
        patch("patch.conditions.is_dota_running", return_value=False),
        patch("patch.conditions.check_binaries", return_value=True),
        patch("patch.os.path.exists", side_effect=fake_exists),
        patch.object(constants, "mods_with_order", ["Mute Sounds"]),
        patch("patch.manifest_utils.get_mod", return_value={"settings": [{"key": "mute_ambient"}]}),
        patch("patch.mods_shared.get_state", return_value=True),
        patch("patch.helper.exec_script"),
        patch("ui.modal_shared.show_setup_flow", return_value="cancel") as mock_setup,
        patch("patch.fs.remove_path"),
        patch("patch.fs.create_dirs"),
        patch("patch.output.clean"),
        patch("patch.output.add_text"),
    ):
        result = patcher()

    assert result is False
    mock_setup.assert_called_once()
    pending = mock_setup.call_args.args[0]
    assert [name for name, _ in pending] == ["Mute Sounds"]
