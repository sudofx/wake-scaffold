import json
import os

def find_repo_root():
    start = os.path.abspath(os.path.dirname(__file__))
    curr = start
    while curr and curr != os.path.dirname(curr):
        if os.path.exists(os.path.join(curr, "rules.md")):
            return curr
        curr = os.path.dirname(curr)
    curr = os.path.abspath(os.getcwd())
    while curr and curr != os.path.dirname(curr):
        if os.path.exists(os.path.join(curr, "rules.md")):
            return curr
        curr = os.path.dirname(curr)
    return os.getcwd()

def validate():
    root = find_repo_root()
    checks = {
        "rules_md": os.path.exists(os.path.join(root, "rules.md")),
        "memory_dir": os.path.isdir(os.path.join(root, "memory")),
        "core_workspace_dir": os.path.exists(os.path.join(root, "memory", "core_workspace")) or os.path.exists(os.path.join(root, "core_workspace")),
        "growth_plan": os.path.exists(os.path.join(root, "memory", "core_workspace", "growth_plan.json")) or os.path.exists(os.path.join(root, "growth_plan.json")),
        "hypotheses": os.path.exists(os.path.join(root, "memory", "core_workspace", "hypotheses.json")) or os.path.exists(os.path.join(root, "hypotheses.json")),
        "tool_runs": os.path.exists(os.path.join(root, "memory", "core_workspace", "tool_runs.json")) or os.path.exists(os.path.join(root, "tool_runs.json")),
        "tools_dir": os.path.isdir(os.path.join(root, "memory", "core_workspace", "tools")) or os.path.isdir(os.path.join(root, "tools"))
    }
    all_ok = all(checks.values())
    status = "STRUCTURALLY_COMPLETE" if all_ok else "STRUCTURALLY_INVALID"
    output = {
        "status": status,
        "mechanism": "Repo root traversal and workspace path verification",
        "discovered_root": root,
        "checks": checks
    }
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    validate()
