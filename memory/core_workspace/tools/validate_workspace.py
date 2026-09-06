import os
import json

def main():
    targets = ['memory', 'tools']
    details = {}
    all_present = True
    for target in targets:
        present = os.path.exists(target)
        details[target] = 'PRESENT' if present else 'ABSENT'
        if not present:
            all_present = False
    
    status = 'STRUCTURALLY_COMPLETE' if all_present else 'STRUCTURALLY_INVALID'
    output = {
        'status': status,
        'mechanism': 'Checked presence of required core workspace paths',
        'details': details
    }
    print(json.dumps(output, indent=2))

if __name__ == '__main__':
    main()
