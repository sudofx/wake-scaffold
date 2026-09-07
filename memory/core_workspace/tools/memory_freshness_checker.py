import json
import re
from pathlib import Path

def main():
    # Get paths relative to tool script location
    tools_dir = Path(__file__).resolve().parent
    core_workspace = tools_dir.parent
    memory_dir = core_workspace.parent
    index_path = memory_dir / "core_memories" / "index.md"

    output = {
        "status": "UNKNOWN",
        "index_path": str(index_path),
        "last_consolidated_timestamp": None,
        "latest_journal": None,
        "stale_journals": [],
        "error": None
    }

    try:
        if not index_path.exists():
            output["status"] = "ERROR"
            output["error"] = f"index.md not found at {index_path}"
            print(json.dumps(output, indent=2))
            return

        # Read index.md to extract last consolidated journal
        index_content = index_path.read_text()
        # Match 'through 2026-09-07-032146' or similar
        match = re.search(r"through\s+(\d{4}-\d{2}-\d{2}-\d{6})", index_content)
        if not match:
            output["status"] = "INCOMPLETE_INDEX_METADATA"
            output["error"] = "Could not parse standard YYYY-MM-DD-HHMMSS journal timestamp from index.md"
            print(json.dumps(output, indent=2))
            return

        last_consolidated = match.group(1)
        output["last_consolidated_timestamp"] = last_consolidated

        # Scan recursively under memory/ for files matching YYYY-MM-DD-HHMMSS.md
        journal_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})\.md$")
        journals = []
        for path in memory_dir.rglob("*.md"):
            m = journal_pattern.match(path.name)
            if m:
                journals.append((m.group(1), str(path)))

        if not journals:
            output["status"] = "NO_JOURNALS_FOUND"
            output["error"] = "No journal files matching YYYY-MM-DD-HHMMSS.md pattern found."
            print(json.dumps(output, indent=2))
            return

        journals.sort()  # Chronological sorting
        latest_journal_timestamp, latest_journal_path = journals[-1]
        output["latest_journal"] = {
            "timestamp": latest_journal_timestamp,
            "path": latest_journal_path
        }

        # Find journal files with timestamps newer than our consolidated index
        stale = [j for j in journals if j[0] > last_consolidated]
        output["stale_journals"] = [s[0] for s in stale]

        if stale:
            output["status"] = "STALE"
        else:
            output["status"] = "FRESH"

    except Exception as e:
        output["status"] = "ERROR"
        output["error"] = str(e)

    # Output formatted JSON at start to prevent truncation diagnostic loss
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()