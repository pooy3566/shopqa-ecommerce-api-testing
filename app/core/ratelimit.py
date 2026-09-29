"""Minimal in-process login throttle (CWE-307).

Tracks failed login attempts per (client IP, username) and locks the pair for a
cooldown once a threshold is crossed. Intentionally dependency-free.

LIMITATION, stated plainly because it matters: this state lives in one process's
memory. It does not survive a restart and is not shared across replicas or workers.
Behind more than one instance the real control belongs at the edge (a WAF) or in a
shared store (Redis). This raises the cost of online password guessing against a
single instance; it is not a distributed rate limiter.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, List, Tuple

MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60  # 15 minutes

_failures: Dict[Tuple[str, str], List[float]] = defaultdict(list)


def _key(ip: str, username: str) -> Tuple[str, str]:
    return (ip or "unknown", (username or "").lower())


def _prune(times: List[float], now: float) -> List[float]:
    cutoff = now - WINDOW_SECONDS
    return [t for t in times if t >= cutoff]


def is_locked(ip: str, username: str) -> bool:
    now = time.monotonic()
    key = _key(ip, username)
    times = _prune(_failures[key], now)
    _failures[key] = times
    return len(times) >= MAX_FAILURES


def record_failure(ip: str, username: str) -> None:
    now = time.monotonic()
    key = _key(ip, username)
    _failures[key] = _prune(_failures[key], now)
    _failures[key].append(now)


def clear(ip: str, username: str) -> None:
    """Drop the failure history for a pair, e.g. after a successful login."""
    _failures.pop(_key(ip, username), None)


def retry_after_seconds() -> int:
    return WINDOW_SECONDS


def reset() -> None:
    """Test hook: wipe all counters."""
    _failures.clear()
