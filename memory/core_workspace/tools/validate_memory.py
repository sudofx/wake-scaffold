import os
import sys
import json

def find_memory_root():
    candidates = [os.getcwd(), os.path.dirname(os.path.abspath(__file__))]
    for start in candidates:
        curr = start
        for _ in range(5):
            if os.path.exists(os.path.join(curr, 'identity.md')) or os.path.exists(os.path.join(curr, 'rules.md')):
                return curr
            if os.path.exists(os.path.join(curr, 'memory', 'identity.md')):
                return os.path.join(curr, 'memory')
            parent = os.path.dirname(curr)
            if parent == curr:
                break
            curr = parent
    return os.getcwd()

def validate_workspace(root_path):
    required_files = ['identity.md', 'rules.md', 'index.md']
    json_files = ['commitments.json', 'tool_runs.json']
    results = {'root_path': root_path, 'checks': {}, 'status': 'STRUCTURALLY_COMPLETE'}
    for fname in required_files:
        fpath = os.path.join(root_path, fname)
        exists = os.path.exists(fpath)
        size = os.path.getsize(fpath) if exists else 0
        results['checks'][fname] = {'exists': exists, 'size_bytes': size}
        if not exists or size == 0:
            results['status'] = 'STRUCTURALLY_INVALID'
    for fname in json_files:
        fpath = os.path.join(root_path, fname)
        exists = os.path.exists(fpath)
        valid_json = False
        if exists:
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    json.load(f)
                valid_json = True
            except Exception:
                valid_json = False
        results['checks'][fname] = {'exists': exists, 'valid_json': valid_json}
        if not exists or not valid_json:
            results['status'] = 'STRUCTURALLY_INVALID'
    return results

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else find_memory_root()
    report = validate_workspace(target)
    print(json.dumps(report, indent=2))
