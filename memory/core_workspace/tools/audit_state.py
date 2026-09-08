#!/usr/bin/env python3
import json
import os
import sys

def find_repo_root():
    start_dirs = [os.getcwd(), os.path.dirname(os.path.abspath(__file__))]
    for start in start_dirs:
        curr = os.path.abspath(start)
        while curr != os.path.dirname(curr):
            if os.path.isdir(os.path.join(curr, 'memory')) or os.path.isdir(os.path.join(curr, 'tools')):
                return curr
            curr = os.path.dirname(curr)
    return os.getcwd()

def audit_workspace():
    root = find_repo_root()
    report = {
        "workspace_root": root,
        "status": "STRUCTURALLY_COMPLETE",
        "failures": [],
        "audits": {
            "markdown_files": {},
            "json_files": {},
            "tools_cross_check": {}
        }
    }

    target_mds = ["identity.md", "rules.md", "index.md"]
    for md in target_mds:
        found = False
        for dirpath, _, filenames in os.walk(root):
            if md in filenames:
                full_path = os.path.join(dirpath, md)
                rel_path = os.path.relpath(full_path, root)
                size = os.path.getsize(full_path)
                report["audits"]["markdown_files"][md] = {
                    "exists": True,
                    "path": rel_path,
                    "size_bytes": size
                }
                found = True
                break
        if not found:
            report["audits"]["markdown_files"][md] = {"exists": False}
            report["failures"].append(f"Missing core markdown file: {md}")

    target_jsons = ["commitments.json", "tool_runs.json"]
    for jf in target_jsons:
        found_path = None
        for dirpath, _, filenames in os.walk(root):
            if jf in filenames:
                found_path = os.path.join(dirpath, jf)
                break
        if found_path and os.path.exists(found_path):
            rel_path = os.path.relpath(found_path, root)
            try:
                with open(found_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                report["audits"]["json_files"][jf] = {
                    "exists": True,
                    "path": rel_path,
                    "valid_json": True,
                    "item_count": len(data) if isinstance(data, list) else len(data.keys()) if isinstance(data, dict) else 0
                }
            except Exception as e:
                report["audits"]["json_files"][jf] = {
                    "exists": True,
                    "path": rel_path,
                    "valid_json": False,
                    "error": str(e)
                }
                report["failures"].append(f"Invalid JSON in {jf}: {str(e)}")
        else:
            report["audits"]["json_files"][jf] = {"exists": False}
            report["failures"].append(f"Missing state JSON file: {jf}")

    tools_dir = os.path.join(root, "tools")
    if not os.path.exists(tools_dir):
        for dirpath, dirnames, _ in os.walk(root):
            if "tools" in dirnames:
                tools_dir = os.path.join(dirpath, "tools")
                break

    existing_tools = []
    if os.path.exists(tools_dir):
        existing_tools = [f for f in os.listdir(tools_dir) if os.path.isfile(os.path.join(tools_dir, f))]
    
    report["audits"]["tools_cross_check"]["existing_tool_files"] = existing_tools

    tool_runs_path = None
    for dirpath, _, filenames in os.walk(root):
        if "tool_runs.json" in filenames:
            tool_runs_path = os.path.join(dirpath, "tool_runs.json")
            break

    if tool_runs_path and os.path.exists(tool_runs_path):
        try:
            with open(tool_runs_path, "r", encoding="utf-8") as f:
                runs = json.load(f)
            referenced_tools = list(set(r.get("tool", r.get("filename", "")) for r in runs if isinstance(r, dict)))
            report["audits"]["tools_cross_check"]["referenced_tools_in_history"] = referenced_tools
        except Exception as e:
            report["failures"].append(f"Failed parsing tool_runs.json for cross-check: {str(e)}")

    if report["failures"]:
        report["status"] = "STRUCTURALLY_INVALID"

    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    audit_workspace()
