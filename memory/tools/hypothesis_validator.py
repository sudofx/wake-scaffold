import json
import os
import sys

def find_file(filename):
    candidates = [
        filename,
        os.path.join("memory", filename),
        os.path.join("..", "memory", filename),
        os.path.join("..", filename)
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

def validate():
    target = sys.argv[1] if len(sys.argv) > 1 else "hypotheses.json"
    filepath = find_file(target)
    if not filepath:
        print(json.dumps({"valid": False, "error": f"File not found: {target}" if not filepath else ""}))
        return

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(json.dumps({"valid": False, "error": f"JSON parse error: {str(e)}"}))
        return

    items = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for key in ["hypotheses", "data", "items"]:
            if key in data and isinstance(data[key], list):
                items = data[key]
                break

    if not items and not isinstance(data, list):
        print(json.dumps({"valid": False, "error": "Root JSON must be a list or contain a list under 'hypotheses'."}))
        return

    errors = []
    required_fields = ["id", "prediction", "test_method", "status"]
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"Item {idx} is not an object.")
            continue
        missing = [f for f in required_fields if f not in item]
        if missing:
            errors.append(f"Item {item.get('id', idx)} missing fields: {missing}")

    result = {
        "valid": len(errors) == 0,
        "path_used": filepath,
        "count": len(items),
        "errors": errors
    }
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    validate()
