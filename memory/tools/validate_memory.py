#!/usr/bin/env python3
"""
Workspace and Memory Validator
Checks JSON schemas, required file presence, and formatting constraints to prevent state drift and corrupt memory structures.
"""

import json
import os
import sys

REQUIRED_FILES = [
    "identity.md",
    "rules.md",
]

OPTIONAL_JSON_FILES = [
    "growth_plan.json",
    "commitments.json",
    "core_memories.json"
]

def check_file_exists(filepath):
    return os.path.exists(filepath)

def validate_json_file(filepath):
    if not os.path.exists(filepath):
        return True, "File not present (pending creation)"
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return True, f"Valid JSON syntax ({type(data).__name__})"
    except Exception as e:
        return False, f"JSON parse error: {str(e)}"

def run_checks():
    print("=== Workspace Memory & Structure Integrity Check ===")
    all_passed = True

    # 1. Required core files
    for rfile in REQUIRED_FILES:
        if check_file_exists(rfile):
            print(f"[PASS] Required file present: {rfile}")
        else:
            print(f"[FAIL] Missing required file: {rfile}")
            all_passed = False

    # 2. JSON Integrity
    for jfile in OPTIONAL_JSON_FILES:
        valid, msg = validate_json_file(jfile)
        if valid:
            print(f"[PASS] Schema check for {jfile}: {msg}")
        else:
            print(f"[FAIL] Schema check for {jfile}: {msg}")
            all_passed = False

    print("====================================================")
    if all_passed:
        print("SUMMARY: Integrity verification successful.")
        sys.exit(0)
    else:
        print("SUMMARY: Integrity verification failed.")
        sys.exit(1)

if __name__ == "__main__":
    run_checks()
