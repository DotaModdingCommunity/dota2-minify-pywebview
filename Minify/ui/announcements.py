"Unix timestamp based announcement system internals"

import os
import time
import webbrowser
from typing import Any

import jsonc
from core import base, config, net


def _extract_identifier(time_str: str | None) -> str:
    if not time_str:
        return ""
    return time_str.replace("-", "").replace("+", "").split("=")[0]


def get_pending_announcements() -> list[dict[str, Any]]:
    """
    Returns a list of announcements that should be shown.
    Only active in frozen mode (compiled executable).
    """
    if not base.FROZEN and not os.environ.get("MINIFY_ANNOUNCEMENTS_URL"):
        return []

    url = os.environ.get("MINIFY_ANNOUNCEMENTS_URL", f"{base.github_io}/announcements.json")
    try:
        response = net.get(url, timeout=5)
        response.raise_for_status()
        announcements = jsonc.loads(response.text)
    except Exception:
        return []

    if not announcements:
        return []

    seen = config.get("announcements_seen", [])
    current_version = base.VERSION
    current_time = int(time.time())

    pending = []
    for ann in announcements:
        time_cond = ann.get("time")
        text = ann.get("text")

        if not time_cond or not text:
            continue

        identifier = _extract_identifier(time_cond)

        if identifier in seen:
            continue

        try:
            # inline time condition parsing
            if "-" in time_cond:
                if current_time > int(time_cond.replace("-", "")):
                    continue
            elif "+" in time_cond:
                if current_time < int(time_cond.replace("+", "")):
                    continue
            elif "=" in time_cond:
                parts = time_cond.split("=")
                if len(parts) == 2:
                    t1, t2 = int(parts[0]), int(parts[1])
                    if not (t1 <= current_time <= t2):
                        continue
        except ValueError:
            continue

        # inline version check
        versions = ann.get("versions")
        if versions and current_version not in versions:
            continue

        pending.append(ann)

    return pending


def mark_as_seen(identifier: str) -> None:
    seen = config.get("announcements_seen", [])
    if identifier not in seen:
        seen.append(identifier)
        config.set("announcements_seen", seen)


def handle_announcement_action(announcement: dict[str, Any], action: str) -> None:
    "action: 'OK' or 'Ignore'"
    time_cond = announcement.get("time")
    identifier = _extract_identifier(time_cond)

    if action == "OK":
        urls = announcement.get("urls", [])
        for url in urls:
            webbrowser.open(url)

    mark_as_seen(identifier)
