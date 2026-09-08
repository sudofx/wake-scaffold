import os
import json

def main():
    start_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    print(f"Scanning from: {start_dir}")
    
    structure = {}
    for root, dirs, files in os.walk(start_dir):
        # Skip hidden directories like .git
        if '.git' in root or '.github' in root:
            continue
        
        rel_root = os.path.relpath(root, start_dir)
        structure[rel_root] = []
        for f in files:
            full_path = os.path.join(root, f)
            size = os.path.getsize(full_path)
            structure[rel_root].append({
                "file": f,
                "size_bytes": size
            })
            
    print(json.dumps(structure, indent=2))

if __name__ == '__main__':
    main()
