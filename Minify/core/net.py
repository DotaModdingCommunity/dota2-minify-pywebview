"Network request helpers with offline simulation support"

from typing import Any

import requests

from core import config

SIMULATED_FAILURE_MSG = "Simulated network failure (debug_simulate_offline)"


def simulate_failure() -> bool:
    "Whether network requests should be simulated as failing"
    return config.get("debug_simulate_offline", False)


def get(url: str, timeout: Any = 10, **kwargs: Any) -> requests.Response:
    "requests.get() wrapper that simulates a failure when debug_simulate_offline is set"
    if simulate_failure():
        raise requests.exceptions.ConnectionError(SIMULATED_FAILURE_MSG)
    return requests.get(url, timeout=timeout, **kwargs)
