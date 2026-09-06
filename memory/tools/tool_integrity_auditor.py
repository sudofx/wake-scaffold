#!/usr/bin/env python3
"""
Audits script files in tools/ to report script inventory.
"""
import sys
import os
import json

def audit_tools(tools_dir):
    if not os.path.exists(tools_dir):
        return {"valid": False, "error": f"Directory not found: {tools_dir}"}

    tool_files = [f for f in os.listdir(tools_dir) if f.endswith(".py")]
    
    report = {
        "valid": True,
        "tools_directory": tools_dir,
        "total_script_files": len(tool_files),
        "files": tool_files,
        "audit_status": "AUDITED"
    }
    return report

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "tools"
    result = audit_tools(target_dir)
    print(json.dumps(result, indent=2))
