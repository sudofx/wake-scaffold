# WAKE✳︎ UI / branding patch

This patch implements the requested presentation cleanup without changing the hash chain, governance rules, model-call contract, or canonical JSON/JSONL formats.

## Included changes

1. `state.html` and `events.html` now use the same light/dark palette as the main WAKE✳︎ site, including the same `wake-theme` preference and a theme toggle.
2. Main navigation label `The lab →` is now `Lab`.
3. The favicon is replaced with a simple WAKE✳︎ mark using the site paper + teal palette rather than the previous orange/purple-looking mark. The readable standalone pages use the same favicon.
4. Automatic README Lab Comics cover rotation is removed from `.github/workflows/wake.yml`. The current cover remains in `README.md` as a manually selected static cover. The existing cover assets/scripts may remain in the repository for manual use.
5. README positioning now says: **WAKE✳︎ is following _the big questions_. Bob is going to blog about WAKE✳︎.** The Blog page copy also frames Bob as blogging about WAKE✳︎.
6. Human-facing WAKE branding in the files included here is normalized to the text-presentation form `WAKE✳︎` (U+2733 + U+FE0E), including the GitHub Actions workflow title.
7. Historical/canonical data is not rewritten. Readable event/state exports normalize the displayed brand glyph only; raw JSON/JSONL remains byte-for-byte authoritative.

## Files to replace

- `README.md`
- `.github/workflows/wake.yml`
- `wake/assets/index.html`
- `wake/report.py`
- `scripts/github_wake.py`
- `scripts/publish.py`
- `tests/test_cloud_workflow.py`
- `tests/test_publishing.py`
- `docs/operations.md`

## Validation performed

- Python syntax compilation for modified Python files.
- Direct render smoke test for the standalone readable HTML helpers.
- Tests updated so cover-rotation workflow expectations are removed and readable HTML theme/favicon/navigation expectations are checked.

No remote files were changed by this patch.
