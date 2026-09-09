#!/usr/bin/env python3
"""Create a clean replacement ZIP. Never include credentials or private state."""

from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "wake-scaffold.zip"
FILES = ["README.md", "LICENSE", ".env.example", ".gitignore", "wake.toml", "pyproject.toml", "requirements.txt"]
FOLDERS = ["wake", "tests", "docs", "scripts", ".github", "examples"]


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
        paths = [ROOT / name for name in FILES]
        paths += [path for name in FOLDERS for path in (ROOT / name).rglob("*") if path.is_file()]
        for path in sorted(paths):
            if "__pycache__" not in path.parts and path.suffix != ".pyc" and path.name != ".DS_Store":
                archive.write(path, path.relative_to(ROOT))
    print(OUTPUT)
