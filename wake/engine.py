"""One fresh process, one bounded proposal, one atomic decision."""

from datetime import datetime
import json
import os
from pathlib import Path
import tomllib
import uuid
from zoneinfo import ZoneInfo

from .governance import Rejected, require, text, transition
from .providers import SYSTEM
from .store import Store, canonical, digest


DEFAULTS = {"timezone": "America/Los_Angeles", "objective": "Test durable continuity under mechanical governance.",
            "provider": "gemini", "model": "gemini-2.5-flash", "daily_call_limit": 20,
            "max_context_chars": 48000, "max_output_tokens": 4096, "timeout_seconds": 60,
            "free_tier_confirmed": False}


def config(path="wake.toml"):
    result = {**DEFAULTS, **(tomllib.loads(Path(path).read_text()) if Path(path).exists() else {})}
    require(type(result["daily_call_limit"]) is int and 1 <= result["daily_call_limit"] <= 20,
            "daily_call_limit must be between 1 and 20")
    require(result["timezone"] == "America/Los_Angeles", "Daily quota timezone must be America/Los_Angeles")
    for key, low, high in (("max_context_chars", 4000, 64000), ("max_output_tokens", 256, 8192), ("timeout_seconds", 1, 120)):
        require(type(result[key]) is int and low <= result[key] <= high, f"Invalid {key}")
    text(result["objective"], "Objective", 2000)
    if result.get("mission"):
        text(result["mission"], "Research mission", 3000)
        text(result.get("pet_name", "Wake"), "Pet name", 80)
    return result


class Engine:
    def __init__(self, directory="data", settings=None):
        self.config = settings or config()
        self.store = Store(directory)

    def initialize(self):
        state, _ = self.store.replay()
        if not state["objective"]:
            state = self.store.append("initialized", {"objective": self.config["objective"], "governance": 1})
        if self.config.get("mission") and not state.get("charter"):
            state = self.store.append("charter_adopted", {"mission": self.config["mission"],
                                     "pet_name": self.config.get("pet_name", "Wake"), "actor": "operator"})
        return self.store.load(repair=True)

    def recover(self, explicit=False):
        state = self.store.load(repair=True)
        if state["pending"]:
            item = state["invocations"][state["pending"]]
            require(explicit or item["provider"] != "manual", "A manual proposal is pending; complete it or explicitly recover")
            state = self.store.append("recovered", {"id": state["pending"],
                                       "reason": "Previous invocation ended without a committed decision; resumed last valid state."})
        return state

    def observe(self, content, source, evidence_id=None):
        text(content, "Observation", 8000)
        text(source, "Source", 1000)
        state = self.store.load()
        require(state["pending"] is None, "Finish or recover the pending invocation before adding evidence")
        return self.store.append("observation", {"id": evidence_id or "e-" + uuid.uuid4().hex[:16],
                                                 "source": source, "content": content, "actor": "human"})

    def context(self, state, receipt):
        # Recent receipts and the newest supporting evidence for every belief stay visible.
        # All citation IDs remain in beliefs; full evidence is always in the durable export.
        wanted = set(list(state["evidence"])[-6:])
        for belief in state["beliefs"].values():
            wanted.update(belief["evidence"][-3:])
        context = {"version": state["version"], "objective": state["objective"], "focus": state["focus"],
                "receipt": receipt, "beliefs": list(state["beliefs"].values()),
                "commitments": [c for c in state["commitments"].values() if c["status"] == "open"],
                "evidence": [v for k, v in state["evidence"].items() if k in wanted],
                "recent_journal": state["journal"][-3:],
                "evidence_scope": "Recent observations plus newest three citations per belief; full evidence remains in history."}
        if state.get("charter"):
            context["mission"] = state["charter"]
            context["pet_name"] = state["pet_name"]
            projects = list(state["projects"].values())
            context["projects"] = [p for p in projects if p["status"] == "active"] + [p for p in projects if p["status"] != "active"][-8:]
            context["notebooks"] = [{k:n[k] for k in ("id", "project", "title", "summary", "revision", "evidence")}
                                    for n in list(state["notebooks"].values())[-8:]]
            working = [n for n in state["notebooks"].values() if state["projects"][n["project"]]["status"] == "active"]
            context["working_notebook"] = ({**working[-1], "findings": working[-1]["findings"][:3000],
                                           "context_excerpt": True} if working else None)
            context["research"] = list(state["research"].values())[-8:]
            # Research excerpts are bounded. Full snapshots remain available in the lab.
            sources = [v for v in state["evidence"].values() if v.get("actor") == "collector"][-6:]
            context["evidence"] = [{**e, "content": e["content"][:3000], "context_excerpt": len(e["content"]) > 3000}
                                   for e in context["evidence"] if e.get("actor") != "collector"][-3:]
            context["evidence"] += [{**e, "content": e["content"][:3000], "context_excerpt": len(e["content"]) > 3000} for e in sources]
            context["beliefs"] = [{**b, "evidence": b["evidence"][-6:]} for b in context["beliefs"]]
            outcomes = [e for e in self.store.events() if e["kind"] in ("rejected", "failed")][-2:]
            context["recent_problems"] = [e["payload"].get("reason", "") for e in outcomes]
        return context

    def start(self, provider, model, charged=False):
        state = self.store.load()
        require(state["pending"] is None, "An invocation is already pending")
        day = datetime.now(ZoneInfo(self.config["timezone"])).date().isoformat()
        used = sum(i["charged"] and i["quota_day"] == day for i in state["invocations"].values())
        require(not charged or used < self.config["daily_call_limit"], "Daily call ceiling reached; no request sent")
        invocation = "w-" + uuid.uuid4().hex[:16]
        receipt = "r-" + invocation[2:]
        _, head = self.store.replay()
        state = self.store.append("observation", {"id": receipt, "source": "runtime:continuity",
            "actor": "runtime", "content": canonical({"invocation": invocation, "process_id": os.getpid(),
                "base_version": state["version"], "previous_head": head,
                "inherited_commitments": [k for k, v in state["commitments"].items() if v["status"] == "open"],
                "scope": "Receipt proves state delivery to the provider boundary, not model comprehension."})})
        from .providers import RESEARCH_SYSTEM, SCHEMA
        request = {"system": SYSTEM + (RESEARCH_SYSTEM if state.get("charter") else ""),
                   "context": self.context(state, receipt), "response_schema": SCHEMA}
        if state.get("charter") and len(canonical(request)) > self.config["max_context_chars"]:
            request["context"]["recent_journal"] = []
            request["context"]["notebooks"] = request["context"]["notebooks"][-4:]
            request["context"]["working_notebook"] = None
            request["context"]["projects"] = [{**p, "reason": p["reason"][:120], "question": p["question"][:300],
                                               "next_step": p["next_step"][:300], "title": p["title"][:120]}
                                              for p in request["context"]["projects"]]
            # Retain every open obligation and belief ID; excerpts are explicitly labeled.
            for collection, fields in (("commitments", ("task", "reason")), ("beliefs", ("statement", "reason"))):
                request["context"][collection] = [{**item, **{key:item[key][:200] for key in fields},
                                                   "context_excerpt": True} for item in request["context"][collection]]
            for evidence in request["context"]["evidence"]:
                evidence["content"] = evidence["content"][:1000]
                evidence["context_excerpt"] = True
        require(len(canonical(request)) <= self.config["max_context_chars"],
                "Context ceiling reached; human review required, no model call made")
        self.store.append("invocation_started", {"id": invocation, "provider": provider, "model": model,
            "charged": charged, "quota_day": day, "base_version": state["version"], "request": request,
            "request_hash": digest(request), "process_id": os.getpid()})
        return invocation, request

    def finish(self, invocation, raw, metadata=None, crash=False):
        state = self.store.load()
        require(state["pending"] == invocation, "Response does not match the pending invocation")
        try:
            require(isinstance(raw, str) and len(raw) <= 64000, "Response exceeds 64,000 characters")
            proposal = json.loads(raw, parse_constant=lambda x: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
            result = transition(state, proposal, invocation)
        except (ValueError, TypeError, KeyError) as exc:
            reason = str(exc)[:1000]
            self.store.append("rejected", {"id": invocation, "reason": reason,
                                          "raw_response": str(raw)[:64000], "metadata": metadata or {}})
            return {"status": "rejected", "id": invocation, "reason": reason}
        fields = ["version", "beliefs", "commitments", "journal"]
        if state.get("charter"):
            fields += ["projects", "notebooks", "research"]
        result_hash = digest({k: result[k] for k in fields})
        self.store.append("accepted", {"id": invocation, "proposal": proposal, "raw_response": raw,
                                       "metadata": metadata or {}, "result_hash": result_hash, "hash_fields": fields}, crash=crash)
        return {"status": "accepted", "id": invocation, "cycle": result["version"]}

    def run(self, provider, crash_at=None, checkpoint=None, collector=None):
        with self.store.lock():
            self.initialize()
            self.recover()
            if collector:
                collector(self)
            invocation, request = self.start(provider.name, provider.model, provider.charged)
            if checkpoint:
                checkpoint()  # Remote reservation must succeed before the model call.
            if crash_at == "after-start":
                os._exit(85)
            try:
                raw, metadata = provider.propose(request)
            except Exception as exc:
                reason = str(exc)[:1000] if isinstance(exc, Rejected) else f"Provider failed ({type(exc).__name__}); no automatic retry"
                self.store.append("failed", {"id": invocation, "reason": reason})
                if checkpoint:
                    checkpoint()
                return {"status": "failed", "id": invocation, "reason": reason}
            result = self.finish(invocation, raw, metadata, crash=crash_at == "during-commit")
            if checkpoint:
                checkpoint()
            return result
