# WAKE ✳

**Same tape. Fresh deck.**

Disposable models. Durable state. Receipts for everything.

WAKE tests a specific hypothesis: can durable state, evidence, commitments, and mechanical governance make fresh model invocations behave as one accountable process? A model gets one request and proposes a small set of changes. The system checks them, commits the entire decision atomically, and records who did what and why. Then the process exits.

The public journal has some Gen-X mileage on it. The laboratory does not get to substitute attitude for evidence.

## Start here — no account, no API calls

Requires **Python 3.11 or later on macOS or Linux**. No runtime packages, Node, database server, or build tools to install. Run commands from the project directory.

```sh
# Read the included, fully executed 100-cycle experiment.
python3 -m wake serve --directory examples/journal
# Open http://127.0.0.1:8000
```

The [included Markdown journal](examples/journal/journal.md) and [experiment results](examples/journal/experiment.json) are readable without running anything. The HTML is self-contained, responsive, and works as a local file. It has a journal, lab notebook, belief and commitment registers, searchable evidence, a cycle chart, and the full audit trail. Every simulated entry is labeled.

To reproduce the experiment from scratch:

```sh
python3 -m wake --data data/rehearsal experiment --cycles 100 --output site
python3 -m wake audit --events site/events.jsonl --head site/head.txt
python3 -m wake serve
```

Use a **new** data directory each time. The experiment refuses to erase existing records. It launches over 100 separate Python processes, alternates two deterministic provider implementations, changes persisted focus in a controlled branch, attempts an invalid action, revises and retracts a belief, kills processes at two save boundaries, corrupts a cached projection, and reconstructs the result from exported history alone. It costs **zero API calls**.

These are harness guarantees tested with simulated providers, **not evidence of live-model comprehension**. The separate live experiment protocol is in [docs/experiment.md](docs/experiment.md).

## A real record with Gemini

```sh
cp .env.example .env   # Only if you do not already have a .env file.
# Put GEMINI_API_KEY=your-key in .env.
python3 -m wake init
python3 -m wake observe --source human:research-plan --text 'Evaluate whether each fresh invocation inherits open obligations without a reminder.'
```

In `wake.toml`, confirm `free_tier_confirmed = true` **only after verifying that your Gemini API project has billing disabled**. The default model is configurable `gemini-2.5-flash`. Then:

```sh
python3 -m wake wake
python3 -m wake export
python3 -m wake serve
```

One wake makes at most one Gemini request. The local ceiling is 20 attempts per Pacific calendar day, including failed calls and interrupted attempts. No retries, paid fallback, web grounding, or hidden second model call. Token and context ceilings bound each request. A provider's actual free quota can be lower, and the program cannot inspect your billing settings. See [Google's rate-limit documentation](https://ai.google.dev/gemini-api/docs/rate-limits) and [API pricing](https://ai.google.dev/gemini-api/docs/pricing).

The rebuild preserves an existing `.env`; it is never included in the ZIP or report. No live calls are necessary to run the tests or demo.

## Claude, ChatGPT, and other desktop models

Use free desktop sessions manually without assuming they include free API access:

```sh
python3 -m wake prepare --model 'Claude Desktop / human-attested' --output request.json
# Paste request.json into a fresh desktop chat. Ask for the specified JSON object.
# Save the response alone as reply.json, then use the ID printed by prepare:
python3 -m wake complete --id w-REPLACE_WITH_PRINTED_ID --file reply.json
python3 -m wake export
```

The exact request is durable before you switch apps. A pending manual request blocks automatic wakes until completed or explicitly recovered. All providers cross the same governance boundary. Manual model identity is honestly labeled human-attested. To add another API adapter, implement `name`, `model`, `charged`, and `propose(request) -> (raw_json, metadata)` and register it in the CLI; the state and governance layer do not change.

## Set it and inspect it

```sh
# See the proposed cron line without installing it.
python3 scripts/install_cron.py --print
# Explicitly install an every-three-hours schedule (about 8 attempts/day).
python3 scripts/install_cron.py
# Remove only WAKE's schedule.
python3 scripts/install_cron.py --remove
```

Each scheduled cycle refreshes the HTML/Markdown and retains a consistent SQLite backup. It runs while the host is awake; cron cannot wake a sleeping Mac. Existing cron entries are preserved. Logs live in `data/cron.log`. Scheduling and publishing are not activated merely by installing or rebuilding the project.

For iPhone, iPad and Mac access away from the host, opt into publishing the static reports to GitHub Pages. The included publishing script maintains a separate `journal-pages` branch without force pushes. See [operations and publishing](docs/operations.md). No hosting service is required for local reading.

## How it works

```text
SQLite event history → fresh request → replaceable provider → untrusted proposal
        ↑                                                        ↓
atomic event + projection ← deterministic governance ← accept / reject
        ↓
portable HTML journal → lab notes → evidence / raw history
```

- `wake/store.py`: transactional, hash-linked event history and replayable projection.
- `wake/governance.py`: explicit actions, evidence requirements, immutable model authority.
- `wake/engine.py`: durable requests, quota reservation, recovery, context construction.
- `wake/providers.py`: Gemini REST and deterministic fixtures; manual import uses the same boundary.
- `wake/report.py`, `wake/assets/`: portable, offline HTML and Markdown reports.
- `wake/experiment.py`: executable 100–1000-cycle experiment.
- `tests/`: failure, governance, provider-contract and audit checks.
- `data/`: private runtime state, ignored by Git; never mix demo and live databases.
- `examples/journal/`: published evidence of the included offline experiment.

Read [architecture and limits](docs/architecture.md), [experiment protocol](docs/experiment.md), or [operations](docs/operations.md) for details. The original research requirements are preserved as [docs/spec.md](docs/spec.md).

## Verify and package

```sh
python3 -m unittest discover -s tests -v
python3 scripts/package.py
```

The replacement ZIP is `dist/wake-scaffold.zip`. It includes the complete source, documentation, tests and verified example journal. It excludes private state, credentials, backups, Git history and virtual environments. Extract into an empty project directory, preserving `.git` if replacing a checkout.

No model is immortal here. The record just has a better filing system.
