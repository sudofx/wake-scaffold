import sys
import os
import json

def validate_memory(memory_dir):
    if not os.path.isdir(memory_dir):
        alt = os.path.join("..", memory_dir)
        if os.path.isdir(alt):
            memory_dir = alt

    print(f"Validating memory directory: {memory_dir}")
    if not os.path.isdir(memory_dir):
        print(f"ERROR: Memory directory '{memory_dir}' does not exist.")
        sys.exit(1)
        
    files = os.listdir(memory_dir)
    print(f"Found files in {memory_dir}: {files}")
    
    errors = 0
    warnings = 0
    
    def get_items(data, possible_keys):
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for k in possible_keys:
                if k in data and isinstance(data[k], list):
                    return data[k]
            for k, v in data.items():
                if isinstance(v, list):
                    return v
        return None

    targets = {
        'commitments.json': ['commitments', 'items', 'add'],
        'growth_plan.json': ['projects', 'growth_plan', 'items', 'add'],
        'hypotheses.json': ['hypotheses', 'items', 'add'],
        'core_memories.json': ['core_memories', 'memories', 'lessons', 'items']
    }

    for fname, keys in targets.items():
        fpath = os.path.join(memory_dir, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                dtype = type(data).__name__
                items = get_items(data, keys)
                if items is None:
                    print(f"WARNING: {fname} (type {dtype}) could not be extracted into an item list.")
                    warnings += 1
                else:
                    print(f"SUCCESS: {fname} (type {dtype}) validated with {len(items)} item(s).")
            except Exception as e:
                print(f"ERROR: Failed to read/parse {fname}: {e}")
                errors += 1
        else:
            print(f"INFO: {fname} does not exist yet.")

    print(f"Validation summary: {errors} error(s), {warnings} warning(s).")
    if errors > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'memory'
    validate_memory(target)
