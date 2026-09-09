import os
import json
import hashlib
import shutil
import sys
from datetime import datetime

def hash_file(filepath):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def find_memory_root(start_dir):
    curr = start_dir
    while True:
        manifest = os.path.join(curr, "core_manifest.json")
        if os.path.exists(manifest):
            return curr, manifest
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent
    return None, None

def main():
    print("=== MEMORY BACKUP & INTEGRITY TOOL ===")
    cwd = os.getcwd()
    root, manifest_path = find_memory_root(cwd)
    if not root:
        print("ERROR: core_manifest.json not found in hierarchy.")
        sys.exit(1)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(root, "core_workspace", "backups", f"snapshot_{timestamp}")
    os.makedirs(backup_dir, exist_ok=True)

    copied_files = []
    targets = [
        "core_manifest.json",
        "core_identity/identity.md",
        "core_memories/index.md",
        "core_workspace/hypotheses.json",
        "core_workspace/growth_plan.json"
    ]

    backup_manifest = {
        "timestamp": timestamp,
        "files": {}
    }

    all_valid = True
    for rel_path in targets:
        src = os.path.join(root, rel_path)
        if os.path.exists(src):
            dst = os.path.join(backup_dir, rel_path)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            
            src_hash = hash_file(src)
            dst_hash = hash_file(dst)

            if src_hash == dst_hash:
                backup_manifest["files"][rel_path] = {
                    "hash": src_hash,
                    "size": os.path.getsize(src),
                    "status": "VERIFIED"
                }
                copied_files.append(rel_path)
            else:
                backup_manifest["files"][rel_path] = {
                    "status": "HASH_MISMATCH"
                }
                all_valid = False
        else:
            backup_manifest["files"][rel_path] = {
                "status": "FILE_NOT_FOUND"
            }

    manifest_dst = os.path.join(backup_dir, "backup_manifest.json")
    with open(manifest_dst, 'w', encoding='utf-8') as f:
        json.dump(backup_manifest, f, indent=2)

    status = "BACKUP_VERIFIED" if all_valid and len(copied_files) > 0 else "BACKUP_FAILED"
    print(f"Backup Status: {status}")
    print(f"Backed up {len(copied_files)} files to {backup_dir}")
    print(json.dumps(backup_manifest, indent=2))

if __name__ == "__main__":
    main()
