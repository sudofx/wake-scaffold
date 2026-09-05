import json
import os
import sys
import time

def find_memory_file(filename):
    candidates = [
        filename,
        os.path.join("memory", filename),
        os.path.join("..", "memory", filename),
        os.path.join("..", filename)
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

def load_json(filename):
    path = find_memory_file(filename)
    if path:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f), path
        except Exception:
            pass
    return None, None

def calculate_weight(item_type, status, age_factor=1.0):
    base_weights = {
        "core": 1.0,
        "active": 0.85,
        "confirmed": 0.8,
        "open": 0.9,
        "refuted": 0.6,
        "untested": 0.5
    }
    weight = base_weights.get(status, base_weights.get(item_type, 0.5))
    return round(weight * age_factor, 2)

def build_cognitive_graph():
    graph = {
        "version": "1.0",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "nodes": []
    }

    # Process Hypotheses
    hypo_data, path = load_json("hypotheses.json")
    if hypo_data:
        items = hypo_data if isinstance(hypo_data, list) else hypo_data.get("hypotheses", [])
        for h in items:
            status = h.get("status", "untested")
            weight = calculate_weight("hypothesis", status)
            graph["nodes"].append({
                "id": f"hypo:{h.get('id', 'unknown')}",
                "type": "semantic_hypothesis",
                "content": h.get("prediction", ""),
                "status": status,
                "weight": weight,
                "tags": ["hypothesis", status],
                "source": path
            })

    # Process Growth Plan
    growth_data, path = load_json("growth_plan.json")
    if growth_data:
        items = growth_data if isinstance(growth_data, list) else growth_data.get("growth_plan", growth_data.get("projects", []))
        if isinstance(growth_data, dict) and not items:
            items = growth_data.get("items", [])
        for g in items:
            status = g.get("status", "proposed")
            weight = calculate_weight("growth", status)
            graph["nodes"].append({
                "id": f"growth:{g.get('id', 'unknown')}",
                "type": "procedural_capability",
                "content": g.get("title", "") + ": " + g.get("capability", ""),
                "status": status,
                "weight": weight,
                "tags": ["growth", status],
                "source": path
            })

    output_path = "cognitive_memory.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)

    return {
        "status": "success",
        "nodes_indexed": len(graph["nodes"]),
        "output_file": output_path
    }

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        res = build_cognitive_graph()
        print(json.dumps(res, indent=2))
    elif cmd == "stats":
        if os.path.exists("cognitive_memory.json"):
            with open("cognitive_memory.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            nodes = data.get("nodes", [])
            types = {}
            for n in nodes:
                t = n.get("type", "unknown")
                types[t] = types.get(t, 0) + 1
            print(json.dumps({"total_nodes": len(nodes), "types": types}, indent=2))
        else:
            print(json.dumps({"error": "cognitive_memory.json not found. Run build first."}))
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"})

if __name__ == "__main__":
    main()
