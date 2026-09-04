import sys
from pathlib import Path
import json

def validate():
    # Resolve root relative to this script's location (tools/)
    script_dir = Path(__file__).resolve().parent
    workspace_root = script_dir.parent
    memory_dir = workspace_root / 'memory'
    
    print(json.dumps({
        "workspace_root": str(workspace_root),
        "memory_dir": str(memory_dir),
        "exists": memory_dir.exists()
    }, indent=2))
    
    if not memory_dir.exists():
        sys.exit(1)
    sys.exit(0)

if __name__ == '__main__':
    validate()