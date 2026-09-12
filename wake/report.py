"""Portable static journal. No CDN, build pipeline, tracking, or API-key exposure."""

from datetime import datetime
import html
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


def _pretty(value):
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=False)


def _md_code(value, language="json"):
    text = value if isinstance(value, str) else _pretty(value)
    fence = "```"
    while fence in text:
        fence += "`"
    return f"{fence}{language}\n{text}\n{fence}"


def _html_pre(value):
    text = value if isinstance(value, str) else _pretty(value)
    return f"<pre>{html.escape(text)}</pre>"


def _human_events_markdown(events, head):
    lines = [
        "# WAKE✳ — Human-readable event history",
        "",
        "> A presentation layer over `events.jsonl`. The JSONL file remains the canonical audit export.",
        "",
        f"Verified head: `{head}`",
        "",
        "[Open the HTML version](events.html) · [Raw JSONL](events.jsonl) · [Readable state](state.md)",
        "",
    ]
    for event in reversed(events):
        payload = event.get("payload", {})
        event_id = payload.get("id", "system")
        lines += [
            f"## Event {event['seq']:04d} · `{event['kind']}`",
            "",
            f"**Time:** {event['time']}  ",
            f"**ID:** `{event_id}`  ",
            f"**Hash:** `{event['hash']}`  ",
            f"**Previous hash:** `{event['prev_hash']}`",
            "",
        ]
        kind = event["kind"]
        if kind == "invocation_started":
            request = payload.get("request", {})
            lines += [
                f"**Provider / model:** `{payload.get('provider', '')}` / `{payload.get('model', '')}`  ",
                f"**Base version:** {payload.get('base_version', '')}  ",
                f"**Request hash:** `{payload.get('request_hash', '')}`",
                "",
                "### System prompt",
                "",
                _md_code(request.get("system", ""), "text"),
                "",
                "### Context sent to the model",
                "",
                _md_code(request.get("context", {})),
                "",
                "### Response schema",
                "",
                _md_code(request.get("response_schema", {})),
                "",
            ]
        elif kind == "accepted":
            lines += ["### Accepted proposal", "", _md_code(payload.get("proposal", {})), ""]
            if payload.get("raw_response") is not None:
                lines += ["### Raw model response", "", _md_code(payload["raw_response"], "json"), ""]
            if payload.get("result_hash"):
                lines += [f"**Result hash:** `{payload['result_hash']}`", ""]
        elif kind == "rejected":
            if payload.get("reason"):
                lines += [f"**Reason:** {payload['reason']}", ""]
            if payload.get("raw_response") is not None:
                lines += ["### Raw rejected response", "", _md_code(payload["raw_response"], "text"), ""]
        elif kind == "failed":
            lines += [f"**Reason:** {payload.get('reason', '')}", ""]
        elif kind == "observation":
            lines += [
                f"**Source:** `{payload.get('source', '')}`  ",
                f"**Actor:** `{payload.get('actor', '')}`",
                "",
                payload.get("content", ""),
                "",
            ]
        else:
            lines += ["### Payload", "", _md_code(payload), ""]
    return "\n".join(lines).rstrip() + "\n"


def _human_state_markdown(state, head):
    lines = [
        "# WAKE✳ — Human-readable durable state",
        "",
        "> A presentation layer over `state.json`. The JSON file remains the canonical state export.",
        "",
        f"**Version:** {state.get('version', 0)}  ",
        f"**Objective:** {state.get('objective', '')}  ",
        f"**Focus:** {state.get('focus', '')}  ",
        f"**Verified head:** `{head}`",
        "",
        "[Open the HTML version](state.html) · [Raw JSON](state.json) · [Readable history](events.md)",
        "",
    ]
    sections = [
        ("Beliefs", state.get("beliefs", {})),
        ("Commitments", state.get("commitments", {})),
        ("Projects", state.get("projects", {})),
        ("Notebooks", state.get("notebooks", {})),
        ("Invocations", state.get("invocations", {})),
        ("Evidence", state.get("evidence", {})),
        ("Journal", state.get("journal", [])),
        ("Research", state.get("research", {})),
        ("Blog posts", state.get("posts", {})),
    ]
    for title, collection in sections:
        lines += [f"## {title}", ""]
        if not collection:
            lines += ["_None recorded._", ""]
            continue
        if isinstance(collection, dict):
            for key, item in collection.items():
                label = item.get("title") if isinstance(item, dict) else None
                heading = f"### `{key}`" + (f" · {label}" if label else "")
                lines += [heading, "", _md_code(item), ""]
        else:
            for index, item in enumerate(collection, 1):
                label = item.get("title") if isinstance(item, dict) else None
                heading = f"### {index:03d}" + (f" · {label}" if label else "")
                lines += [heading, "", _md_code(item), ""]
    return "\n".join(lines).rstrip() + "\n"


def _human_page(title, subtitle, body, head, raw_href, markdown_href):
    return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>{html.escape(title)}</title>
<style>
:root{{color-scheme:light dark;--bg:#f3f0e8;--fg:#181818;--muted:#666;--card:#fff;--line:#d7d1c5;--accent:#b64a2c}}
@media(prefers-color-scheme:dark){{:root{{--bg:#171715;--fg:#eee;--muted:#aaa;--card:#22221f;--line:#3a3933;--accent:#e47b58}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif}}main{{max-width:1100px;margin:auto;padding:28px 18px 80px}}header{{border-bottom:1px solid var(--line);padding-bottom:22px;margin-bottom:24px}}h1{{font-size:clamp(2rem,5vw,4rem);line-height:1;margin:.15em 0}}h2{{margin-top:0}}a{{color:var(--accent)}}nav{{display:flex;gap:16px;flex-wrap:wrap;margin-top:14px}}.meta{{color:var(--muted)}}details{{background:var(--card);border:1px solid var(--line);border-radius:12px;margin:12px 0;padding:0 14px}}summary{{cursor:pointer;padding:14px 0;font-weight:700}}.inside{{border-top:1px solid var(--line);padding:12px 0 18px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:rgba(127,127,127,.08);padding:14px;border-radius:8px;font:13px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace}}code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}}.tag{{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:1px 8px;font-size:.78rem;margin-right:8px}}.event-links{{font-size:.9rem}}hr{{border:0;border-top:1px solid var(--line);margin:24px 0}}
</style></head><body><main><header><div class=\"meta\">WAKE✳ / READABLE EXPORT</div><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p><p class=\"meta\">Verified head: <code>{html.escape(head)}</code></p><nav><a href=\"index.html\">Main journal</a><a href=\"{html.escape(markdown_href)}\">Markdown</a><a href=\"{html.escape(raw_href)}\">Raw data</a></nav></header>{body}</main></body></html>"""


def _human_events_html(events, head):
    cards = []
    for event in reversed(events):
        payload = event.get("payload", {})
        event_id = payload.get("id", "system")
        blocks = [
            f"<p class=\"meta\">Time: {html.escape(event['time'])}<br>ID: <code>{html.escape(str(event_id))}</code><br>Hash: <code>{html.escape(event['hash'])}</code><br>Previous hash: <code>{html.escape(event['prev_hash'])}</code></p>"
        ]
        kind = event["kind"]
        if kind == "invocation_started":
            request = payload.get("request", {})
            blocks += [
                f"<p><strong>Provider / model:</strong> <code>{html.escape(str(payload.get('provider','')))}</code> / <code>{html.escape(str(payload.get('model','')))}</code><br><strong>Base version:</strong> {html.escape(str(payload.get('base_version','')))}<br><strong>Request hash:</strong> <code>{html.escape(str(payload.get('request_hash','')))}</code></p>",
                "<h3>System prompt</h3>" + _html_pre(request.get("system", "")),
                "<h3>Context sent to the model</h3>" + _html_pre(request.get("context", {})),
                "<h3>Response schema</h3>" + _html_pre(request.get("response_schema", {})),
            ]
        elif kind == "accepted":
            blocks += ["<h3>Accepted proposal</h3>" + _html_pre(payload.get("proposal", {}))]
            if payload.get("raw_response") is not None:
                blocks += ["<h3>Raw model response</h3>" + _html_pre(payload["raw_response"])]
            if payload.get("result_hash"):
                blocks += [f"<p><strong>Result hash:</strong> <code>{html.escape(payload['result_hash'])}</code></p>"]
        elif kind == "rejected":
            if payload.get("reason"):
                blocks += [f"<p><strong>Reason:</strong> {html.escape(str(payload['reason']))}</p>"]
            if payload.get("raw_response") is not None:
                blocks += ["<h3>Raw rejected response</h3>" + _html_pre(payload["raw_response"])]
        elif kind == "failed":
            blocks += [f"<p><strong>Reason:</strong> {html.escape(str(payload.get('reason','')))}</p>"]
        elif kind == "observation":
            blocks += [
                f"<p><strong>Source:</strong> <code>{html.escape(str(payload.get('source','')))}</code><br><strong>Actor:</strong> <code>{html.escape(str(payload.get('actor','')))}</code></p>",
                f"<p>{html.escape(str(payload.get('content','')))}</p>",
            ]
        else:
            blocks += ["<h3>Payload</h3>" + _html_pre(payload)]
        cards.append(
            f"<details id=\"event-{event['seq']}\"><summary><span class=\"tag\">#{event['seq']:04d}</span> {html.escape(kind)} · {html.escape(str(event_id))}</summary><div class=\"inside\">{''.join(blocks)}</div></details>"
        )
    body = "<p class=\"event-links\">Newest event first. Use your browser’s Find command to search prompts, evidence IDs, invocation IDs, or hashes.</p>" + "".join(cards)
    return _human_page("Human-readable event history", "Every recorded event, including exact model requests and replies, without changing the canonical JSONL.", body, head, "events.jsonl", "events.md")


def _human_state_html(state, head):
    sections = [
        ("Beliefs", state.get("beliefs", {})), ("Commitments", state.get("commitments", {})),
        ("Projects", state.get("projects", {})), ("Notebooks", state.get("notebooks", {})),
        ("Invocations", state.get("invocations", {})), ("Evidence", state.get("evidence", {})),
        ("Journal", state.get("journal", [])), ("Research", state.get("research", {})),
        ("Blog posts", state.get("posts", {})),
    ]
    chunks = [f"<p><strong>Version:</strong> {html.escape(str(state.get('version',0)))}<br><strong>Objective:</strong> {html.escape(str(state.get('objective','')))}<br><strong>Focus:</strong> {html.escape(str(state.get('focus','')))}</p>"]
    for title, collection in sections:
        chunks.append(f"<h2>{html.escape(title)}</h2>")
        if not collection:
            chunks.append("<p class=\"meta\">None recorded.</p>")
            continue
        items = collection.items() if isinstance(collection, dict) else enumerate(collection, 1)
        for key, item in items:
            label = item.get("title") if isinstance(item, dict) else None
            summary = f"{key}" + (f" · {label}" if label else "")
            chunks.append(f"<details><summary>{html.escape(str(summary))}</summary><div class=\"inside\">{_html_pre(item)}</div></details>")
    return _human_page("Human-readable durable state", "The current projected state, reorganized for reading without changing the canonical JSON.", "".join(chunks), head, "state.json", "state.md")


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
        page = page.replace("/* HELP_SCRIPT */", (assets / "help.js").read_text())
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
        atomic_write(target / "state.md", _human_state_markdown(state, head))
        atomic_write(target / "state.html", _human_state_html(state, head))
        atomic_write(target / "events.md", _human_events_markdown(events, head))
        atomic_write(target / "events.html", _human_events_html(events, head))
        atomic_write(target / "head.txt", head + "\n")
        for notebook in state.get("notebooks", {}).values():
            sources = "\n".join(f"- [{eid}]({state['evidence'][eid]['source']})" for eid in notebook["evidence"])
            markdown = (f"# {notebook['title']}\n\n{notebook['summary']}\n\n## Findings\n\n{notebook['findings']}\n\n"
                        f"## Limitations and competing views\n\n{notebook['limitations']}\n\n"
                        f"## Next questions\n\n{notebook['next_questions']}\n\n## Collected sources\n\n{sources}\n\n"
                        f"Revision {notebook['revision']} · AI-authored research synthesis; see source scopes in the journal.\n")
            atomic_write(target / "notebooks" / (notebook["id"] + ".md"), markdown)
        for post in state.get("posts", {}).values():
            newline = chr(10)
            notebook_links = newline.join(
                f"- [{state['notebooks'][item]['title']}](../index.html#projects/notebook:{item})"
                for item in post["notebooks"])
            source_links = newline.join(
                f"- [{item}]({state['evidence'][item]['source']})" for item in post["evidence"])
            parts = [f"# {post['title']}", "", post["lede"], "", post["body"]]
            if post.get("lens"):
                parts += ["", "> **Bob's Lens — philosophical reflection**", "", f"> {post['lens']}"]
            if post.get("superseded_by"):
                parts += ["", f"This post was superseded by [{post['superseded_by']}](../index.html#blog/{post['superseded_by']})."]
            parts += ["", "## Follow the receipts", "", "### Research notebooks", "", notebook_links, "",
                      "### Collected sources", "", source_links, "",
                      f"[Exact wake and decision](../index.html#history/{post['created_by']})", "",
                      "AI-authored from WAKE✳'s durable research record. Research claims link to evidence; philosophical reflections are reflections.", ""]
            atomic_write(target / "blog" / (post["id"] + ".md"), newline.join(parts))
        if experiment:
            atomic_write(target / "experiment.json", json.dumps(experiment, indent=2))
        else:
            (target / "experiment.json").unlink(missing_ok=True)
        atomic_write(target / "index.html", page)
        return {"path": str((target / "index.html").resolve()), "cycles": state["version"], "head": head}
