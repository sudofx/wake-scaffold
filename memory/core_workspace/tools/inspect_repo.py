import os
from pathlib import Path
import json

def inspect():
    # Start from current file and go up to find repo root
    current = Path(__file__).resolve()
    root = None
    for parent in [current] + list(current.parents):
        if (parent / 'memory').exists():
            root = parent
            break
    
    if not root:
        root = Path.cwd()

    results = {
        'root': str(root),
        'cwd': os.getcwd(),
        'root_files': os.listdir(root) if root.exists() else [],
        'github_workflows': []
    }
    
    workflow_dir = root / '.github' / 'workflows'
    if workflow_dir.exists():
        results['github_workflows'] = os.listdir(workflow_dir)
        
    # Let's also search for any .sh, .py, or .json files at the root level
    results['root_scripts'] = [f for f in results['root_files'] if f.endswith(('.sh', '.py', '.json', '.yml', '.yaml'))]

    print(json.dumps(results, indent=2))

if __name__ == '__main__':
    inspect()