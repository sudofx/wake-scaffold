"""Reconstruct from exported events alone, without SQLite or a saved projection."""

import json
from pathlib import Path

from .store import IntegrityError, ZERO, digest, empty, reduce_event


def verify_history(path, expected_head=None):
    state, head = empty(), ZERO
    for seq, line in enumerate(Path(path).read_text().splitlines(), 1):
        try:
            event = json.loads(line)
            if event["seq"] != seq or event["prev_hash"] != head or digest({k:v for k,v in event.items() if k != "hash"}) != event["hash"]:
                raise IntegrityError(f"Exported event {seq} failed verification")
            state = reduce_event(state, event)
            head = event["hash"]
        except (ValueError, KeyError, TypeError) as exc:
            raise IntegrityError(f"Exported event {seq} is invalid: {exc}") from exc
    if expected_head and head != expected_head.strip():
        raise IntegrityError("History does not match the independently retained head")
    return state, head
