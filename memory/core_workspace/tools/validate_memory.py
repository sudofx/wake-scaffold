import os
import json
import sys

def find_manifest(start_dir):
    curr = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(curr, "core_manifest.json")
        if os.path.exists(candidate):
            return candidate, curr
        parent = os.path.dirname(curr)
        if parent == curr:
            return None, None
        curr = parent

def main():
    print("=== MEMORY VALIDATOR ===")
    current_dir = os.getcwd()
    print(f"Starting search from CWD: {current_dir}")
    
    manifest_path, memory_root = find_manifest(current_dir)
    if not manifest_path:
        print("ERROR: core_manifest.json not found in hierarchy.")
        sys.exit(1)
        
    print(f"Found manifest at: {manifest_path}")
    print(f"Memory root directory: {memory_root}")
    
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        print(f"ERROR reading manifest: {e}")
        sys.exit(1)
        
    layout = manifest.get("layout", {})
    if not layout:
        print("ERROR: No 'layout' key in manifest.")
        sys.exit(1)
        
    missing = []
    found = []
    
    for key, rel_path in layout.items():
        full_path = os.path.join(memory_root, rel_path)
        if os.path.exists(full_path):
            found.append(f"{key}: {rel_path}")
        else:
            missing.append(f"{key}: {rel_path}")
            
    print("\nChecked layout paths:")
    for item in found:
        print(f" [EXISTS] {item}")
    for item in missing:
        print(f" [MISSING] {item}")
        
    if missing:
        print(f"\nSTATUS: STRUCTURALLY_INVALID - Missing {len(missing)} declared paths.")
        sys.exit(1)
    else:
        print(f"\nSTATUS: STRUCTURALLY_COMPLETE - All {len(found)} declared layout paths verified.")
        sys.exit(0)

if __name__ == "__main__":
    main()
