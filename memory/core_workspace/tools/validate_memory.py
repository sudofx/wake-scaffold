import os
import json

def validate():
    required = ['identity.md', 'rules.md', 'index.md', 'commitments.json']
    found = []
    for f in required:
        if os.path.exists(f'memory/{f}'):
            found.append(f)
    
    return {'status': 'STRUCTURALLY_COMPLETE' if len(found) == len(required) else 'STRUCTURALLY_INVALID', 'files_found': found}

if __name__ == '__main__':
    print(json.dumps(validate()))