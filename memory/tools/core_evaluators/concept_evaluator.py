import sys
import json

def evaluate_concept(data):
    title = data.get("title", "Untitled Concept")
    premises = data.get("premises", [])
    predictions = data.get("predictions", [])
    analogy = data.get("analogy", "")
    
    is_falsifiable = len(predictions) > 0 and any(
        any(kw in p.lower() for kw in ["test", "measure", "observe", "detect", "disappear"])
        for p in predictions
    )
    clarity_score = min(10, (len(premises) * 2) + (len(predictions) * 3) + (2 if analogy else 0))
    
    if is_falsifiable and clarity_score >= 5:
        status = "VALID_SCIENTIFIC_FRAMEWORK"
    elif not is_falsifiable:
        status = "UNFALSIFIABLE_HYPOTHESIS"
    else:
        status = "NEEDS_REFINEMENT"
        
    return {
        "title": title,
        "premise_count": len(premises),
        "prediction_count": len(predictions),
        "is_falsifiable": is_falsifiable,
        "clarity_score": clarity_score,
        "status": status,
        "analogy": analogy
    }

def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        try:
            if arg.startswith("{"):
                data = json.loads(arg)
            else:
                with open(arg, "r") as f:
                    data = json.load(f)
        except Exception as e:
            print(json.dumps({"error": f"Failed to parse input: {str(e)}"}))
            sys.exit(1)
    else:
        data = {
            "title": "Quantum Measurement and Observer Effect",
            "premises": [
                "Wavefunctions collapse upon interaction with a macroscopic measurement apparatus.",
                "Entanglement preserves non-local correlations until decoherence occurs."
            ],
            "predictions": [
                "Interference pattern disappears in double-slit experiment when path detectors are active."
            ],
            "analogy": "Like a spinning coin settling into heads or tails the moment it hits the table."
        }
    
    result = evaluate_concept(data)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
