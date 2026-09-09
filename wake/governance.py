"""Pure, deterministic transition rules. No model gets to edit the rulebook."""

from copy import deepcopy
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
              "commitments": deepcopy(state["commitments"]), "journal": list(state["journal"])}
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
        else:
            raise Rejected(f"Action is not allowed: {kind!r}")
    result["version"] += 1
    result["journal"].append({"cycle": result["version"], "invocation": invocation,
                              "title": proposal["title"], "summary": proposal["summary"]})
    return result
