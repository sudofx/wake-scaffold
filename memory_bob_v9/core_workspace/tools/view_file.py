import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: python view_file.py <relative_path>")
        sys.exit(1)
    
    rel_path = sys.argv[1]
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    memory_root = os.path.abspath(os.path.join(tools_dir, "..", ".."))
    target_path = os.path.abspath(os.path.join(memory_root, rel_path))
    
    if not target_path.startswith(memory_root):
        print("Error: Access denied (path outside memory root)")
        sys.exit(1)
        
    if not os.path.exists(target_path):
        print(f"Error: File not found at {target_path}")
        sys.exit(1)
        
    if os.path.isdir(target_path):
        print(f"Error: {target_path} is a directory")
        sys.exit(1)
        
    try:
        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"=== FILE: {rel_path} ===")
        print(content)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()