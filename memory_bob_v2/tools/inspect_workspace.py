import os
import sys

def inspect():
    cwd = os.getcwd()
    print(f"Current Working Directory: {cwd}")
    print("Listing top-level directory contents:")
    try:
        entries = sorted(os.listdir(cwd))
        for entry in entries:
            path = os.path.join(cwd, entry)
            is_dir = os.path.isdir(path)
            print(f"  {'[DIR] ' if is_dir else '[FILE]'} {entry}")
            if is_dir and entry in ['memory', 'tools']:
                sub_entries = sorted(os.listdir(path))
                for sub in sub_entries:
                    print(f"    - {entry}/{sub}")
    except Exception as e:
        print(f"Error inspecting directory: {e}")

if __name__ == "__main__":
    inspect()
