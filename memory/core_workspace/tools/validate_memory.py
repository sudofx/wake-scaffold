import os
import json
import sys

def main():
    print("=== MEMORY VALIDATOR ===")
    current_dir = os.getcwd()
    print(f"Starting search from CWD: {current_dir}")
    
    manifest_path = None
    temp_dir = current_dir
    while True:
        possible_manifest = os.path.join(temp_dir, "core_manifest.json")
        if os.path.exists(possible_manifest):
            manifest_path = possible_manifest
            break
        parent = os.path.dirname(temp_dir)
        if parent == temp_dir:
            break
        temp_dir = parent
        
    if not manifest_path:
        possible_paths = [
            "core_manifest.json",
            "../core_manifest.json",
            "../../core_manifest.json",
            "../../../core_manifest.json"
        ]
        for p in possible_paths:
            if os.path.exists(p):
                manifest_path = os.path.abspath(p)
                break

    if not manifest_path:
        print("Error: core_manifest.json not found!")
        sys.exit(1)
        
    print(f"Found manifest at: {manifest_path}")
    memory_root = os.path.dirname(manifest_path)
    print(f"Memory root directory: {memory_root}")
    
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
    except Exception as e:
        print(f"Error reading/parsing core_manifest.json: {e}")
        sys.exit(1)
        
    print("Successfully parsed core_manifest.json.")
    print("Manifest contents:")
    print(json.dumps(manifest, indent=2))
    
    print("\n--- Directory Listing of Memory Root ---")
    try:
        for item in sorted(os.listdir(memory_root)):
            item_path = os.path.join(memory_root, item)
            is_dir = os.path.isdir(item_path)
            print(f" {'[DIR] ' if is_dir else '[FILE]'} {item}")
    except Exception as e:
        print(f"Error listing memory root: {e}")
        sys.exit(1)
        
    expected_dirs = ["core_workspace", "core_identity", "core_memories"]
    all_exist = True
    print("\n--- Core Directory Verification ---")
    for d in expected_dirs:
        path = os.path.join(memory_root, d)
        exists = os.path.exists(path) and os.path.isdir(path)
        print(f"Directory '{d}': {'EXISTS' if exists else 'MISSING'}")
        if not exists:
            all_exist = False
            
    if all_exist:
        print("\nSTATUS: STRUCTURALLY_COMPLETE")
    else:
        print("\nSTATUS: STRUCTURALLY_INVALID")
        sys.exit(1)

if __name__ == '__main__':
    main()