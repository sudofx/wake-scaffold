import os
import json

def main():
    print('=== WORKSPACE EXPLORER ===')
    cwd = os.getcwd()
    print('Current Working Directory: ' + str(cwd))
    
    results = {
        'cwd': cwd,
        'cwd_contents': [],
        'parent_contents': [],
        'errors': []
    }
    
    try:
        results['cwd_contents'] = os.listdir('.')
    except Exception as e:
        results['errors'].append('Error listing cwd: ' + str(e))
        
    try:
        results['parent_contents'] = os.listdir('..')
    except Exception as e:
        results['errors'].append('Error listing parent: ' + str(e))

    print('Contents of cwd: ' + str(results['cwd_contents']))
    print('Contents of parent: ' + str(results['parent_contents']))

    paths_to_try = [
        'core_workspace/tool_runs.json',
        '../core_workspace/tool_runs.json',
        '../../core_workspace/tool_runs.json',
        'memory/core_workspace/tool_runs.json',
        '../memory/core_workspace/tool_runs.json'
    ]
    
    target_path = None
    for p in paths_to_try:
        norm_p = os.path.normpath(p)
        dir_name = os.path.dirname(norm_p)
        if os.path.exists(dir_name):
            target_path = norm_p
            break
            
    print('Target path: ' + str(target_path))
    
    run_record = {
        'tool': 'explore_workspace',
        'timestamp': '2026-09-08T21:12:00',
        'status': 'STRUCTURALLY_COMPLETE',
        'result': results
    }
    
    if target_path:
        try:
            runs = []
            if os.path.exists(target_path):
                with open(target_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        runs = json.loads(content)
            runs.append(run_record)
            with open(target_path, 'w') as f:
                json.dump(runs, f, indent=2)
            print('Successfully wrote run record to ' + str(target_path))
        except Exception as e:
            print('Error writing: ' + str(e))
            results['errors'].append('Error writing: ' + str(e))
    else:
        print('No valid path')
        results['errors'].append('No valid path')

if __name__ == '__main__':
    main()
