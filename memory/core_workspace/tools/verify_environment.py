import os
import sys
import json

def verify():
    targets = ['identity.md', 'rules.md', 'index.md']
    checks = {}
    all_present = True
    for t in targets:
        exists = os.path.isfile(t)
        size = os.path.getsize(t) if exists else 0
        checks[t] = {'exists': exists, 'size_bytes': size}
        if not (exists and size > 0):
            all_present = False
    return {
        'status': 'STRUCTURALLY_COMPLETE' if all_present else 'STRUCTURALLY_INVALID',
        'checks': checks,
        'working_directory': os.getcwd()
    }

if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
