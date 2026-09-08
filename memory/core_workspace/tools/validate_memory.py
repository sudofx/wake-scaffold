import os
import json

def check_files():
    required = ['identity.md', 'rules.md', 'index.md']
    results = {f: os.path.exists(os.path.join('memory', f)) for f in required}
    print(json.dumps(results, indent=2))

if __name__ == '__main__':
    check_files()