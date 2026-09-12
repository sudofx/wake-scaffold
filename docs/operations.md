# Operating the record

**The GitHub-hosted research system uses [cloud operations](cloud.md).** The commands below operate an independent local record. Do not run a second live schedule against the cloud record’s API allowance.

## Everyday commands

Global options precede the command: `python3 -m wake --data data/another-record status`.

```sh
python3 -m wake status
python3 -m wake audit
python3 -m wake observe --source human:bench-test --text 'The measured output was 17; expected tolerance was 9–11.'
python3 -m wake focus 'Review contradictory measurements' --reason 'New bench result conflicts with the current belief.'
python3 -m wake cancel commitment-ID --reason 'The operator has withdrawn this task.'
python3 -m wake export --output site
python3 -m wake backup /absolute/path/to/new-backup.sqlite3
```

`data/wake.sqlite3` is the authoritative record. `site/` is generated and disposable. Keep private observations out of a journal you intend to publish. Exact model requests and replies are included in `events.jsonl` and the HTML audit view; the renderer does not silently redact scientific evidence. API keys and `.env` are never read into prompts or exports by WAKE✳.

Each export also creates human-readable companions for the two core machine exports: `events.md` and `events.html` present the complete event history, including exact model requests and replies, while `state.md` and `state.html` present the current durable state. These files are presentation layers only. `events.jsonl`, `state.json`, and the verified `head.txt` remain the audit sources of record.

## Scheduled wakes

First verify a single live `wake` and `export`. Then run `python3 scripts/install_cron.py` to install one managed entry every three hours. This explicitly edits your user crontab, preserving unrelated entries. `--print` shows the command first and `--remove` removes only WAKE✳’s entry. The installer records the absolute Python executable and project path, so cron does not need an activated environment.

The wrapper refreshes output even when a model rejects or fails. Every run keeps a SQLite backup under `data/backups/`; manage retention according to your storage budget. Backups are deliberately not silently deleted. Check `data/cron.log` and the journal's History view. The schedule uses the host cron timezone; the daily API limit and report dates always use Pacific time. The every-three-hours cadence leaves room under a 20-call daily ceiling. A sleeping or disconnected host cannot run a wake; cron does not catch up missed cycles. macOS may require permission for cron to read a protected folder; keep the project in Developer rather than Downloads/Desktop.

To manually exercise exactly what cron will run: `python3 scripts/scheduled_wake.py`. This invokes the configured provider, so it can consume one live API call after free-tier opt-in.

## Read on iPhone, iPad and Mac

For local desktop reading, open `site/journal.md` or `site/index.html`. The HTML contains its own CSS, JavaScript and data, with no remote fonts, tracking, dependencies or fetch requests. The layout adapts to a 375-pixel iPhone 12 mini viewport, iPad and desktop. Lab and evidence are links away from the main journal. JavaScript-disabled readers can use the complete Markdown export.

For a direct readable view of the raw record, open `site/events.html` or `site/events.md`. The matching durable-state views are `site/state.html` and `site/state.md`. The HTML versions are standalone static pages; the Markdown versions remain easy to inspect directly in GitHub.

To read from another device on the same network:

```sh
python3 -m wake serve --host 0.0.0.0 --port 8000
```

Visit `http://YOUR-MACS-LAN-ADDRESS:8000` on that device while the server is running. This serves the generated report directory, not the repository. Anyone who can reach this port can read the exported report.

For access from anywhere, the optional GitHub Pages publishing flow uses an existing `origin` remote and your normal Git authentication:

```sh
# Review site/ first. This explicitly publishes all report and evidence files.
python3 scripts/publish.py --confirm-public
```

The script copies `index.html`, `journal.md`, the raw `state.json` and `events.jsonl`, their human-readable Markdown and HTML companions, `head.txt`, published notebook Markdown files, and optional `experiment.json` into an isolated temporary checkout. It pushes a new commit to `journal-pages`, without changing your source checkout or force-pushing. In repository Settings → Pages, select **Deploy from a branch**, **journal-pages**, **/ (root)**. Your repository must be eligible for free Pages hosting; the usual zero-dollar route is a public repository. See [GitHub's Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site).

After publication, the readable pages are available alongside the main journal as `events.html` and `state.html`; `events.md` and `state.md` are available in the same branch for direct GitHub reading.

After the first publication, set `publish_reports = true` in `wake.toml` to explicitly opt scheduled runs into the same publication. Publishing failure leaves the durable local record and report intact. Local backups are never pushed. Source commits and secrets are never copied to the publishing branch. A concurrent publisher causes a non-fast-forward failure instead of overwriting someone else's work.

The included `examples/journal/` is a shareable fixture report. To publish that instead, pass `--directory examples/journal`. Its simulated labels remain visible. `htmlpreview.github.io` may also display the self-contained `index.html` directly from a repository; Pages is the more predictable option.

## Crash, corruption and recovery

```sh
python3 -m wake recover
python3 -m wake audit
python3 -m wake export
```

Recovery reconstructs a corrupt projection from valid event history and closes unfinished invocations. It does not refund an uncertain API attempt. Manual requests are only abandoned by explicit recovery, so a slow desktop reply is not silently lost.

If the event history itself is damaged, stop scheduled wakes. Preserve the damaged directory for investigation. Restore a separately retained SQLite backup into a **new** state directory as `wake.sqlite3`, then run `--data that-directory audit`, `recover` if needed, and `export`. Never recover by deleting inconvenient events. When resuming a backup from earlier today, use manual/fixture mode until the next Pacific day or account conservatively for calls made since the backup; the older ledger cannot know about later attempts.

To audit outside the database:

```sh
python3 -m wake audit --events site/events.jsonl --head /independently/retained/head.txt
```

The head must correspond to the export you are verifying. Store the export and its head together for reconstruction and retain another copy of the head separately for tamper/truncation detection.

## Updates and replacement

This is a new architecture, not a migration of older Bob identity/memory directories. Earlier experimental records remain in Git history and in the local pre-rebuild backup. Do not re-label them as verified v2 events. Private credentials can be retained in `.env`.

`scripts/package.py` creates a complete replacement ZIP using a source allowlist. Extracting the ZIP needs no existing files besides a usable Python installation. Runtime `data/`, backups and API keys are deliberately excluded; keep them separately when updating an existing v2 installation.
