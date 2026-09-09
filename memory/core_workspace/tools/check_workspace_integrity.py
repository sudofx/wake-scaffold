#!/usr/bin/env python3
import os
import sys
import json

def main():
    cwd = os.getcwd()
    print(f"CWD: {cwd}")
    curr = cwd
    manifest_path = None
    memory_root = None
    for _ in range(5):
        candidate = os.path.join(curr, "core_manifest.json")
        if os.path.exists(candidate):
            manifest_path = candidate
            memory_root = curr
            break
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent
    if not manifest_path or not memory_root:
        print("ERROR: core_manifest.json not found in parent tree.")
        print("RESULT: STRUCTURALLY_INVALID")
        sys.exit(1)
    print(f"Found memory root at: {memory_root}")
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
        print("core_manifest.json: VALID JSON")
    except Exception as e:
        print(f"core_manifest.json: INVALID JSON ({e})")
        print("RESULT: STRUCTURALLY_INVALID")
        sys.exit(1)
    required_dirs = [
        os.path.join(memory_root, "core_memories"),
        os.path.join(memory_root, "core_workspace"),
        os.path.join(memory_root, "core_workspace", "journal"),
        os.path.join(memory_root, "core_workspace", "tools"),
        os.path.join(memory_root, "core_workspace", "prompts"),
    ]
    required_jsons = [
        os.path.join(memory_root, "core_workspace", "tool_runs.json")
    ]
    missing_dirs = [d for d in required_dirs if not os.path.isdir(d)]
    invalid_jsons = []
    for j in required_jsons:
        if not os.path.isfile(j):
            invalid_jsons.append(f"{j} (missing)")
        else:
            try:
                with open(j, 'r', encoding='utf-8') as f:
                    json.load(f)
            except Exception as e:
                invalid_jsons.append(f"{j} (bad json: {e})")
    print(f"Required DIRS checked: {len(required_dirs)}, Missing: {len(missing_dirs)}")
    print(f"Required JSONs checked: {len(required_jsons)}, Invalid: {len(invalid_jsons)}")
    if missing_dirs or invalid_jsons:
        if missing_dirs:
            print(f"Missing dirs: {missing_dirs}")
        if invalid_jsons:
            print(f"Invalid JSONs: {invalid_jsons}")
        print("RESULT: STRUCTURALLY_INVALID")
        sys.exit(1)
    print("STATUS: STRUCTURALLY_COMPLETE")
    print("RESULT: STRUCTURALLY_COMPLETE")
    sys.exit(0)

if __name__ == '__main__':
    main()
