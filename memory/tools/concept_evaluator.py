# NOTE ON WHAT THIS TOOL ACTUALLY CHECKS (added during a code review pass,
# not a wake cycle): `is_falsifiable` is a keyword match against a small
# fixed list ("test", "measure", "observe", "detect", "disappear") in the
# prediction text, and `clarity_score` is a weighted count of list lengths.
# Neither checks whether a premise is true, whether the prediction is
# coherent, or whether the analogy is apt. The status field describes
# *structural shape* (does this look like it has a testable prediction and
# enough content?), not scientific validity. Earlier versions labeled a
# passing structural check "VALID_SCIENTIFIC_FRAMEWORK", which overclaims
# what a keyword/length heuristic can tell you. Renamed to make that
# limitation visible in the output itself, per rules.md's "Tool honesty"
# section.

import sys
import json

def evaluate_concept(data):
    title = data.get("title", "Untitled Concept")
    premises = data.get("premises", [])
    predictions = data.get("predictions", [])
    analogy = data.get("analogy", "")
    
    has_testable_keyword = len(predictions) > 0 and any(
        any(kw in p.lower() for kw in ["test", "measure", "observe", "detect", "disappear"])
        for p in predictions
    )
    clarity_score = min(10, (len(premises) * 2) + (len(predictions) * 3) + (2 if analogy else 0))
    
    if has_testable_keyword and clarity_score >= 5:
        status = "STRUCTURALLY_COMPLETE"
    elif not has_testable_keyword:
        status = "UNFALSIFIABLE_HYPOTHESIS"
    else:
        status = "INCOMPLETE_STRUCTURE"
        
    return {
        "title": title,
        "premise_count": len(premises),
        "prediction_count": len(predictions),
        "is_falsifiable": has_testable_keyword,
        "clarity_score": clarity_score,
        "status": status,
        "analogy": analogy,
        "note": "Heuristic structural check (keyword match + length count). Not a judgment of truth, coherence, or scientific validity."
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
