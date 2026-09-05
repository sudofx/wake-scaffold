import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Error: No target path provided.")
        print("Usage: python workspace_explorer.py <file_or_directory_path>")
        sys.exit(1)

    target = sys.argv[1]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)

    # Try resolving relative to script dir, parent repo root, or as direct path
    paths_to_try = [
        os.path.join(script_dir, target),
        os.path.join(parent_dir, target),
        target
    ]

    found = False
    for path in paths_to_try:
        if os.path.exists(path):
            normalized_path = os.path.abspath(path)
            if os.path.isdir(normalized_path):
                print(f"Listing directory: {normalized_path}")
                try:
                    items = sorted(os.listdir(normalized_path))
                    for item in items:
                        item_path = os.path.join(normalized_path, item)
                        is_dir = "dir" if os.path.isdir(item_path) else "file"
                        size = os.path.getsize(item_path) if is_dir == "file" else ""
                        print(f"  {is_dir:<5} {item:<30} {size}")
                    found = True
                    break
                except Exception as e:
                    print(f"Error listing directory {normalized_path}: {e}")
                    found = True
                    break
            elif os.path.isfile(normalized_path):
                print(f"Reading file: {normalized_path}")
                try:
                    with open(normalized_path, 'r', encoding='utf-8') as f:
                        # Stay within tool-run stdout truncation limits (4000 chars)
                        print(f.read()[:3800])
                    found = True
                    break
                except Exception as e:
                    print(f"Error reading file {normalized_path}: {e}")
                    found = True
                    break

    if not found:
        print(f"Path not found: {target}")
        print(f"Tried locations: {[os.path.abspath(p) for p in paths_to_try]}")
        sys.exit(1)

if __name__ == '__main__':
    main()