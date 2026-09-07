import os
import json
from pathlib import Path

def explore():
    current_file = Path(__file__).resolve()
    tools_dir = current_file.parent
    
    result = {
        "current_file": str(current_file),
        "tools_dir": str(tools_dir),
        "parents": []
    }
    
    # Traverse up and collect dir contents
    for i in range(5):
        if i < len(tools_dir.parents):
            parent = tools_dir.parents[i]
            if parent.exists():
                try:
                    entries = os.listdir(parent)
                    dirs = [e for e in entries if (parent / e).is_dir()]
                    files = [e for e in entries if (parent / e).is_file()]
                    result["parents"].append({
                        "level": i + 1,
                        "path": str(parent),
                        "dirs": dirs,
                        "files": files[:20]  # Safe limit to prevent stdout truncation
                    })
                except Exception as e:
                    result["parents"].append({
                        "level": i + 1,
                        "path": str(parent),
                        "error": str(e)
                    })
                
    # Read env_check.py if it exists
    env_check_path = tools_dir / "env_check.py"
    if env_check_path.exists():
        try:
            result["env_check_source"] = env_check_path.read_text()
        except Exception as e:
            result["env_check_source"] = f"Error reading: {e}"
    else:
        result["env_check_source"] = "Not found"
        
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    explore()