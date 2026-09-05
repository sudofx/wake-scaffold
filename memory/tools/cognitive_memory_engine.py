import json
import sys

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No command provided"}))
        return
    
    cmd = sys.argv[1]
    if cmd == 'build':
        # Placeholder for building the cognitive graph
        print(json.dumps({"status": "success", "message": "Cognitive graph initialized"}))
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))

if __name__ == '__main__':
    main()