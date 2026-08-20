import json
from unittest.mock import MagicMock


def test_send_js_buffers_until_frontend_ready():
    from ui import output_bridge

    window = MagicMock()
    calls_run = []
    calls_eval = []
    window.run_js.side_effect = lambda js: calls_run.append(js)
    window.evaluate_js.side_effect = lambda js: calls_eval.append(js)

    output_bridge._window_ref = window
    output_bridge._frontend_ready = False
    output_bridge._early_queue.clear()
    try:
        output_bridge.send_js("window.early()")
        assert not calls_run
        assert list(output_bridge._early_queue) == ["window.early()"]

        output_bridge.mark_frontend_ready()
        assert calls_eval == ["window.early()"]
        assert not output_bridge._early_queue

        output_bridge.send_js("window.late()")
        assert calls_run == ["window.late()"]
    finally:
        output_bridge._window_ref = None
        output_bridge._frontend_ready = False
        output_bridge._early_queue.clear()


def test_push_line_payload_has_no_prefix():
    from ui import output_bridge

    sent = []
    window = MagicMock()
    window.run_js.side_effect = lambda js: sent.append(js)
    output_bridge._window_ref = window
    output_bridge._frontend_ready = True
    output_bridge._early_queue.clear()
    try:
        output_bridge.push_line("hello", msg_type="warning")
        payload = json.loads(sent[0].split("(", 1)[1].rstrip(")"))
        assert payload["raw"] == "hello"
        assert payload["type"] == "warning"
        assert "prefix" not in payload
    finally:
        output_bridge._window_ref = None
        output_bridge._frontend_ready = False
        output_bridge._early_queue.clear()
