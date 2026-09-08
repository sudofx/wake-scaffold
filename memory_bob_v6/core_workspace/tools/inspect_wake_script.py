import json
import os
from pathlib import Path

def find_repo_root():
    curr = Path.cwd().resolve()
    for p in [curr] + list(curr.parents):
        if (p / 'wake.py').exists():
            return p
    file_path = Path(__file__).resolve()
    for p in [file_path] + list(file_path.parents):
        if (p / 'wake.py').exists():
            return p
    return curr

def inspect_wake():
    root = find_repo_root()
    wake_file = root / 'wake.py'
    if not wake_file.exists():
        return {'error': 'wake.py not found', 'root': str(root)}
    
    content = wake_file.read_text(encoding='utf-8')
    lines = content.splitlines()
    
    return {
        'root': str(root),
        'total_lines': len(lines),
        'content': content if len(content) < 3500 else content[:3500] + '\n...[truncated]'
    }

if __name__ == '__main__':
    print(json.dumps(inspect_wake(), indent=2))
