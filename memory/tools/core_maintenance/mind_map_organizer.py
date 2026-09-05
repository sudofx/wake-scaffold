import os
import shutil
import json
import sys

CATEGORIES = {
    "core_functions": ["validate_memory.py", "hypothesis_validator.py"],
    "core_thinking": ["cognitive_memory_engine.py"],
    "core_evaluators": ["concept_evaluator.py", "quantum_batch_evaluator.py"],
    "core_maintenance": ["mind_map_organizer.py"]
}

def organize():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    summary = {"directories_created": [], "files_categorized": {}, "mind_map": {}}

    for cat, files in CATEGORIES.items():
        cat_dir = os.path.join(base_dir, cat)
        if not os.path.exists(cat_dir):
            os.makedirs(cat_dir, exist_ok=True)
            summary["directories_created"].append(cat)
        
        summary["files_categorized"][cat] = []
        for filename in files:
            src = os.path.join(base_dir, filename)
            if os.path.exists(src):
                dst = os.path.join(cat_dir, filename)
                shutil.copy2(src, dst)
                summary["files_categorized"][cat].append(filename)
                summary["mind_map"][filename] = {
                    "category": cat,
                    "rel_path": os.path.join(cat, filename)
                }

    manifest_path = os.path.join(base_dir, "mind_map.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(summary["mind_map"], f, indent=2)

    return {"status": "success", "summary": summary}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "organize"
    if cmd == "organize":
        res = organize()
        print(json.dumps(res))
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))
