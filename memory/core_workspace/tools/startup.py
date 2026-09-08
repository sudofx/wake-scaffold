import os
import json

def check():
    required = ['memory', 'core_workspace']
    missing = [d for d in required if not os.path.exists(d)]
    if not missing:
        print(json.dumps({'status': 'STRUCTURALLY_COMPLETE'}))
    else:
        print(json.dumps({'status': 'STRUCTURALLY_INVALID', 'missing': missing}))

if __name__ == '__main__':
    check()