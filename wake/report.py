"""Portable static journal. No CDN, build pipeline, tracking, or API-key exposure."""

from datetime import datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from .store import canonical, now


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def export(store, destination="site", experiment=None, operation=None):
    with store.lock():
        state = store.load()
        events = store.events()
        _, head = store.replay()
        if experiment is None:
            evidence_file = store.directory / "experiment.json"
            experiment = json.loads(evidence_file.read_text()) if evidence_file.exists() else None
        data = {"state": state, "events": events, "head": head, "generated": now(),
                "experiment": experiment, "timezone": "America/Los_Angeles", "operation": operation}
        target = Path(destination)
        target.mkdir(parents=True, exist_ok=True)
        assets = Path(__file__).parent / "assets"
        template = (assets / "index.html").read_text()
        embedded = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
        page = template.replace("/* WAKE_STYLE */", (assets / "style.css").read_text())
        page = page.replace("/* WAKE_SCRIPT */", (assets / "app.js").read_text())
        page = page.replace("/* PET_SCRIPT */", (assets / "pet.js").read_text()).replace("WAKE_DATA", embedded)
        lines = ["# WAKE✳ — The journal", "", "> Disposable models. Durable state. Receipts for everything.", "",
                 f"Objective: {state['objective']}", "", f"Verified head: `{head}`", "",
                 "Fixture entries are deterministic simulations, not live model experiments.", ""]
        for item in reversed(state["journal"]):
            invocation = state["invocations"][item["invocation"]]
            date = datetime.fromisoformat(invocation["time"]).astimezone(ZoneInfo("America/Los_Angeles"))
            lines += [f"## {item['cycle']:03d} · {item['title']}", "",
                      f"{date:%B %d, %Y · %I:%M %p %Z} · {invocation['provider']} / {invocation['model']}", "",
                      item["summary"], "", f"Invocation: `{item['invocation']}`", ""]
        atomic_write(target / "journal.md", "\n".join(lines))
        atomic_write(target / "state.json", json.dumps(state, indent=2, ensure_ascii=False))
        atomic_write(target / "events.jsonl", "".join(canonical(event) + "\n" for event in events))
        atomic_write(target / "head.txt", head + "\n")
        for notebook in state.get("notebooks", {}).values():
            sources = "\n".join(f"- [{eid}]({state['evidence'][eid]['source']})" for eid in notebook["evidence"])
            markdown = (f"# {notebook['title']}\n\n{notebook['summary']}\n\n## Findings\n\n{notebook['findings']}\n\n"
                        f"## Limitations and competing views\n\n{notebook['limitations']}\n\n"
                        f"## Next questions\n\n{notebook['next_questions']}\n\n## Collected sources\n\n{sources}\n\n"
                        f"Revision {notebook['revision']} · AI-authored research synthesis; see source scopes in the journal.\n")
            atomic_write(target / "notebooks" / (notebook["id"] + ".md"), markdown)
        if experiment:
            atomic_write(target / "experiment.json", json.dumps(experiment, indent=2))
        else:
            (target / "experiment.json").unlink(missing_ok=True)
        atomic_write(target / "index.html", page)
        return {"path": str((target / "index.html").resolve()), "cycles": state["version"], "head": head}
