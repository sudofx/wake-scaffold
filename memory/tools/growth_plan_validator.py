import sys
import json
import os

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"valid": False, "error": "No filename provided."}))
        return

    filepath = sys.argv[1]
    paths_to_try = [filepath, os.path.join("..", filepath)]
    data = None
    path_used = None
    for p in paths_to_try:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    data = json.load(f)
                path_used = p
                break
            except Exception as e:
                print(json.dumps({"valid": False, "error": f"Failed to parse JSON in {p}: {str(e)}"}))
                return
    
    if data is None:
        print(json.dumps({"valid": False, "error": f"File not found: {filepath}"}))
        return

    if isinstance(data, dict):
        projects = None
        if "projects" in data:
            projects = data["projects"]
        else:
            # Treat dict values as projects if they look like objects
            projects = [v for v in data.values() if isinstance(v, dict)]
        
        if not isinstance(projects, list):
            print(json.dumps({
                "valid": False, 
                "error": "Could not locate a list of projects in the JSON object.",
                "root_type": "dict",
                "keys": list(data.keys())
            }))
            return
    elif isinstance(data, list):
        projects = data
    else:
        print(json.dumps({"valid": False, "error": f"Invalid JSON root type: {type(data).__name__}"}))
        return

    valid_projects = []
    invalid_projects = []
    errors = []

    for idx, proj in enumerate(projects):
        if not isinstance(proj, dict):
            errors.append(f"Project at index {idx} is not an object.")
            continue
        
        proj_id = proj.get("id") or proj.get("project_id") or f"unknown_{idx}"
        status = proj.get("status") or proj.get("new_status") or "unknown"
        
        missing = []
        for field in ["title", "capability", "next_step"]:
            if field not in proj:
                missing.append(field)
        
        if missing:
            errors.append(f"Project {proj_id} is missing fields: {', '.join(missing)}")
            invalid_projects.append(proj_id)
        else:
            valid_projects.append({
                "id": proj_id,
                "title": proj["title"],
                "status": status,
                "next_step": proj["next_step"]
            })

    is_valid = len(errors) == 0
    print(json.dumps({
        "valid": is_valid,
        "path_used": path_used,
        "total_projects": len(projects),
        "valid_count": len(valid_projects),
        "invalid_count": len(invalid_projects),
        "projects": valid_projects,
        "errors": errors,
        "raw_keys_if_dict": list(data.keys()) if isinstance(data, dict) else None
    }, indent=2))

if __name__ == "__main__":
    main()
