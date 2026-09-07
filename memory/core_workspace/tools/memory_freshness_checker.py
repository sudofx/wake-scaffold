import sys
import json
import re
from pathlib import Path

def find_repo_root():
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "base_memory").exists() or (parent / "memory").exists() or (parent / ".git").exists():
            return parent
    return current.parents[2]

def locate_all_files(repo_root, filename_pattern):
    return sorted(list(repo_root.glob(f"**/{filename_pattern}")))

def extract_timestamps(text):
    pattern = r"(20\d{2})[-_./]?(\d{2})[-_./]?(\d{2})(?:[-_.\sT]?(\d{2}):?(\d{2}):?(\d{2}))?"
    stamps = []
    for m in re.finditer(pattern, text):
        y, mon, d, h, min_, s = m.groups()
        h = h or "00"
        min_ = min_ or "00"
        s = s or "00"
        stamps.append(f"{y}-{mon}-{d}-{h}{min_}{s}")
    return stamps

def main():
    repo_root = find_repo_root()
    
    index_files = locate_all_files(repo_root, "index.md")
    
    index_details = []
    all_index_stamps = []
    
    for idx_path in index_files:
        try:
            content = idx_path.read_text(encoding="utf-8")
        except Exception as e:
            content = f"Error reading file: {e}"
        
        stamps = extract_timestamps(content)
        all_index_stamps.extend(stamps)
        
        snippet = content[:300] if len(content) > 300 else content
        interesting_lines = [line.strip() for line in content.splitlines() if any(k in line.lower() for k in ["202", "journal", "consolidat", "update", "date"])]
        
        index_details.append({
            "path": str(idx_path.relative_to(repo_root)),
            "timestamps_found": stamps,
            "snippet": snippet,
            "interesting_lines": interesting_lines[:10]
        })
        
    last_consolidated_stamp = max(all_index_stamps) if all_index_stamps else None
    
    journal_files = sorted(list(repo_root.glob("**/journal/20*.md")) + list(repo_root.glob("**/journals/20*.md")))
    latest_journal = journal_files[-1] if journal_files else None
    latest_journal_stamp = None
    if latest_journal:
        j_stamps = extract_timestamps(latest_journal.name)
        if j_stamps:
            latest_journal_stamp = j_stamps[-1]
            
    status = "UNKNOWN"
    if last_consolidated_stamp and latest_journal_stamp:
        if last_consolidated_stamp >= latest_journal_stamp:
            status = "FRESH"
        else:
            status = "STALE"
            
    out = {
        "status": status,
        "index_files_scanned": index_details,
        "last_consolidated_stamp": last_consolidated_stamp,
        "latest_journal_path": str(latest_journal.relative_to(repo_root)) if latest_journal else None,
        "latest_journal_stamp": latest_journal_stamp
    }
    print(json.dumps(out, indent=2))
    sys.exit(0 if status in ["FRESH", "STALE"] else 1)

if __name__ == "__main__":
    main()
