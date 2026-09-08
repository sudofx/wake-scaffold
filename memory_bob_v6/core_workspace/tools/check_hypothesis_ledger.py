import json
import os
from pathlib import Path

def check_ledger():
    repo_root = Path(__file__).resolve().parents[3]
    ledger_paths = [
        repo_root / 'base_memory/core_memories/hypotheses.json',
        repo_root / 'memory/core_memories/hypotheses.json'
    ]
    
    found_files = []
    total_hypotheses = 0
    errors = []
    
    for path in ledger_paths:
        if path.exists():
            found_files.append(str(path.relative_to(repo_root)))
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    total_hypotheses += len(data.get('hypotheses', []))
            except Exception as e:
                errors.append(f"Error reading {path}: {str(e)}")
    
    if not found_files:
        return {"status": "STRUCTURALLY_INVALID", "error": "No ledger found"}
    
    return {
        "status": "STRUCTURALLY_COMPLETE",
        "files_checked": found_files,
        "total_hypotheses": total_hypotheses,
        "errors": errors
    }

if __name__ == '__main__':
    print(json.dumps(check_ledger(), indent=2))