from ui import actions


class _FakeFile:
    def __init__(self, content):
        self._content = content

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._content


def _make_notes(content, monkeypatch, locale="EN"):
    monkeypatch.setattr("os.path.exists", lambda p: True)
    monkeypatch.setattr(actions.utils, "open_utf8", lambda p: _FakeFile(content))
    monkeypatch.setattr(actions.config, "get", lambda key, default=None: locale if key == "locale" else default)
    return actions._get_mod_notes_html("TestMod")


INLINE = "<!-- LANG:EN -->English notes<!-- LANG:BG -->Български бележки<!-- LANG:DE -->Deutsche Notizen"

NEWLINE = (
    "<!-- LANG:EN -->\n\nEnglish notes\n\n<!-- LANG:BG -->\n\nБългарски бележки\n\n<!-- LANG:DE -->\n\nDeutsche Notizen"
)


def test_get_mod_notes_html_inline_markers_split_by_locale(monkeypatch):
    result = _make_notes(INLINE, monkeypatch, locale="DE")

    assert result == "Deutsche Notizen"
    assert "English" not in result
    assert "Български" not in result


def test_get_mod_notes_html_newline_markers_split_by_locale(monkeypatch):
    result = _make_notes(NEWLINE, monkeypatch, locale="BG")

    assert result == "Български бележки"
    assert "English" not in result
    assert "Deutsche" not in result


def test_get_mod_notes_html_falls_back_to_en_when_locale_missing(monkeypatch):
    result = _make_notes(INLINE, monkeypatch, locale="RU")

    assert result == "English notes"


def test_get_mod_notes_html_no_markers_passthrough(monkeypatch):
    result = _make_notes("  Plain notes without markers  \n", monkeypatch)

    assert result == "Plain notes without markers"


def test_get_mod_notes_html_missing_notes_returns_none(monkeypatch):
    monkeypatch.setattr("os.path.exists", lambda p: False)

    assert actions._get_mod_notes_html("TestMod") is None
