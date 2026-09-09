import os
import json

def main():
    print("--- Starting Layout Inspection ---")
    cwd = os.getcwd()
    print(f"Current Working Directory: {cwd}")
    
    # Try to find core_manifest.json by walking up
    manifest_path = None
    current = cwd
    for _ in range(5):
        candidate = os.path.join(current, 'core_manifest.json')
        if os.path.exists(candidate):
            manifest_path = candidate
            break
        # Also check in parent memory/ folder if it exists
        candidate_memory = os.path.join(current, 'memory', 'core_manifest.json')
        if os.path.exists(candidate_memory):
            manifest_path = candidate_memory
            break
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
        
    if not manifest_path:
        print("ERROR: Could not find core_manifest.json in current or parent directories.")
        # List files in current directory to help debug
        print(f"CWD Contents: {os.listdir('.')}")
        return
        
    print(f"Found core_manifest.json at: {manifest_path}")
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        print("Manifest Contents:")
        print(json.dumps(manifest, indent=2))
        
        # Resolve paths relative to manifest directory
        manifest_dir = os.path.dirname(manifest_path)
        print(f"Manifest Directory: {manifest_dir}")
        
        for key, relative_path in manifest.items():
            target_path = os.path.abspath(os.path.join(manifest_dir, relative_path))
            exists = os.path.exists(target_path)
            print(f"- Key '{key}' -> Path: {relative_path} (Resolved: {target_path}) | Exists: {exists}")
            if exists and os.path.isdir(target_path):
                print(f"  Contents of {relative_path}: {os.listdir(target_path)}")
            elif exists:
                # If it's a file, print a short preview if it's JSON/text
                if target_path.endswith('.json'):
                    try:
                        with open(target_path, 'r') as tf:
                            content = json.load(tf)
                        print(f"  JSON Keys: {list(content.keys()) if isinstance(content, dict) else 'list'}")
                    except Exception as e:
                        print(f"  Failed to parse JSON: {e}")
    except Exception as e:
        print(f"ERROR reading or processing manifest: {e}")

if __name__ == '__main__':
    main()
