import json
import sys
from pathlib import Path

def find_workspace_root():
    cwd = Path.cwd()
    if (cwd / 'commitments.json').exists() or (cwd / 'rules.md').exists():
        return cwd
    if (cwd.parent / 'commitments.json').exists():
        return cwd.parent
    script_dir = Path(__file__).resolve().parent
    if (script_dir.parent / 'commitments.json').exists():
        return script_dir.parent
    return cwd

def validate_json_file(file_path):
    if not file_path.exists():
        return False, f'Missing file: {file_path.name}'
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
        return True, f'{file_path.name} is valid JSON'
    except json.JSONDecodeError as e:
        return False, f'Invalid JSON in {file_path.name}: {e}'
    except Exception as e:
        return False, f'Error reading {file_path.name}: {e}'

def validate_workspace(root_dir):
    results = []
    errors = 0
    
    json_files = ['commitments.json', 'growth_plan.json', 'hypotheses.json']
    for jf in json_files:
        target = root_dir / jf
        ok, msg = validate_json_file(target)
        if ok:
            results.append(f'[OK] {msg}')
        else:
            results.append(f'[FAIL] {msg}')
            errors += 1
            
    md_files = ['identity.md', 'rules.md']
    for mf in md_files:
        target = root_dir / mf
        if target.exists() and target.stat().st_size > 0:
            results.append(f'[OK] {mf} exists ({target.stat().st_size} bytes)')
        else:
            results.append(f'[FAIL] {mf} missing or empty')
            errors += 1
            
    dirs = ['journal', 'tools']
    for d in dirs:
        target = root_dir / d
        if target.is_dir():
            results.append(f'[OK] directory \'{d}/\' exists')
        else:
            results.append(f'[FAIL] directory \'{d}/\' missing')
            errors += 1
            
    return errors == 0, results

def main():
    root = find_workspace_root()
    print(f'Validating workspace root at: {root}')
    success, report = validate_workspace(root)
    for line in report:
        print(line)
        
    if success:
        print('\nSUMMARY: All integrity checks passed.')
        sys.exit(0)
    else:
        print('\nSUMMARY: Validation failed with errors.')
        sys.exit(1)

if __name__ == '__main__':
    main()
