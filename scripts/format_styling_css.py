"""Reformat Minify mod `styling.css` files into readable, multi-line CSS.

Minify mods historically ship minified, single-line `styling.css` content
(e.g. `#Foo { visibility: collapse; }#Bar { color: #fff; }`). This utility
reformats that content into an indented, one-declaration-per-line layout while
preserving the Minify syntax comments verbatim on their own lines:

    /* g:panorama/styles/hud/hud_reborn */
    #Foo {
        visibility: collapse;
    }

    #Bar {
        color: #fff;
    }

The formatting is behavior-neutral: VCSS is whitespace-insensitive, and the
`/* g: */`, `/* c: */`, and `/* @key: */` markers must remain single-line
comments (the parser regex in `patch/styling.py` is non-DOTALL), which this
tool guarantees by keeping every comment token intact.

Usage:
    python scripts/format_styling_css.py [path...]       # format in place
    python scripts/format_styling_css.py --check [path...]  # verify only

`path` may be a `styling.css` file or a directory (searched recursively).
Defaults to the `Minify/mods` directory.
"""

import argparse
import io
import os
import sys

INDENT = 4


def _split_selectors(sel: str) -> list[str]:
    """Split a selector list on top-level commas (parens & strings aware)."""
    parts: list[str] = []
    depth = 0
    quote: str | None = None
    cur: list[str] = []
    i = 0
    n = len(sel)
    while i < n:
        ch = sel[i]
        if quote is not None:
            cur.append(ch)
            if ch == "\\" and i + 1 < n:
                cur.append(sel[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "'\"":
            quote = ch
            cur.append(ch)
        elif ch == "(":
            depth += 1
            cur.append(ch)
        elif ch == ")":
            depth = max(depth - 1, 0)
            cur.append(ch)
        elif ch == "," and depth == 0:
            part = "".join(cur).strip()
            if part:
                parts.append(part)
            cur = []
        else:
            cur.append(ch)
        i += 1
    part = "".join(cur).strip()
    if part:
        parts.append(part)
    return parts


def format_css(text: str) -> str:
    """Return a readable, indented rendering of the given CSS text."""
    lines: list[str] = []
    depth = 0
    buf: list[str] = []
    quote: str | None = None
    blank_pending = False

    def flush() -> str:
        nonlocal buf
        s = "".join(buf).strip()
        buf = []
        return s

    def emit(s: str, d: int) -> None:
        nonlocal blank_pending
        if not s:
            return
        if blank_pending:
            lines.append("")
            blank_pending = False
        lines.append(" " * (INDENT * d) + s)

    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if quote is not None:
            buf.append(ch)
            if ch == "\\" and i + 1 < n:
                buf.append(text[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue

        if ch in "'\"":
            quote = ch
            buf.append(ch)
            i += 1
            continue

        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            s = flush()
            if s:
                emit(s, depth)
            end = text.find("*/", i + 2)
            if end == -1:
                end = n
            else:
                end += 2
            for part in text[i:end].splitlines() or [""]:
                emit(part, depth)
            i = end
            continue

        if ch == "{":
            parts = _split_selectors(flush())
            if len(parts) <= 1:
                emit(parts[0] + " {", depth) if parts else emit("{", depth)
            else:
                for k, part in enumerate(parts):
                    emit(part + " {" if k == len(parts) - 1 else part + ",", depth)
            depth += 1
            i += 1
            continue

        if ch == "}":
            s = flush()
            if s:
                emit(s, depth)
            depth = max(depth - 1, 0)
            emit("}", depth)
            if depth == 0:
                blank_pending = True
            i += 1
            continue

        if ch == ";":
            s = flush()
            if s:
                emit(s + ";", depth)
            i += 1
            continue

        buf.append(ch)
        i += 1

    s = flush()
    if s:
        emit(s, depth)

    return "\n".join(lines)


def format_text(text: str) -> str:
    """Normalize then beautify CSS text (single trailing newline, no BOM)."""
    formatted = format_css(text).strip("\n") + "\n"
    if formatted.startswith("\ufeff"):
        formatted = formatted[1:]
    return formatted


def collect_files(paths: list[str]) -> list[str]:
    files: list[str] = []
    for path in paths:
        if not os.path.exists(path):
            print(f"warning: path does not exist: {path}", file=sys.stderr)
            continue
        if os.path.isdir(path):
            for root, _dirs, names in os.walk(path):
                if "styling.css" in names:
                    files.append(os.path.join(root, "styling.css"))
        elif path.endswith("styling.css"):
            files.append(path)
        else:
            print(f"warning: not a styling.css file: {path}", file=sys.stderr)
    return sorted(files)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", default=["Minify/mods"], help="file or directory to format")
    parser.add_argument("--check", action="store_true", help="verify formatting without modifying files")
    args = parser.parse_args(argv)

    files = collect_files(args.paths or ["Minify/mods"])
    changed: list[str] = []
    for path in files:
        with io.open(path, encoding="utf-8", newline="") as fh:
            original = fh.read()
        formatted = format_text(original)
        if formatted != original:
            changed.append(path)
            if not args.check:
                with io.open(path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(formatted)

    if changed:
        verb = "Would reformat" if args.check else "Reformatted"
        print(f"{verb} {len(changed)} file(s):")
        for path in changed:
            print(f"  {path}")
        return 1 if args.check else 0
    print("All styling.css files are properly formatted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
