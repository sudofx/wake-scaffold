import json
import os
import sys

def check_file_exists(filepath):
    if not os.path.isfile(filepath):
        return False, f"File missing: {filepath}"
    return True, f"File exists: {filepath}"

def check_json_valid(filepath):
    exists, msg = check_file_exists(filepath)
    if not exists:
        return False, msg
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return True, f"Valid JSON: {filepath} ({type(data).__name__})"
    except Exception as e:
        return False, f"Invalid JSON in {filepath}: {e}"

def check_html_valid(filepath):
    exists, msg = check_file_exists(filepath)
    if not exists:
        return False, msg
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if len(content.strip()) == 0:
            return False, f"Empty HTML file: {filepath}"
        return True, f"Valid non-empty HTML: {filepath} ({len(content)} bytes)"
    except Exception as e:
        return False, f"Error reading HTML {filepath}: {e}"

def validate_memory_dir(target_dir):
    errors = []
    successes = []

    json_files = ['growth_plan.json', 'commitments.json', 'hypotheses.json']
    for jf in json_files:
        path = os.path.join(target_dir, jf)
        ok, msg = check_json_valid(path)
        if ok:
            successes.append(msg)
        else:
            errors.append(msg)

    html_files = ['blog.html']
    for hf in html_files:
        path = os.path.join(target_dir, hf)
        ok, msg = check_html_valid(path)
        if ok:
            successes.append(msg)
        else:
            errors.append(msg)

    md_files = ['rules.md', 'index.md', 'identity.md']
    for mf in md_files:
        path = os.path.join(target_dir, mf)
        ok, msg = check_file_exists(path)
        if ok:
            successes.append(msg)
        else:
            errors.append(msg)

    return successes, errors

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'memory'
    print(f"Validating directory: {target}")
    successes, errors = validate_memory_dir(target)
    for s in successes:
        print(f"[OK] {s}")
    for e in errors:
        print(f"[FAIL] {e}")
    if errors:
        sys.exit(1)
    else:
        print("Validation passed cleanly.")
        sys.exit(0)
