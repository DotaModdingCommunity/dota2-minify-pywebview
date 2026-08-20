import threading


def _import_output():
    import core.output as output

    return output


def test_capture_thread_routes_only_calling_thread():
    output = _import_output()
    captured = []
    global_calls = []

    def sink(text, *args, msg_type=None, **kwargs):
        captured.append(text)

    def global_send(text, *args, msg_type=None, **kwargs):
        global_calls.append(text)

    output._send = global_send
    try:
        with output.capture_thread(sink):
            output.add_text("inside")
        output.add_text("outside")
    finally:
        output._send = None

    assert captured == ["inside"]
    assert global_calls == ["outside"]


def test_capture_thread_does_not_leak_into_other_threads():
    output = _import_output()
    captured = []
    other_thread_seen = []

    def sink(text, *args, msg_type=None, **kwargs):
        captured.append(text)

    def other_worker():
        output.add_text("other")
        other_thread_seen.append(len(captured))

    output._send = None
    with output.capture_thread(sink):
        t = threading.Thread(target=other_worker)
        t.start()
        t.join()
        output.add_text("main")

    assert captured == ["main"]
    assert other_thread_seen == [0], "other thread must not be captured"


def test_prefix_map_covers_all_styled_types(capsys):
    output = _import_output()
    assert output.PREFIX["error"] == "[ERROR] "
    assert output.PREFIX["warning"] == "[WARNING] "
    assert output.PREFIX["success"] == "[SUCCESS] "
    assert output.PREFIX["section"] == ""
    assert output.PREFIX["detail"] == ""


def test_console_fallback_prints_prefix_for_styled_types(capsys):
    output = _import_output()
    output._send = None
    output.add_text("boom", msg_type="error")
    out = capsys.readouterr().out
    assert out.startswith("[ERROR] ")


def test_console_fallback_prints_plain_line_without_prefix(capsys):
    output = _import_output()
    output._send = None
    output.add_text("plain line")
    out = capsys.readouterr().out
    assert out == "plain line\n"


def test_leading_whitespace_is_stripped_from_lines(capsys):
    output = _import_output()
    output._send = None
    output.add_text("   indented text")
    output.add_section("   Step")
    output.add_detail("   detail")
    out = capsys.readouterr().out
    assert out == "indented text\nStep\n   detail\n"


def test_add_section_and_detail_are_plain_styled_lines(capsys):
    output = _import_output()
    output._send = None
    output.add_section("Step one")
    output.add_detail("secondary info")
    out = capsys.readouterr().out
    assert "Step one" in out
    assert "secondary info" in out
    assert "[SECTION]" not in out and "[DETAIL]" not in out


def test_sink_handled_lines_are_not_echoed_to_console(capsys):
    output = _import_output()
    received = []

    def global_send(text, *args, msg_type=None, **kwargs):
        received.append(text)

    output._send = global_send
    try:
        output.add_text("handled")
        output.add_text("handled two", msg_type="error")
    finally:
        output._send = None

    assert received == ["handled", "handled two"]
    assert capsys.readouterr().out == ""


def test_separator_dispatches_to_global_sink_when_registered():
    output = _import_output()
    received = []

    def global_send(text, *args, msg_type=None, **kwargs):
        received.append((text, msg_type))

    output._send = global_send
    try:
        output.add_separator()
    finally:
        output._send = None

    assert received == [(None, "__sep__")]


def test_separator_prints_dashes_without_sink(capsys):
    output = _import_output()
    output._send = None
    output.add_separator()
    assert capsys.readouterr().out.strip() == "-" * 50
