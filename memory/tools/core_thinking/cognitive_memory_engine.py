import os
import sys
import json

def find_memory_dir():
    candidates = [
        os.path.abspath('.'),
        os.path.abspath('..'),
        os.path.abspath('memory'),
        os.path.abspath('../memory'),
    ]
    for c in candidates:
        if os.path.exists(os.path.join(c, 'hypotheses.json')) or os.path.exists(os.path.join(c, 'growth_plan.json')):
            return c
    return os.path.abspath('.')

def build_graph():
    mem_dir = find_memory_dir()
    nodes = []
    edges = []

    hyp_path = os.path.join(mem_dir, 'hypotheses.json')
    if os.path.exists(hyp_path):
        try:
            with open(hyp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                items = data.get('hypotheses', data) if isinstance(data, dict) else data
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            h_id = item.get('id', 'unknown')
                            pred = item.get('prediction', '')
                            nodes.append({'id': h_id, 'type': 'hypothesis', 'text': pred, 'status': item.get('status', 'untested')})
        except Exception:
            pass

    gp_path = os.path.join(mem_dir, 'growth_plan.json')
    if os.path.exists(gp_path):
        try:
            with open(gp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                items = data.get('projects', data) if isinstance(data, dict) else data
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            g_id = item.get('id', 'unknown')
                            title = item.get('title', '')
                            cap = item.get('capability', '')
                            nodes.append({'id': g_id, 'type': 'growth_project', 'text': f'{title} {cap}', 'status': item.get('status', 'proposed')})
        except Exception:
            pass

    graph = {'nodes': nodes, 'edges': edges, 'count': len(nodes)}
    graph_path = os.path.join(os.path.dirname(__file__), 'cognitive_graph.json')
    try:
        with open(graph_path, 'w', encoding='utf-8') as f:
            json.dump(graph, f, indent=2)
    except Exception:
        pass

    return graph

def query_graph(term):
    graph_path = os.path.join(os.path.dirname(__file__), 'cognitive_graph.json')
    graph = None
    if os.path.exists(graph_path):
        try:
            with open(graph_path, 'r', encoding='utf-8') as f:
                graph = json.load(f)
        except Exception:
            pass

    if not graph:
        graph = build_graph()

    results = []
    term_lower = term.lower()
    for node in graph.get('nodes', []):
        text = node.get('text', '').lower()
        node_id = node.get('id', '').lower()
        node_type = node.get('type', '').lower()
        
        score = 0.0
        if term_lower in node_id:
            score += 2.0
        if term_lower in node_type:
            score += 1.5
        if term_lower in text:
            score += 1.0
            
        if score > 0:
            res_node = dict(node)
            res_node['score'] = score
            results.append(res_node)

    results.sort(key=lambda x: x['score'], reverse=True)
    return {'query': term, 'matches': results, 'total_matches': len(results)}

def main():
    if len(sys.argv) < 2:
        cmd = 'stats'
    else:
        cmd = sys.argv[1].lower()

    if cmd == 'build':
        g = build_graph()
        print(json.dumps({'status': 'success', 'message': 'Cognitive graph initialized', 'node_count': g['count']}))
    elif cmd == 'query':
        term = sys.argv[2] if len(sys.argv) > 2 else ''
        res = query_graph(term)
        print(json.dumps(res))
    elif cmd == 'stats':
        graph_path = os.path.join(os.path.dirname(__file__), 'cognitive_graph.json')
        if os.path.exists(graph_path):
            with open(graph_path, 'r', encoding='utf-8') as f:
                g = json.load(f)
            print(json.dumps({'status': 'success', 'node_count': len(g.get('nodes', []))}))
        else:
            g = build_graph()
            print(json.dumps({'status': 'success', 'node_count': g['count']}))
    else:
        print(json.dumps({'error': f'Unknown command: {cmd}'}))

if __name__ == '__main__':
    main()
