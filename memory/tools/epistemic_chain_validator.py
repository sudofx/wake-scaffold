import sys
import json
import os

def analyze_hypotheses(filepath):
    if not os.path.exists(filepath):
        fallback = os.path.join("..", filepath)
        if os.path.exists(fallback):
            filepath = fallback
        else:
            return {"valid": False, "error": f"File not found: {filepath}"}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return {"valid": False, "error": str(e)}

    hypotheses = data if isinstance(data, list) else data.get("hypotheses", [])

    total = len(hypotheses)
    confirmed_count = 0
    refuted_count = 0
    untested_count = 0
    weakly_supported = []
    supported = []

    for item in hypotheses:
        status = item.get("status", "untested")
        hid = item.get("id", "unknown")
        evidence = str(item.get("evidence", "")) + " " + str(item.get("conclusion", ""))
        
        if status in ["confirmed", "refuted"]:
            if status == "confirmed":
                confirmed_count += 1
            else:
                refuted_count += 1
            
            if len(evidence.strip()) < 15 or not any(k in evidence.lower() for k in ["tool", "run", "execute", "stdout", "output", "history", "file", "observed", "result", "failed", "error", "created"]):
                weakly_supported.append({"id": hid, "status": status, "evidence_snippet": evidence[:100]})
            else:
                supported.append(hid)
        elif status == "untested":
            untested_count += 1

    return {
        "valid": True,
        "filepath": filepath,
        "total_hypotheses": total,
        "summary": {
            "confirmed": confirmed_count,
            "refuted": refuted_count,
            "untested": untested_count,
            "supported_chains": len(supported),
            "weakly_supported_chains": len(weakly_supported)
        },
        "weakly_supported_details": weakly_supported
    }

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "hypotheses.json"
    report = analyze_hypotheses(target)
    print(json.dumps(report, indent=2))
