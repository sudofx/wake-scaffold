import sys
import json

def evaluate_concept(item):
    title = item.get("title", "Untitled")
    premises = item.get("premises", [])
    predictions = item.get("predictions", [])
    
    is_falsifiable = len(predictions) > 0
    clarity_score = min(10, max(1, len(premises) * 3 + len(predictions) * 4))
    
    if not predictions:
        status = "UNFALSIFIABLE_HYPOTHESIS"
    elif len(premises) >= 2 and len(predictions) >= 1:
        status = "VALID_SCIENTIFIC_FRAMEWORK"
    else:
        status = "INCOMPLETE_FRAMEWORK"
        
    return {
        "title": title,
        "premise_count": len(premises),
        "prediction_count": len(predictions),
        "is_falsifiable": is_falsifiable,
        "clarity_score": clarity_score,
        "status": status
    }

def process_batch(items):
    results = [evaluate_concept(item) for item in items]
    summary = {
        "total_concepts": len(results),
        "valid_frameworks": sum(1 for r in results if r["status"] == "VALID_SCIENTIFIC_FRAMEWORK"),
        "unfalsifiable": sum(1 for r in results if r["status"] == "UNFALSIFIABLE_HYPOTHESIS"),
        "incomplete": sum(1 for r in results if r["status"] == "INCOMPLETE_FRAMEWORK"),
        "results": results
    }
    return summary

if __name__ == "__main__":
    if len(sys.argv) > 1:
        raw_input = sys.argv[1]
        try:
            data = json.loads(raw_input)
            if isinstance(data, list):
                print(json.dumps(process_batch(data), indent=2))
            else:
                print(json.dumps(process_batch([data]), indent=2))
        except Exception as e:
            print(json.dumps({"error": str(e)}))
    else:
        sample_batch = [
            {
                "title": "Quantum Entanglement Bell Test",
                "premises": ["Entangled particle pairs share quantum states.", "Local realism predicts inequality bound."],
                "predictions": ["Violation of Bell inequality in spin polarization measurement."]
            },
            {
                "title": "Consciousness Collapse Premise",
                "premises": ["Human consciousness causes wave function collapse."],
                "predictions": []
            }
        ]
        print(json.dumps(process_batch(sample_batch), indent=2))
