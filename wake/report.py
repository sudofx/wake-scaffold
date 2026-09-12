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
    text = text.replace("WAKE✳︎", "WAKE✳").replace("WAKE✳", "WAKE✳︎")
    fence = "```"
    while fence in text:
        fence += "`"
    return f"{fence}{language}\n{text}\n{fence}"


def _html_pre(value):
    text = value if isinstance(value, str) else _pretty(value)
    # Presentation-only normalization: keep canonical JSON untouched while forcing
    # the text-style asterisk in readable exports, including historical prompts.
    text = text.replace("WAKE✳︎", "WAKE✳").replace("WAKE✳", "WAKE✳︎")
    return f"<pre>{html.escape(text)}</pre>"


def _human_events_markdown(events, head):
    lines = [
        "# WAKE✳︎ — Human-readable event history",
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
        "# WAKE✳︎ — Human-readable durable state",
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
    favicon = "data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 64 64%27%3E%3Crect width=%2764%27 height=%2764%27 rx=%2712%27 fill=%27%23f7f3ea%27/%3E%3Cpath d=%27M32 9v46M9 32h46M15.7 15.7l32.6 32.6M48.3 15.7L15.7 48.3%27 stroke=%27%23286d72%27 stroke-width=%276%27 stroke-linecap=%27round%27/%3E%3C/svg%3E"
    return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<meta name=\"theme-color\" media=\"(prefers-color-scheme: light)\" content=\"#f7f3ea\"><meta name=\"theme-color\" media=\"(prefers-color-scheme: dark)\" content=\"#24283b\">
<link rel=\"icon\" href=\"{favicon}\"><title>{html.escape(title)} · WAKE✳︎</title>
<script>try{{const saved=localStorage.getItem('wake-theme');const dark=saved?saved==='dark':matchMedia('(prefers-color-scheme:dark)').matches;if(dark)document.documentElement.dataset.theme='dark'}}catch{{}}</script>
<style>
:root{{--paper:#f7f3ea;--ink:#242335;--muted:#615f6f;--line:#d8d0c5;--accent:#7b3fc6;--green:#286d72;--pale:#ece6f0;--surface:#fffaf2;--mono:ui-monospace,SFMono-Regular,Consolas,monospace;--sans:Arial,Helvetica,sans-serif;--serif:Georgia,'Times New Roman',serif}}
:root[data-theme=dark]{{--paper:#24283b;--ink:#c0caf5;--muted:#a9b1d6;--line:#414868;--accent:#c69cff;--green:#7dcfff;--pale:#292e42;--surface:#1f2335}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 var(--sans)}}a{{color:inherit;text-decoration:none}}a:hover{{text-decoration:underline;text-underline-offset:5px}}button,summary{{font:inherit;color:inherit}}button{{cursor:pointer}}main{{max-width:1120px;margin:auto;padding:32px 28px 90px}}header{{border-bottom:1px solid var(--ink);padding-bottom:24px;margin-bottom:30px}}.topline{{display:flex;align-items:center;justify-content:space-between;gap:18px}}.wordmark{{font-size:30px;font-weight:900;letter-spacing:-1.7px}}.wordmark b{{color:var(--green)}}.theme-toggle{{border:1px solid var(--line);background:var(--surface);padding:8px 10px;font:10px var(--mono);letter-spacing:.08em}}.eyebrow{{font:10px var(--mono);letter-spacing:1.5px;color:var(--green);margin:26px 0 10px}}h1{{font:400 clamp(2.4rem,6vw,4.8rem)/1.03 var(--serif);letter-spacing:-.035em;margin:.1em 0 .3em}}h2{{font:400 1.7rem/1.2 var(--serif);margin:38px 0 14px}}h3{{font-size:14px;margin:24px 0 10px}}nav{{display:flex;gap:20px;flex-wrap:wrap;margin-top:18px;font:10px var(--mono);color:var(--muted)}}.meta{{color:var(--muted);font:11px/1.6 var(--mono)}}details{{background:var(--surface);border:1px solid var(--line);margin:12px 0;padding:0 16px}}summary{{cursor:pointer;padding:15px 0;font:11px var(--mono);color:var(--green)}}.inside{{border-top:1px solid var(--line);padding:14px 0 18px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:var(--pale);padding:16px;font:11px/1.7 var(--mono);max-height:560px;overflow:auto}}code{{font-family:var(--mono);overflow-wrap:anywhere}}.tag{{display:inline-block;border:1px solid var(--line);padding:2px 8px;font-size:.78rem;margin-right:8px;color:var(--accent)}}.event-links{{font-size:.9rem;color:var(--muted)}}hr{{border:0;border-top:1px solid var(--line);margin:28px 0}}@media(max-width:680px){{main{{padding:24px 18px 70px}}h1{{font-size:2.7rem}}.topline{{align-items:flex-start}}}}
</style></head><body><main><header><div class=\"topline\"><a class=\"wordmark\" href=\"index.html\">WAKE<b>✳︎</b></a><button id=\"theme-toggle\" class=\"theme-toggle\" type=\"button\">DARK</button></div><div class=\"eyebrow\">READABLE EXPORT</div><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p><p class=\"meta\">Verified head: <code>{html.escape(head)}</code></p><nav><a href=\"index.html\">Main journal</a><a href=\"{html.escape(markdown_href)}\">Markdown source</a><a href=\"{html.escape(raw_href)}\">Raw data</a></nav></header>{body}</main><script>(()=>{{const b=document.getElementById('theme-toggle');const sync=()=>{{const d=document.documentElement.dataset.theme==='dark';b.textContent=d?'LIGHT':'DARK';b.setAttribute('aria-label',d?'Use light theme':'Use dark theme')}};sync();b.addEventListener('click',()=>{{const d=document.documentElement.dataset.theme==='dark';if(d)delete document.documentElement.dataset.theme;else document.documentElement.dataset.theme='dark';try{{localStorage.setItem('wake-theme',d?'light':'dark')}}catch{{}}sync()}})}})();</script></body></html>"""

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


def _reading_page(title, eyebrow, body, source_href, back_href="../index.html"):
    """Standalone browser reading page; Markdown remains a secondary flat artifact."""
    favicon = "data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 64 64%27%3E%3Crect width=%2764%27 height=%2764%27 rx=%2712%27 fill=%27%23f7f3ea%27/%3E%3Cpath d=%27M32 9v46M9 32h46M15.7 15.7l32.6 32.6M48.3 15.7L15.7 48.3%27 stroke=%27%23286d72%27 stroke-width=%276%27 stroke-linecap=%27round%27/%3E%3C/svg%3E"
    return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<meta name=\"theme-color\" media=\"(prefers-color-scheme: light)\" content=\"#f7f3ea\"><meta name=\"theme-color\" media=\"(prefers-color-scheme: dark)\" content=\"#24283b\"><link rel=\"icon\" href=\"{favicon}\"><title>{html.escape(title)} · WAKE✳︎</title>
<script>try{{const saved=localStorage.getItem('wake-theme');const dark=saved?saved==='dark':matchMedia('(prefers-color-scheme:dark)').matches;if(dark)document.documentElement.dataset.theme='dark'}}catch{{}}</script>
<style>
:root{{--paper:#f7f3ea;--ink:#242335;--muted:#615f6f;--line:#d8d0c5;--accent:#7b3fc6;--green:#286d72;--pale:#ece6f0;--surface:#fffaf2;--mono:ui-monospace,SFMono-Regular,Consolas,monospace;--sans:Arial,Helvetica,sans-serif;--serif:Georgia,'Times New Roman',serif}}
:root[data-theme=dark]{{--paper:#24283b;--ink:#c0caf5;--muted:#a9b1d6;--line:#414868;--accent:#c69cff;--green:#7dcfff;--pale:#292e42;--surface:#1f2335}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:17px/1.72 var(--serif)}}main{{max-width:840px;margin:auto;padding:34px 22px 90px}}header{{border-bottom:1px solid var(--ink);padding-bottom:24px;margin-bottom:34px}}.topline{{display:flex;align-items:center;justify-content:space-between;gap:18px}}.wordmark{{font:900 29px/1 var(--sans);letter-spacing:-1.7px;color:inherit;text-decoration:none}}.wordmark b{{color:var(--green)}}.theme-toggle{{border:1px solid var(--line);background:var(--surface);color:var(--ink);padding:8px 10px;font:10px var(--mono);letter-spacing:.08em;cursor:pointer}}h1{{font:400 clamp(2.4rem,7vw,4.8rem)/1.02 var(--serif);letter-spacing:-.035em;margin:.18em 0 .3em}}h2{{font:400 1.8rem/1.2 var(--serif);margin-top:2.2em}}h3{{font:700 14px var(--sans);margin-top:2em}}a{{color:var(--green)}}nav{{display:flex;gap:18px;flex-wrap:wrap;margin-top:17px;font:10px var(--mono)}}.eyebrow,.meta{{font:10px var(--mono);color:var(--muted);text-transform:uppercase;letter-spacing:.1em}}.eyebrow{{color:var(--green);margin-top:24px}}.lede{{font-size:1.25rem;line-height:1.55}}.note{{border-left:3px solid var(--accent);padding:2px 0 2px 18px;margin:28px 0}}.sources{{font-family:var(--sans);font-size:.95rem}}code{{font-family:var(--mono)}}hr{{border:0;border-top:1px solid var(--line);margin:34px 0}}small{{color:var(--muted)}}@media(max-width:680px){{main{{padding:24px 18px 70px}}h1{{font-size:2.7rem}}}}
</style></head><body><main><header><div class=\"topline\"><a class=\"wordmark\" href=\"{html.escape(back_href)}\">WAKE<b>✳︎</b></a><button id=\"theme-toggle\" class=\"theme-toggle\" type=\"button\">DARK</button></div><div class=\"eyebrow\">{html.escape(eyebrow)}</div><h1>{html.escape(title)}</h1><nav><a href=\"{html.escape(back_href)}\">WAKE site</a><a href=\"{html.escape(source_href)}\">Markdown source</a></nav></header>{body}</main><script>(()=>{{const b=document.getElementById('theme-toggle');const sync=()=>{{const d=document.documentElement.dataset.theme==='dark';b.textContent=d?'LIGHT':'DARK';b.setAttribute('aria-label',d?'Use light theme':'Use dark theme')}};sync();b.addEventListener('click',()=>{{const d=document.documentElement.dataset.theme==='dark';if(d)delete document.documentElement.dataset.theme;else document.documentElement.dataset.theme='dark';try{{localStorage.setItem('wake-theme',d?'light':'dark')}}catch{{}}sync()}})}})();</script></body></html>"""

def _notebook_html(notebook, state):
    source_items = []
    for eid in notebook["evidence"]:
        evidence = state["evidence"][eid]
        source_items.append(f'<li><a href="{html.escape(str(evidence["source"]))}">{html.escape(eid)}</a></li>')
    body = (
        f'<p class="lede">{html.escape(notebook["summary"])}</p>'
        f'<h2>Findings</h2><p>{html.escape(notebook["findings"])}</p>'
        f'<h2>Limitations and competing views</h2><p>{html.escape(notebook["limitations"])}</p>'
        f'<h2>Next questions</h2><p>{html.escape(notebook["next_questions"])}</p>'
        f'<h2>Collected sources</h2><ul class="sources">{"".join(source_items)}</ul>'
        f'<hr><p class="meta">Revision {notebook["revision"]} · AI-authored research synthesis; see source scopes in the journal.</p>'
    )
    return _reading_page(notebook["title"], "WAKE✳︎ / RESEARCH NOTEBOOK", body, notebook["id"] + ".md")


def _blog_html(post, state):
    paragraphs = "".join(f"<p>{html.escape(part)}</p>" for part in str(post["body"]).split("\n\n") if part.strip())
    lens = f'<div class="note"><div class="eyebrow">BOB’S LENS / PHILOSOPHICAL REFLECTION</div><p>{html.escape(post["lens"])}</p></div>' if post.get("lens") else ""
    notebooks = "".join(
        f'<li><a href="../notebooks/{html.escape(nid)}.html">{html.escape(state["notebooks"][nid]["title"])}</a> <small>· <a href="../notebooks/{html.escape(nid)}.md">Markdown source</a></small></li>'
        for nid in post["notebooks"])
    sources = "".join(
        f'<li><a href="{html.escape(str(state["evidence"][eid]["source"]))}">{html.escape(eid)}</a></li>'
        for eid in post["evidence"])
    correction = ""
    if post.get("superseded_by"):
        correction = f'<p class="note">Superseded by <a href="{html.escape(post["superseded_by"])}.html">{html.escape(post["superseded_by"])}</a>.</p>'
    body = (
        f'<p class="lede">{html.escape(post["lede"])}</p>{correction}{paragraphs}{lens}'
        f'<h2>Follow the receipts</h2><h3>Research notebooks</h3><ul class="sources">{notebooks}</ul>'
        f'<h3>Collected sources</h3><ul class="sources">{sources}</ul>'
        f'<p><a href="../index.html#history/{html.escape(post["created_by"])}">Exact wake and decision →</a></p>'
        '<hr><p class="meta">AI-authored from WAKE✳︎’s durable research record. Research claims link to evidence; philosophical reflections are reflections.</p>'
    )
    return _reading_page(post["title"], "BOB / WAKE✳︎ BLOG", body, post["id"] + ".md")


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
        # Browser UX is HTML-first. Markdown remains available as a flat source artifact.
        page = page.replace('href="journal.md">Markdown ↓</a>', 'href="events.html">Readable history →</a>')
        page = page.replace('Read the complete <a href="journal.md">Markdown journal</a> or download <a href="state.json">the durable state</a>.',
                            'Read the <a href="events.html">human-readable history</a> or <a href="state.html">human-readable durable state</a>.')
        page = page.replace('<a href="state.json">State →</a><a href="events.jsonl">History →</a><a href="journal.md">Markdown →</a>',
                            '<a href="state.html">State →</a><a href="events.html">History →</a><a href="journal.md">Journal source ↓</a>')
        page = page.replace("'.md'>Markdown ↓</a>", "'.html'>Standalone HTML →</a> · <a class=\"subtle\" href=\"blog/'+encodeURIComponent(post.id)+'.md\">Markdown source ↓</a>")
        lines = ["# WAKE✳︎ — The journal", "", "> Disposable models. Durable state. Receipts for everything.", "",
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
            atomic_write(target / "notebooks" / (notebook["id"] + ".html"), _notebook_html(notebook, state))
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
                      "AI-authored from WAKE✳︎'s durable research record. Research claims link to evidence; philosophical reflections are reflections.", ""]
            atomic_write(target / "blog" / (post["id"] + ".md"), newline.join(parts))
            atomic_write(target / "blog" / (post["id"] + ".html"), _blog_html(post, state))
        if experiment:
            atomic_write(target / "experiment.json", json.dumps(experiment, indent=2))
        else:
            (target / "experiment.json").unlink(missing_ok=True)
        atomic_write(target / "index.html", page)
        return {"path": str((target / "index.html").resolve()), "cycles": state["version"], "head": head}
