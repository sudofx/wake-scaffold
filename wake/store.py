"""SQLite transactions + hash-linked events. The projection is disposable too."""

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3

from .governance import Rejected, require, transition


ZERO = "0" * 64


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def empty():
    return {"version": 0, "objective": "", "focus": "continuity", "beliefs": {},
            "commitments": {}, "evidence": {}, "journal": [], "invocations": {}, "pending": None}


def reduce_event(state, event):
    p, kind = event["payload"], event["kind"]
    if kind == "initialized":
        require(not state["objective"], "Duplicate initialization")
        state["objective"] = p["objective"]
    elif kind == "observation":
        require(p["id"] not in state["evidence"], "Duplicate evidence ID")
        state["evidence"][p["id"]] = {**p, "version": state["version"], "time": event["time"]}
    elif kind == "focus_changed":
        state["focus"] = p["focus"]
    elif kind == "commitment_cancelled":
        item = state["commitments"].get(p["id"])
        require(item is not None and item["status"] == "open", "Only open commitments can be cancelled")
        item.update(status="cancelled", resolution_reason=p["reason"], resolved_by="human")
    elif kind == "invocation_started":
        require(state["pending"] is None and p["id"] not in state["invocations"], "Conflicting invocation")
        require(p["base_version"] == state["version"], "Start version mismatch")
        state["pending"] = p["id"]
        state["invocations"][p["id"]] = {k: v for k, v in p.items() if k != "request"}
        state["invocations"][p["id"]].update(status="pending", time=event["time"])
    elif kind in ("accepted", "rejected", "failed", "recovered"):
        require(state["pending"] == p["id"], "Invocation is not pending")
        if kind == "accepted":
            state = transition(state, p["proposal"], p["id"])
            require(digest({k: state[k] for k in ("version", "beliefs", "commitments", "journal")}) == p["result_hash"],
                    "Transition result hash mismatch")
        state["invocations"][p["id"]].update(status=kind, finished=event["time"], reason=p.get("reason", ""))
        state["pending"] = None
    else:
        raise Rejected(f"Unknown event kind: {kind}")
    return state


class IntegrityError(RuntimeError):
    pass


class Store:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "wake.sqlite3"
        self.db = sqlite3.connect(self.path, timeout=10)
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY, time TEXT NOT NULL, kind TEXT NOT NULL,
                payload TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS snapshot (id INTEGER PRIMARY KEY CHECK(id=1),
                head TEXT NOT NULL, state TEXT NOT NULL);
        """)

    def close(self):
        self.db.close()

    @contextmanager
    def lock(self):
        with (self.directory / "writer.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Rejected("Another wake owns this state directory; no call was made") from None
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def events(self):
        return [{"seq": row[0], "time": row[1], "kind": row[2], "payload": json.loads(row[3]),
                 "prev_hash": row[4], "hash": row[5]}
                for row in self.db.execute("SELECT * FROM events ORDER BY seq")]

    def replay(self):
        state, head = empty(), ZERO
        try:
            events = self.events()
            for expected, event in enumerate(events, 1):
                body = {k: v for k, v in event.items() if k != "hash"}
                if event["seq"] != expected or event["prev_hash"] != head or digest(body) != event["hash"]:
                    raise IntegrityError(f"Event {expected}: broken hash chain; restore a known-good backup")
                state = reduce_event(state, event)
                head = event["hash"]
        except (ValueError, KeyError, TypeError, sqlite3.DatabaseError) as exc:
            raise IntegrityError(f"Invalid history: {exc}") from exc
        return state, head

    def load(self, repair=False):
        # Always replay governance; never trust the cache as an authority.
        state, head = self.replay()
        row = self.db.execute("SELECT head, state FROM snapshot WHERE id=1").fetchone()
        if row != (head, canonical(state)):
            if not repair:
                raise IntegrityError("Projection differs from valid history; run `python -m wake recover`")
            with self.db:
                self.db.execute("INSERT OR REPLACE INTO snapshot VALUES(1,?,?)", (head, canonical(state)))
        return state

    def append(self, kind, payload, crash=False):
        state, head = self.replay()
        seq = self.db.execute("SELECT COUNT(*) FROM events").fetchone()[0] + 1
        event = {"seq": seq, "time": now(), "kind": kind, "payload": payload, "prev_hash": head}
        event["hash"] = digest(event)
        state = reduce_event(state, event)
        with self.db:
            self.db.execute("INSERT INTO events VALUES(?,?,?,?,?,?)",
                            (seq, event["time"], kind, canonical(payload), head, event["hash"]))
            if crash:
                os._exit(86)  # Deliberate experiment: process dies before transaction commit.
            self.db.execute("INSERT OR REPLACE INTO snapshot VALUES(1,?,?)", (event["hash"], canonical(state)))
        return state

    def backup(self, destination):
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        require(not path.exists(), "Backup destination already exists")
        with sqlite3.connect(path) as target:
            self.db.backup(target)
        return path
