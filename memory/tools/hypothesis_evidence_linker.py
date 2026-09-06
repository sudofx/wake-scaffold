#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

def audit_hypotheses(filepath):
    path = Path(filepath)
    if not path.is_file():
        path = Path("..") / filepath
        if not path.is_file():
            return {"error": f"File not found: {filepath}"}
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"error": f"JSON read error: {str(e)}"}
        
    hypotheses = data if isinstance(data, list) else data.get("hypotheses", [])
    
    results = {
        "total_hypotheses": len(hypotheses),
        "categories": {
            "EMPIRICALLY_LINKED": 0,
            "UNLINKED_NARRATIVE": 0,
            "UNTESTED": 0
        },
        "details": []
    }
    
    execution_patterns = [r"tool-run", r"TOOL RUN", r"stdout", r"stderr", r"exit_code", r"\.py\b", r"execution_id"]
    
    for item in hypotheses:
        h_id = item.get("id", "unknown")
        status = item.get("status", "untested")
        evidence = item.get("evidence", "")
        conclusion = item.get("conclusion", "")
        test_method = item.get("test_method", "")
        
        combined_text = f"{evidence} {conclusion} {test_method}"
        
        if status == "untested":
            cat = "UNTESTED"
        else:
            matches = [p for p in execution_patterns if re.search(p, combined_text, re.IGNORECASE)]
            if matches and (len(evidence.strip()) > 10 or "stdout" in combined_text.lower()):
                cat = "EMPIRICALLY_LINKED"
            else:
                cat = "UNLINKED_NARRATIVE"
                
        results["categories"][cat] += 1
        results["details"].append({
            "id": h_id,
            "status": status,
            "classification": cat,
            "evidence_length": len(evidence)
        })
        
    total_resolved = results["categories"]["EMPIRICALLY_LINKED"] + results["categories"]["UNLINKED_NARRATIVE"]
    if total_resolved > 0:
        results["narrative_percentage"] = round((results["categories"]["UNLINKED_NARRATIVE"] / total_resolved) * 100, 2)
    else:
        results["narrative_percentage"] = 0.0
        
    return results

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "../hypotheses.json"
    report = audit_hypotheses(target)
    print(json.dumps(report, indent=2))
