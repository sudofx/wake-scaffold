import os
import json

def validate():
    cwd = os.getcwd()
    # Simple walk up to find a marker that identifies the root
    root = cwd
    while root != os.path.dirname(root):
        if 'memory' in os.listdir(root):
            break
        root = os.path.dirname(root)
    
    expected = ['memory', 'memory/core_workspace', 'memory/core_workspace/tools', 'memory/core_workspace/journal']
    results = {}
    for path in expected:
        results[path] = os.path.exists(os.path.join(root, path))

    print(json.dumps({
        "status": "DETAILED_REPORT",
        "discovered_root": root,
        "directory_check": results
    }, indent=2))

if __name__ == '__main__':
    validate()