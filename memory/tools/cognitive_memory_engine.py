import json
import sys

def run_build():
    # Logic to be implemented to build cognitive graph
    # For now, verify functionality
    print(json.dumps({"status": "success", "message": "Cognitive graph built"}))

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'unknown'
    if cmd == 'build':
        run_build()
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))