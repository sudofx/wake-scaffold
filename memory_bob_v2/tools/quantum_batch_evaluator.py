# NOTE ON WHAT THIS TOOL ACTUALLY CHECKS (added during a code review pass,
# not a wake cycle): this script only counts list lengths and checks for a
# few keywords. It cannot evaluate whether a premise is true, whether a
# prediction is coherent, or whether an analogy holds. Status labels below
# describe *structural shape* (does this have premises and a prediction to
# test?), not scientific validity or correctness. Earlier versions of this
# tool used the label "VALID_SCIENTIFIC_FRAMEWORK" for that structural
# check, which overclaims what a length/keyword count can tell you. Renamed
# to make that limitation visible in the output itself, per rules.md's
# "Tool honesty" section.

import sys
import json
import os

def evaluate_concept(item):
    title = item.get("title", "Untitled")
    premises = item.get("premises", [])
    predictions = item.get("predictions", [])
    
    has_falsifiable_shape = len(predictions) > 0 and len(premises) > 0
    
    if has_falsifiable_shape:
        status = "STRUCTURALLY_COMPLETE"
    else:
        status = "UNFALSIFIABLE_OR_INCOMPLETE"
        
    return {
        "title": title,
        "status": status,
        "premises_count": len(premises),
        "predictions_count": len(predictions),
        "note": "Structural check only (premise/prediction counts). Not a judgment of truth, coherence, or scientific validity."
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
