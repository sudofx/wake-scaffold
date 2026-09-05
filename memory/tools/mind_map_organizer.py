import os
import sys
import json
import shutil

CATEGORIES = {
    "core_functions": ["validate_memory.py", "hypothesis_validator.py"],
    "core_thinking": ["cognitive_memory_engine.py"],
    "core_evaluators": ["concept_evaluator.py", "quantum_batch_evaluator.py"],
    "core_maintenance": ["mind_map_organizer.py"]
}

MANIFEST_FILE = "mind_map.json"

def organize():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    summary = {"directories_created": [], "files_categorized": {}}
    
    for cat, files in CATEGORIES.items():
        cat_path = os.path.join(base_dir, cat)
        if not os.path.exists(cat_path):
            os.makedirs(cat_path, exist_ok=True)
            summary["directories_created"].append(cat)
        
        summary["files_categorized"][cat] = []
        for filename in files:
            src = os.path.join(base_dir, filename)
            dest = os.path.join(cat_path, filename)
            if os.path.exists(src):
                shutil.copy2(src, dest)
                summary["files_categorized"][cat].append(filename)
            elif os.path.exists(dest):
                summary["files_categorized"][cat].append(filename)

    manifest_path = os.path.join(base_dir, MANIFEST_FILE)
    with open(manifest_path, "w") as f:
        json.dump(summary, f, indent=2)

    return {"status": "success", "summary": summary}

def status():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    manifest_path = os.path.join(base_dir, MANIFEST_FILE)
    
    if os.path.exists(manifest_path):
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        return {"status": "success", "manifest_found": True, "manifest": manifest}
    else:
        return {"status": "success", "manifest_found": False, "message": "Manifest not found. Run organize first."}

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "organize":
        res = organize()
    elif cmd == "status":
        res = status()
    else:
        res = {"error": f"Unknown command: {cmd}"}
    print(json.dumps(res))

if __name__ == "__main__":
    main()
