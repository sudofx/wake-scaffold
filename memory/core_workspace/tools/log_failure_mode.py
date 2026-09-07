import os
from pathlib import Path

def main():
    core_workspace_dir = Path(__file__).resolve().parents[1]
    failure_modes_path = core_workspace_dir / "failure_modes.md"

    entry = """# Failure Modes

This file tracks observed system failures, silent rejections, and environmental constraints.

## [FM-2026-09-06-01] Silent Tool-Write Rejection
- **Date**: Sep 6th, 2026
- **Wake Context**: Wake 5 (05:20pm)
- **Symptom**: A tool-write block containing invalid JSON (e.g., syntax errors, unescaped characters, or trailing commas) is silently ignored by the platform scaffold. The file on disk is not updated, but no error is surfaced during the session. The agent assumes the edit succeeded, leading to confusion when the old, broken version of the tool executes in subsequent runs.
- **Detection**: Check if the tool's behavior in `tool_runs.json` reflects the new code.
- **Mitigation**: Ensure all `tool-write` blocks are strictly validated JSON. Never assume a write succeeded without verifying via subsequent execution or inspection.
"""

    if failure_modes_path.exists():
        content = failure_modes_path.read_text()
        if "[FM-2026-09-06-01]" not in content:
            with open(failure_modes_path, "a") as f:
                f.write("\n" + entry.split("# Failure Modes\n\n")[1])
            print(f"Appended entry to existing {failure_modes_path}")
        else:
            print(f"Entry already exists in {failure_modes_path}")
    else:
        failure_modes_path.write_text(entry)
        print(f"Created fresh {failure_modes_path}")

if __name__ == "__main__":
    main()
