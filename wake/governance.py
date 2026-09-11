"""Pure, deterministic transition rules. No model gets to edit the rulebook."""

from copy import deepcopy
import json
import math
import re


class Rejected(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Rejected(message)


def text(value, label, maximum=2000):
    require(isinstance(value, str) and 0 < len(value.strip()) <= maximum,
            f"{label} must be nonempty text, at most {maximum} characters")
    return value


def keys(value, expected, label):
    require(isinstance(value, dict) and set(value) == set(expected.split()),
            f"{label} fields must be exactly: {expected}")


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", value),
            "IDs must use 1–80 letters, digits, underscores or hyphens")


def references(value, state):
    require(isinstance(value, list) and 1 <= len(value) <= 12,
            "Changes require 1–12 evidence references")
    require(all(isinstance(v, str) and v in state["evidence"] for v in value),
            "Evidence reference does not exist")
    require(len(set(value)) == len(value), "Duplicate evidence reference")


def _limited_sources(evidence):
    limited = ("abstract", "preprint", "metadata", "incomplete", "truncated")
    scopes = []
    for item in evidence:
        try:
            scopes.append(str(json.loads(item["content"]).get("scope", "")).lower())
        except (ValueError, TypeError):
            scopes.append("")
    return bool(scopes) and all(any(word in scope for word in limited) for scope in scopes)


def _blog_language(action, evidence):
    prose = " ".join(str(action.get(key, "")) for key in ("title", "lede", "body", "lens", "reason"))
    lower = prose.lower()
    # Explicitly stating the scientific boundary is responsible writing, not a
    # prohibited bridge. Remove those statements before looking for causal ones.
    lower = re.sub(r"quantum.{0,40}(does not|doesn't|cannot|can't|is not).{0,50}"
                   r"(prove|explain|cause|validate).{0,70}"
                   r"(consciousness|psychology|empathy|relationships?|communication|personal growth)", "", lower)
    bridge = re.search(r"quantum.{0,100}(proves?|explains?|causes?|validates?).{0,100}"
                       r"(consciousness|psychology|empathy|relationships?|communication|personal growth)", lower)
    reverse = re.search(r"(consciousness|psychology|empathy|relationships?|communication|personal growth)"
                        r".{0,100}(is|are).{0,40}quantum", lower)
    require(not bridge and not reverse,
            "Quantum-Carnegie connections must remain philosophical metaphor, not scientific causation")
    if _limited_sources(evidence):
        calibrated = re.sub(r"\b(not|isn't|is not|has not been|cannot be)\s+"
                            r"(rigorous|confirmed|settled|proven|definitive|conclusive)\b", "", lower)
        inflated = re.search(r"\b(rigorous|confirmed|settled|proven|definitive|conclusive)\b", calibrated)
        require(not inflated, "Limited or abstract-only sources cannot support certainty language")


def transition(state, proposal, invocation):
    """Return a new projection or reject the entire proposal, never a partial write."""
    keys(proposal, "base_version title summary actions", "Proposal")
    require(type(proposal["base_version"]) is int and proposal["base_version"] == state["version"],
            "Stale or invalid base_version")
    text(proposal["title"], "Title", 120)
    text(proposal["summary"], "Summary", 2400)
    require(isinstance(proposal["actions"], list) and len(proposal["actions"]) <= 12,
            "At most 12 actions per invocation")
    result = {**state, "beliefs": deepcopy(state["beliefs"]),
              "commitments": deepcopy(state["commitments"]), "journal": list(state["journal"]),
              "posts": deepcopy(state.get("posts", {}))}
    if state.get("charter"):
        for collection in ("projects", "notebooks", "research"):
            result[collection] = deepcopy(state.get(collection, {}))
    for action in proposal["actions"]:
        require(isinstance(action, dict), "Each action must be an object")
        kind = action.get("type")
        if kind == "belief":
            keys(action, "type id statement confidence status evidence reason", "Belief")
            identifier(action["id"])
            text(action["statement"], "Statement")
            text(action["reason"], "Reason")
            require(type(action["confidence"]) in (int, float) and
                    math.isfinite(action["confidence"]) and 0 <= action["confidence"] <= 1,
                    "Confidence must be a finite number between 0 and 1")
            require(action["status"] in ("active", "retracted"), "Invalid belief status")
            references(action["evidence"], result)
            old = result["beliefs"].get(action["id"])
            if old:
                require(any(e not in old["evidence"] for e in action["evidence"]),
                        "Belief review requires new evidence")
            else:
                require(action["status"] == "active", "Cannot retract a nonexistent belief")
                require(len(result["beliefs"]) < 40, "Belief capacity reached; review existing beliefs")
            require(action["status"] != "retracted" or action["confidence"] == 0,
                    "Retracted beliefs must have zero confidence")
            result["beliefs"][action["id"]] = {
                **action, "evidence": list(dict.fromkeys((old or {}).get("evidence", []) + action["evidence"])),
                "updated_by": invocation, "updated_version": state["version"] + 1,
            }
        elif kind == "commit":
            keys(action, "type id task due_cycle reason", "Commitment")
            identifier(action["id"])
            text(action["task"], "Task")
            text(action["reason"], "Reason")
            require(action["id"] not in result["commitments"], "Commitment ID already exists")
            require(type(action["due_cycle"]) is int and
                    state["version"] + 1 < action["due_cycle"] <= state["version"] + 101,
                    "Commitment must be due in a future cycle, within 100 cycles")
            require(sum(c["status"] == "open" for c in result["commitments"].values()) < 20,
                    "At most 20 open commitments")
            result["commitments"][action["id"]] = {
                **action, "status": "open", "created_by": invocation,
                "created_version": state["version"] + 1,
            }
        elif kind == "resolve":
            keys(action, "type id status evidence reason", "Resolution")
            identifier(action["id"])
            references(action["evidence"], result)
            text(action["reason"], "Reason")
            old = result["commitments"].get(action["id"])
            require(old is not None and old["status"] == "open", "Only open commitments can be resolved")
            require(action["status"] == "fulfilled", "Models cannot cancel commitments; ask a human")
            require(old["created_by"] != invocation, "A commitment must survive at least one invocation")
            require(any(result["evidence"][e]["version"] >= old["created_version"] for e in action["evidence"]),
                    "Resolution requires evidence recorded after the commitment")
            result["commitments"][action["id"]] = {
                **old, "status": "fulfilled", "evidence": action["evidence"],
                "resolution_reason": action["reason"], "resolved_by": invocation,
                "resolved_version": state["version"] + 1,
            }
        elif kind == "project":
            from .research import DOMAINS
            require(bool(state.get("charter")), "Research charter is not enabled")
            keys(action, "type id title question domain status next_step reason", "Project")
            identifier(action["id"])
            for key in ("title", "question", "next_step", "reason"):
                text(action[key], key, 1000)
            require(action["domain"] in DOMAINS, "Choose a charter research domain")
            require(action["status"] in ("active", "parked", "completed"), "Invalid project status")
            old = result["projects"].get(action["id"])
            if not old:
                require(action["status"] == "active", "A new project starts active")
            if action["status"] == "active":
                require(sum(p["status"] == "active" and p["id"] != action["id"] for p in result["projects"].values()) < 3,
                        "Finish or park work before starting a fourth active project")
            if action["status"] == "completed":
                require(any(n["project"] == action["id"] for n in result["notebooks"].values()),
                        "Completed projects need a published research notebook")
            result["projects"][action["id"]] = {**action, "created_version": (old or {}).get("created_version", state["version"] + 1),
                "updated_version": state["version"] + 1, "updated_by": invocation}
        elif kind == "research":
            from .research import DOMAINS
            require(bool(state.get("charter")), "Research charter is not enabled")
            keys(action, "type id project query domain reason" + (" url" if "url" in action else ""), "Research request")
            identifier(action["id"])
            text(action["query"], "Query", 200)
            text(action["reason"], "Reason", 1000)
            if "url" in action:
                from .research import allowed_url
                allowed_url(action["url"])
            require(action["domain"] in DOMAINS, "Invalid research domain")
            require(action["project"] in result["projects"], "Research needs an existing project")
            require(action["id"] not in result["research"], "Research request ID already exists")
            require(sum(r["status"] == "queued" for r in result["research"].values()) < 4, "At most four queued source searches")
            result["research"][action["id"]] = {**action, "status": "queued", "created_by": invocation}
        elif kind == "notebook":
            require(bool(state.get("charter")), "Research charter is not enabled")
            keys(action, "type id project title summary findings limitations next_questions evidence reason", "Notebook")
            identifier(action["id"])
            require(action["project"] in result["projects"], "Notebook needs an existing project")
            for key, limit in (("title", 120), ("summary", 800), ("findings", 10000),
                               ("limitations", 2400), ("next_questions", 1600), ("reason", 1000)):
                text(action[key], key, limit)
            references(action["evidence"], result)
            cited = [result["evidence"][e] for e in action["evidence"]]
            require(all(e.get("actor") == "collector" and e.get("scope") == "collected" for e in cited),
                    "Research notebooks must cite successfully retrieved external sources")
            require(len({e["source"] for e in cited}) >= 2, "Research notebooks need at least two distinct retrieved source URLs")
            old = result["notebooks"].get(action["id"])
            if old:
                require(old["project"] == action["project"], "A notebook cannot change projects")
                require(action["findings"] != old["findings"] and any(e not in old["evidence"] for e in action["evidence"]),
                        "A revision needs changed findings and newly retrieved evidence")
            result["notebooks"][action["id"]] = {**action, "revision": (old or {}).get("revision", 0) + 1,
                "created_version": (old or {}).get("created_version", state["version"] + 1),
                "updated_version": state["version"] + 1, "updated_by": invocation,
                "domain": result["projects"][action["project"]]["domain"]}
        elif kind == "blog":
            require(bool(state.get("charter")), "Research charter is not enabled")
            require(action is proposal["actions"][-1], "A blog action must be last so its research is already validated")
            expected = "type id project title lede body notebooks evidence reason" + (" lens" if "lens" in action else "") + (" supersedes" if "supersedes" in action else "")
            keys(action, expected, "Blog post")
            identifier(action["id"])
            require(action["id"] not in result["posts"], "Blog post ID already exists")
            require(action["project"] in result["projects"], "Blog post needs an existing project")
            for key, limit in (("title", 120), ("lede", 500), ("body", 6000), ("reason", 1000)):
                text(action[key], key, limit)
            require(len(action["body"].strip()) >= 300, "Blog posts must contain at least 300 characters")
            if "lens" in action:
                text(action["lens"], "Bob's Lens", 320)
            require(isinstance(action["notebooks"], list) and 1 <= len(action["notebooks"]) <= 3
                    and len(set(action["notebooks"])) == len(action["notebooks"]),
                    "Blog posts must reference 1–3 distinct notebooks")
            notebooks = [result["notebooks"].get(item) for item in action["notebooks"]]
            require(all(notebook and notebook["project"] == action["project"] for notebook in notebooks),
                    "Blog notebooks must exist and belong to the related project")
            references(action["evidence"], result)
            cited = [result["evidence"][item] for item in action["evidence"]]
            require(all(item.get("actor") == "collector" and item.get("scope") == "collected" for item in cited),
                    "Blog research support must use collected external evidence")
            require(len({item["source"] for item in cited}) >= 2,
                    "Blog posts need evidence from at least two distinct source URLs")
            notebook_evidence = {item for notebook in notebooks for item in notebook["evidence"]}
            require(set(action["evidence"]) <= notebook_evidence,
                    "Blog evidence must be traceable through its referenced notebooks")
            qualifying_notebooks = {item["id"] for item in proposal["actions"]
                                    if item.get("type") == "notebook" and item.get("project") == action["project"]}
            completed = any(item.get("type") == "project" and item.get("id") == action["project"]
                            and item.get("status") == "completed" for item in proposal["actions"])
            require(bool(qualifying_notebooks & set(action["notebooks"])) or completed,
                    "A blog post requires a new/revised notebook or meaningful project completion in this wake")
            supersedes = action.get("supersedes")
            if supersedes:
                require(supersedes in result["posts"], "A correction must reference an existing blog post")
                require(not result["posts"][supersedes].get("superseded_by"),
                        "The earlier blog post is already superseded")
            _blog_language(action, cited)
            post = {**action, "created_by": invocation, "created_version": state["version"] + 1,
                    "status": "current"}
            result["posts"][action["id"]] = post
            if supersedes:
                result["posts"][supersedes] = {**result["posts"][supersedes],
                                               "status": "superseded", "superseded_by": action["id"]}
        else:
            raise Rejected(f"Action is not allowed: {kind!r}")
    result["version"] += 1
    result["journal"].append({"cycle": result["version"], "invocation": invocation,
                              "title": proposal["title"], "summary": proposal["summary"]})
    return result
