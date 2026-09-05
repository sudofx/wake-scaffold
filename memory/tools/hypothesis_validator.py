import sys
import json
import os

def validate_hypotheses(filepath):
    if not os.path.exists(filepath):
        return {"valid": False, "error": f"File not found: {filepath}"}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"valid": False, "error": f"JSON parse error: {str(e)}"}
    if not isinstance(data, list):
        return {"valid": False, "error": "Root structure must be a JSON array"}
    errors = []
    valid_statuses = {"untested", "testing", "confirmed", "refuted", "inconclusive"}
    for idx, item in enumerate(data):
        h_id = item.get("id", f"index-{idx}")
        status = item.get("status")
        if status not in valid_statuses:
            errors.append(f"{h_id}: Invalid status '{status}'")
        if not item.get("prediction"):
            errors.append(f"{h_id}: Missing 'prediction'")
        if not item.get("test_method"):
            errors.append(f"{h_id}: Missing 'test_method'")
        if status in {"confirmed", "refuted", "inconclusive"}:
            if not item.get("evidence") or not item.get("evidence").strip():
                errors.append(f"{h_id}: Status '{status}' requires non-empty 'evidence'")
            if not item.get("conclusion") or not item.get("conclusion").strip():
                errors.append(f"{h_id}: Status '{status}' requires non-empty 'conclusion'")
    return {
        "valid": len(errors) == 0,
        "total_hypotheses": len(data),
        "errors": errors
    }

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "../memory/hypotheses.json"
    if not os.path.exists(path) and os.path.exists("memory/hypotheses.json"):
        path = "memory/hypotheses.json"
    result = validate_hypotheses(path)
    print(json.dumps(result, indent=2))
