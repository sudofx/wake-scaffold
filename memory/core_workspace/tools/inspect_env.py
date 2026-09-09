import os

def main():
    cwd = os.getcwd()
    print(f"CWD: {cwd}")
    print("CWD contents:")
    try:
        for item in os.listdir(cwd):
            print(f"  {item}")
    except Exception as e:
        print(f"  Error listing CWD: {e}")

    print("\nParent directory traversal:")
    curr = cwd
    for depth in range(5):
        print(f"\n--- Depth {depth}: {curr} ---")
        try:
            entries = os.listdir(curr)
            print(f"  Contents ({len(entries)} items): {entries[:10]}")
        except Exception as e:
            print(f"  Error listing: {e}")
        for target in ["identity.md", "rules.md", "index.md", "memory", "core_workspace"]:
            p = os.path.join(curr, target)
            print(f"  Target '{target}': {'EXISTS' if os.path.exists(p) else 'NOT FOUND'}")
        parent = os.path.dirname(curr)
        if parent == curr:
            print("  Reached filesystem root.")
            break
        curr = parent

if __name__ == "__main__":
    main()
