import os
import sys

def list_files(startpath):
    print('=== DIRECTORY STRUCTURE ===')
    for root, dirs, files in os.walk(startpath):
        # Skip hidden directories like .git
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print(f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print(f'{subindent}{f}')

def print_file(filepath):
    print(f'\n=== CONTENT OF {filepath} ===')
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            print(f.read())
    else:
        print('File not found.')

if __name__ == '__main__':
    list_files('.')
    if os.path.exists('tools/validate_memory.py'):
        print_file('tools/validate_memory.py')
    elif os.path.exists('core_workspace/tools/validate_memory.py'):
        print_file('core_workspace/tools/validate_memory.py')
