import os
import json

def main():
    print('--- Current Working Directory ---')
    cwd = os.getcwd()
    print(cwd)

    print('\n--- Recursive Directory Listing (up to 3 levels deep) ---')
    # Walk up to find the root of the workspace or repo
    start_dir = os.path.abspath(os.path.join(cwd, '..', '..'))
    print(f'Starting walk from: {start_dir}')
    
    for root, dirs, files in os.walk(start_dir):
        # Calculate depth
        depth = root[len(start_dir):].count(os.sep)
        if depth > 3:
            continue
        indent = '  ' * depth
        print(f'{indent}[D] {os.path.basename(root)}/')
        for f in files[:10]: # limit files listed to keep output clean
            print(f'{indent}  - {f}')
        if len(files) > 10:
            print(f'{indent}  - ... and {len(files) - 10} more files')

    # Try to find and display core_manifest.json
    manifest_path = None
    for root, dirs, files in os.walk(start_dir):
        if 'core_manifest.json' in files:
            manifest_path = os.path.join(root, 'core_manifest.json')
            break
            
    if manifest_path:
        print(f'\n--- Found core_manifest.json at {manifest_path} ---')
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
                print(json.dumps(manifest, indent=2))
        except Exception as e:
            print(f'Error reading manifest: {e}')
    else:
        print('\n--- core_manifest.json not found ---')

if __name__ == '__main__':
    main()