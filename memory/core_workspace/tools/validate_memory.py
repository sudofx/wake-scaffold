import os
import json
import sys

def main():
    print("=== MEMORY VALIDATOR ===")
    current_dir = os.getcwd()
    print(f"Starting search from CWD: {current_dir}")

    # Find manifest
    manifest_path = None
    temp_dir = current_dir
    while True:
        candidate = os.path.join(temp_dir, "core_manifest.json")
        if os.path.exists(candidate):
            manifest_path = candidate
            break
        parent = os.path.dirname(temp_dir)
        if parent == temp_dir:
            break
        temp_dir = parent

    if not manifest_path:
        print("STATUS: STRUCTURALLY_INVALID")
        print("ERROR: core_manifest.json not found in path hierarchy.")
        sys.exit(1)

    memory_root = os.path.dirname(manifest_path)
    print(f"Found manifest at: {manifest_path}")
    print(f"Memory root directory: {memory_root}")

    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
    except Exception as e:
        print("STATUS: STRUCTURALLY_INVALID")
        print(f"ERROR: Failed to parse manifest JSON: {e}")
        sys.exit(1)

    # Validate Schema
    errors = []
    if "schema_version" not in manifest:
        errors.append("Missing 'schema_version'")
    elif manifest["schema_version"] != 1:
        errors.append(f"Unsupported schema_version: {manifest['schema_version']}")

    if "identity_name" not in manifest or not isinstance(manifest["identity_name"], str):
        errors.append("Missing or invalid 'identity_name'")

    if "layout" not in manifest or not isinstance(manifest["layout"], dict):
        errors.append("Missing or invalid 'layout' object")
    else:
        required_layout_keys = ["identity", "memories", "workspace", "synthesis", "persona", "journal", "prompts"]
        for key in required_layout_keys:
            if key not in manifest["layout"]:
                errors.append(f"Missing required layout key: '{key}'")

    if errors:
        print("STATUS: STRUCTURALLY_INVALID")
        print(f"Schema validation errors: {', '.join(errors)}")
        sys.exit(1)

    print("Manifest schema is valid.")

    # Validate Layout Paths Existence
    layout = manifest["layout"]
    missing_paths = []
    for key, relative_path in layout.items():
        full_path = os.path.join(memory_root, relative_path)
        if not os.path.exists(full_path):
            missing_paths.append(f"'{key}' path does not exist: {relative_path}")
        elif not os.path.isdir(full_path):
            missing_paths.append(f"'{key}' path is not a directory: {relative_path}")

    if missing_paths:
        print("STATUS: STRUCTURALLY_INVALID")
        print(f"Layout existence errors:\n" + "\n".join(missing_paths))
        sys.exit(1)

    print("All 7 declared layout directories exist.")

    # Deep Content Checks
    # 1. Match identity name in identity.md
    identity_dir = os.path.join(memory_root, layout["identity"])
    identity_file = os.path.join(identity_dir, "identity.md")
    expected_name = manifest["identity_name"]

    if not os.path.exists(identity_file):
        # Fallback to checking root memory folder
        identity_file = os.path.join(memory_root, "identity.md")

    if not os.path.exists(identity_file):
        print("STATUS: STRUCTURALLY_INVALID")
        print(f"ERROR: identity.md not found in identity directory ({layout['identity']}) or memory root.")
        sys.exit(1)

    try:
        with open(identity_file, "r") as f:
            identity_content = f.read()
        
        expected_string = f"**Name:** {expected_name}"
        if expected_string not in identity_content:
            if expected_name.lower() not in identity_content.lower():
                print("STATUS: STRUCTURALLY_INVALID")
                print(f"ERROR: Expected identity name '{expected_name}' not found in identity.md")
                sys.exit(1)
            else:
                print(f"Warning: Exact string '{expected_string}' not found, but '{expected_name}' found in identity.md (case-insensitive match).")
        else:
            print(f"Confirmed identity name '{expected_name}' matches identity.md")
    except Exception as e:
        print("STATUS: STRUCTURALLY_INVALID")
        print(f"ERROR: Failed to read/validate identity.md: {e}")
        sys.exit(1)

    # 2. Check journal directory completeness
    journal_dir = os.path.join(memory_root, layout["journal"])
    try:
        journal_files = [f for f in os.listdir(journal_dir) if f.endswith(".md")]
        print(f"Found {len(journal_files)} journal entries in {layout['journal']}.")
    except Exception as e:
        print("STATUS: STRUCTURALLY_INVALID")
        print(f"ERROR: Failed to read journal directory: {e}")
        sys.exit(1)

    print("STATUS: STRUCTURALLY_COMPLETE")
    print("MECHANISM_NOTES: Validated core_manifest.json schema, verified presence of all 7 layout directories, and confirmed 'identity_name' match in identity.md.")

if __name__ == "__main__":
    main()