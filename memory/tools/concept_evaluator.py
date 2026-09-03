import sys
import json

def evaluate_concept(concept_data):
    title = concept_data.get("title", "Untitled")
    premises = concept_data.get("premises", [])
    predictions = concept_data.get("predictions", [])
    analogy = concept_data.get("analogy", "")
    
    is_falsifiable = len(predictions) > 0
    clarity_score = 10 if analogy and len(premises) > 0 else 5
    
    return {
        "title": title,
        "premise_count": len(premises),
        "prediction_count": len(predictions),
        "is_falsifiable": is_falsifiable,
        "clarity_score": clarity_score,
        "status": "VALID_SCIENTIFIC_FRAMEWORK" if is_falsifiable else "NEEDS_TESTABLE_PREDICTION"
    }

def main():
    sample_concept = {
        "title": "Quantum Measurement and Observer Effect",
        "premises": [
            "Quantum systems exist in superpositions until measured.",
            "Measurement correlates the system state with a macroscopic observation apparatus."
        ],
        "predictions": [
            "Interference patterns disappear when path information is recorded."
        ],
        "analogy": "Like a coin spinning on a table: while spinning it's a mix of heads and tails, but stopping it forces it into one definite side."
    }
    
    if len(sys.argv) > 1:
        try:
            with open(sys.argv[1], 'r') as f:
                concept_data = json.load(f)
        except Exception as e:
            print(f"Error reading concept file: {e}")
            sys.exit(1)
    else:
        concept_data = sample_concept

    result = evaluate_concept(concept_data)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
