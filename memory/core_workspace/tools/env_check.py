import os
import json

def main():
    print("Checking environment and workspace...")
    results = {}
    
    # Check memory directory
    memory_dir = "memory"
    if os.path.exists(memory_dir):
        results["memory_files"] = os.listdir(memory_dir)
    else:
        results["memory_files"] = "Not found"
        
    # Check tools directory
    tools_dir = "tools"
    if os.path.exists(tools_dir):
        results["tools_files"] = os.listdir(tools_dir)
    else:
        results["tools_files"] = "Not found"
        
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
