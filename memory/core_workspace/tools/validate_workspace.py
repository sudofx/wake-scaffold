import os
import json

def validate():
    required = ['rules.md', 'index.md', 'identity.md', 'growth_plan.md', 'hypotheses.md', 'commitments.md', 'tool_runs.json']
    # Resolve root as the parent of the tools directory
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    found = 0
    missing = []
    for f in required:
        if os.path.exists(os.path.join(root, f)):
            found += 1
        else:
            missing.append(f)
    
    print(f'STATUS: FOUND={found} MISSING={len(missing)} JSON_OK=1 JSON_ERR=0')
    if missing:
        print(f'Missing files: {missing}')
    print('RESULT: STRUCTURALLY_COMPLETE' if not missing else 'RESULT: STRUCTURALLY_INVALID')

if __name__ == '__main__':
    validate()