import sys
import json
import os

def find_memory_dir():
    if len(sys.argv) > 1:
        return sys.argv[1]
    if os.path.exists("growth_plan.json"):
        return "."
    if os.path.exists("../growth_plan.json"):
        return ".."
    return "."

def validate():
    mem_dir = find_memory_dir()
    print(f"Validating memory directory: {os.path.abspath(mem_dir)}")
    errors = []
    warnings = []

    json_schemas = {
        "growth_plan.json": {
            "root_key": "projects",
            "required_item_keys": ["id", "title", "capability", "status", "next_step"],
            "allowed_statuses": ["proposed", "active", "blocked", "complete"]
        },
        "commitments.json": {
            "root_key": "commitments",
            "required_item_keys": ["id", "to", "what", "due", "status"],
            "allowed_statuses": ["open", "in_progress", "blocked", "closed"]
        },
        "hypotheses.json": {
            "root_key": "hypotheses",
            "required_item_keys": ["id", "prediction", "test_method", "status"],
            "allowed_statuses": ["testing", "confirmed", "refuted", "inconclusive"]
        },
        "core_memories.json": {
            "root_key": "memories",
            "required_item_keys": ["id", "lesson", "weight"],
            "allowed_statuses": None
        }
    }

    for filename, schema in json_schemas.items():
        filepath = os.path.join(mem_dir, filename)
        if not os.path.exists(filepath):
            errors.append(f"Missing file: {filename}")
            continue

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            errors.append(f"Invalid JSON in {filename}: {str(e)}")
            continue

        root_key = schema["root_key"]
        if not isinstance(data, dict) or root_key not in data or not isinstance(data[root_key], list):
            errors.append(f"{filename}: expected root object with key '{root_key}' containing a list.")
            continue

        items = data[root_key]
        seen_ids = set()
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"{filename}[{idx}]: item is not a JSON object.")
                continue

            item_id = item.get("id")
            if not item_id:
                errors.append(f"{filename}[{idx}]: missing required 'id'.")
            elif item_id in seen_ids:
                errors.append(f"{filename}: duplicate id '{item_id}'.")
            else:
                seen_ids.add(item_id)

            for req_key in schema["required_item_keys"]:
                if req_key not in item or item.get(req_key) is None or item.get(req_key) == "":
                    errors.append(f"{filename} item '{item_id or idx}': missing or empty required field '{req_key}'.")

            allowed = schema["allowed_statuses"]
            if allowed and "status" in item and item["status"] not in allowed:
                errors.append(f"{filename} item '{item_id or idx}': invalid status '{item['status']}'. Must be one of {allowed}.")

        print(f"[OK] {filename}: {len(items)} items validated.")

    for md_file in ["rules.md", "index.md", "identity.md"]:
        filepath = os.path.join(mem_dir, md_file)
        if not os.path.exists(filepath):
            errors.append(f"Missing required markdown file: {md_file}")
        else:
            print(f"[OK] {md_file} exists.")

    print("\n--- Summary ---")
    if warnings:
        for w in warnings:
            print(f"WARNING: {w}")
    if errors:
        print(f"FAILED with {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("ALL MEMORY INTEGRITY CHECKS PASSED.")
        sys.exit(0)

if __name__ == "__main__":
    validate()
