import os
import sys
import json

def validate_memory(memory_dir):
    errors = []
    warnings = []
    checked = 0

    # 1. commitments.json
    commitments_path = os.path.join(memory_dir, 'commitments.json')
    if not os.path.isfile(commitments_path):
        errors.append(f"Missing file: {commitments_path}")
    else:
        try:
            with open(commitments_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            checked += 1
            if not isinstance(data, list):
                errors.append(f"{commitments_path}: expected JSON array at top level")
            else:
                valid_statuses = {'open', 'in_progress', 'blocked', 'closed'}
                for idx, item in enumerate(data):
                    if not isinstance(item, dict):
                        errors.append(f"{commitments_path}[{idx}]: expected JSON object")
                        continue
                    for field in ['id', 'description', 'status']:
                        if field not in item:
                            errors.append(f"{commitments_path}[{idx}]: missing required field '{field}'")
                    if 'status' in item and item['status'] not in valid_statuses:
                        warnings.append(f"{commitments_path}[{idx}]: unknown status '{item['status']}'")
        except Exception as e:
            errors.append(f"Failed to parse {commitments_path}: {e}")

    # 2. growth_plan.json
    growth_path = os.path.join(memory_dir, 'growth_plan.json')
    if not os.path.isfile(growth_path):
        errors.append(f"Missing file: {growth_path}")
    else:
        try:
            with open(growth_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            checked += 1
            projects = []
            if isinstance(data, dict) and 'projects' in data:
                projects = data['projects']
            elif isinstance(data, list):
                projects = data
            else:
                errors.append(f"{growth_path}: expected array or object with 'projects' key")

            valid_project_statuses = {'proposed', 'active', 'blocked', 'complete'}
            for idx, proj in enumerate(projects):
                if not isinstance(proj, dict):
                    errors.append(f"{growth_path}.projects[{idx}]: expected JSON object")
                    continue
                for field in ['id', 'title', 'capability', 'status']:
                    if field not in proj:
                        errors.append(f"{growth_path}.projects[{idx}]: missing field '{field}'")
                if 'status' in proj and proj['status'] not in valid_project_statuses:
                    warnings.append(f"{growth_path}.projects[{idx}]: unknown status '{proj['status']}'")
        except Exception as e:
            errors.append(f"Failed to parse {growth_path}: {e}")

    # 3. identity.md
    identity_path = os.path.join(memory_dir, 'identity.md')
    if not os.path.isfile(identity_path):
        errors.append(f"Missing file: {identity_path}")
    else:
        try:
            with open(identity_path, 'r', encoding='utf-8') as f:
                content = f.read()
            checked += 1
            required_substrings = ['Name:', 'Purpose:']
            for sub in required_substrings:
                if sub not in content:
                    warnings.append(f"{identity_path}: expected field/heading '{sub}' not found")
        except Exception as e:
            errors.append(f"Failed to read {identity_path}: {e}")

    # 4. rules.md & index.md
    for filename in ['rules.md', 'index.md']:
        path = os.path.join(memory_dir, filename)
        if not os.path.isfile(path):
            warnings.append(f"Missing optional/standard file: {path}")
        else:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                checked += 1
                if not content.strip():
                    warnings.append(f"{path}: file is empty")
            except Exception as e:
                errors.append(f"Failed to read {path}: {e}")

    print(f"Validated {checked} memory targets in '{memory_dir}'.")
    if warnings:
        print(f"Warnings ({len(warnings)}):")
        for w in warnings:
            print(f" - {w}")
    if errors:
        print(f"Errors ({len(errors)}):")
        for e in errors:
            print(f" - {e}")
        sys.exit(1)
    else:
        print("All memory checks passed cleanly.")

if __name__ == '__main__':
    target_dir = sys.argv[1] if len(sys.argv) > 1 else 'memory'
    validate_memory(target_dir)
