import sys
import json
import os

def evaluate_concept(item):
    title = item.get("title", "Untitled")
    premises = item.get("premises", [])
    predictions = item.get("predictions", [])
    
    is_falsifiable = len(predictions) > 0 and len(premises) > 0
    
    if is_falsifiable:
        status = "VALID_SCIENTIFIC_FRAMEWORK"
    else:
        status = "UNFALSIFIABLE_OR_INCOMPLETE"
        
    return {
        "title": title,
        "status": status,
        "premises_count": len(premises),
        "predictions_count": len(predictions)
    }

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No input provided"}))
        sys.exit(1)
        
    arg = sys.argv[1]
    data = None
    
    if os.path.exists(arg) or arg.endswith('.json'):
        try:
            with open(arg, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(json.dumps({"error": f"Failed to read file {arg}: {str(e)}"}))
            sys.exit(1)
    else:
        try:
            data = json.loads(arg)
        except Exception as e:
            print(json.dumps({"error": f"Failed to parse JSON string: {str(e)}"}))
            sys.exit(1)
            
    if isinstance(data, dict):
        data = [data]
        
    results = [evaluate_concept(item) for item in data]
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
