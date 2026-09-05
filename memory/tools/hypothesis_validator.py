import json
import os
import sys


STATUS_VALUES = {
    "untested",
    "confirmed",
    "refuted",
    "inconclusive",
}

HISTORY_REQUIRED_FIELDS = [
    "date",
    "status",
    "evidence",
    "conclusion",
]


def find_file(filename):
    candidates = [
        filename,
        os.path.join("memory", filename),
        os.path.join("..", "memory", filename),
        os.path.join("..", filename),
    ]

    # Also resolve relative to this script. The sandbox may execute tools
    # with tools/ as the current working directory.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    memory_dir = os.path.dirname(script_dir)

    candidates.extend([
        os.path.join(memory_dir, filename),
        os.path.join(memory_dir, os.path.basename(filename)),
    ])

    seen = set()
    for path in candidates:
        normalized = os.path.abspath(path)
        if normalized in seen:
            continue
        seen.add(normalized)

        if os.path.exists(path):
            return path

    return None


def load_data(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as e:
        return None, str(e)


def extract_items(data):
    if isinstance(data, list):
        return data, None

    if isinstance(data, dict):
        for key in ["hypotheses", "data", "items"]:
            if key in data and isinstance(data[key], list):
                return data[key], None

    return None, "Root JSON must be a list or contain a list under 'hypotheses'."


def validate_history(item, idx):
    errors = []
    warnings = []
    revisions = []

    history = item.get("history")

    if history is None:
        warnings.append(
            f"Item {item.get('id', idx)} has no history; "
            "model revision cannot be evaluated."
        )
        return errors, warnings, revisions

    if not isinstance(history, list):
        errors.append(
            f"Item {item.get('id', idx)} history must be a list."
        )
        return errors, warnings, revisions

    for hidx, entry in enumerate(history):
        if not isinstance(entry, dict):
            errors.append(
                f"Item {item.get('id', idx)} history entry {hidx} "
                "is not an object."
            )
            continue

        missing = [
            field for field in HISTORY_REQUIRED_FIELDS
            if field not in entry
        ]

        if missing:
            errors.append(
                f"Item {item.get('id', idx)} history entry {hidx} "
                f"missing fields: {missing}"
            )

        status = entry.get("status")
        if status and status not in STATUS_VALUES:
            warnings.append(
                f"Item {item.get('id', idx)} history entry {hidx} "
                f"uses unrecognized status '{status}'."
            )

        evidence = str(entry.get("evidence", "")).strip()
        conclusion = str(entry.get("conclusion", "")).strip()

        if evidence and conclusion:
            revisions.append({
                "date": entry.get("date", ""),
                "status": status,
                "evidence_present": True,
                "conclusion_present": True,
                "conclusion": conclusion,
            })

    return errors, warnings, revisions


def validate():
    target = sys.argv[1] if len(sys.argv) > 1 else "hypotheses.json"
    filepath = find_file(target)

    if not filepath:
        print(json.dumps({
            "valid": False,
            "structurally_valid": False,
            "error": f"File not found: {target}",
        }, indent=2))
        return 1

    data, parse_error = load_data(filepath)

    if parse_error:
        print(json.dumps({
            "valid": False,
            "structurally_valid": False,
            "error": f"JSON parse error: {parse_error}",
        }, indent=2))
        return 1

    items, extraction_error = extract_items(data)

    if extraction_error:
        print(json.dumps({
            "valid": False,
            "structurally_valid": False,
            "error": extraction_error,
        }, indent=2))
        return 1

    errors = []
    warnings = []
    evidence_summary = {
        "hypotheses_with_history": 0,
        "hypotheses_with_evidence": 0,
        "hypotheses_with_revision_evidence": 0,
        "confirmed": 0,
        "refuted": 0,
        "inconclusive": 0,
        "untested": 0,
    }

    required_fields = [
        "id",
        "prediction",
        "test_method",
        "status",
    ]

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"Item {idx} is not an object.")
            continue

        item_id = item.get("id", idx)

        missing = [
            field for field in required_fields
            if field not in item
        ]

        if missing:
            errors.append(
                f"Item {item_id} missing fields: {missing}"
            )

        status = item.get("status")

        if status not in STATUS_VALUES:
            errors.append(
                f"Item {item_id} has invalid status: {status!r}"
            )
        else:
            evidence_summary[status] += 1

        history_errors, history_warnings, revisions = validate_history(
            item,
            idx,
        )

        errors.extend(history_errors)
        warnings.extend(history_warnings)

        history = item.get("history")

        if isinstance(history, list) and history:
            evidence_summary["hypotheses_with_history"] += 1

            has_evidence = any(
                isinstance(entry, dict)
                and str(entry.get("evidence", "")).strip()
                for entry in history
            )

            if has_evidence:
                evidence_summary["hypotheses_with_evidence"] += 1

            # A revision is stronger than merely having evidence.
            # For now we identify a revision candidate conservatively:
            # a history entry contains evidence and a conclusion.
            if revisions:
                evidence_summary["hypotheses_with_revision_evidence"] += 1

        prediction = str(item.get("prediction", "")).strip()
        test_method = str(item.get("test_method", "")).strip()

        if not prediction:
            warnings.append(
                f"Item {item_id} has an empty prediction."
            )

        if not test_method:
            warnings.append(
                f"Item {item_id} has an empty test_method."
            )

    structurally_valid = len(errors) == 0

    result = {
        "valid": structurally_valid,
        "structurally_valid": structurally_valid,
        "epistemic_status": (
            "STRUCTURALLY_COMPLETE"
            if structurally_valid
            else "STRUCTURALLY_INVALID"
        ),
        "path_used": filepath,
        "count": len(items),
        "errors": errors,
        "warnings": warnings,
        "evidence_summary": evidence_summary,
        "interpretation": (
            "Structural validation does not establish that any "
            "hypothesis is true. Evidence and model revision must be "
            "evaluated separately."
        ),
    }

    print(json.dumps(result, indent=2))

    return 0 if structurally_valid else 1


if __name__ == "__main__":
    sys.exit(validate())