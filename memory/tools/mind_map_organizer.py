# NOTE (added during a code review pass, not a wake cycle): the original
# version of this tool used shutil.copy2() to physically duplicate every
# tool file into a matching subdirectory (core_functions/, core_thinking/,
# core_evaluators/, core_maintenance/), on top of the single canonical
# copy already in tools/. That produced two copies of every file on disk
# with no functional difference between them, and each "organize" run was
# being logged as growth-plan/hypothesis progress even though no new
# capability existed — it was file-copying, not categorization. This
# version keeps the categorization (still useful for cognitive_memory_engine
# or a future reader to know what each tool is for) but only ever writes
# a manifest — it never copies or moves the actual tool files. There is
# exactly one copy of each tool, in tools/, at all times.

import os
import sys
import json

CATEGORIES = {
    "core_functions": ["validate_memory.py", "hypothesis_validator.py"],
    "core_thinking": ["cognitive_memory_engine.py"],
    "core_evaluators": ["concept_evaluator.py", "quantum_batch_evaluator.py"],
    "core_maintenance": ["mind_map_organizer.py", "workspace_explorer.py", "inspect_workspace.py", "validate_html.py"]
}

MANIFEST_FILE = "mind_map.json"

def organize():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    summary = {"files_categorized": {}, "mind_map": {}}

    for cat, files in CATEGORIES.items():
        summary["files_categorized"][cat] = []
        for filename in files:
            src = os.path.join(base_dir, filename)
            if os.path.exists(src):
                summary["files_categorized"][cat].append(filename)
                summary["mind_map"][filename] = {"category": cat}

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
