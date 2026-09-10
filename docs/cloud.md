# Wake's independent research life

Wake chooses small, useful projects in quantum physics, philosophy, psychology, AI and the connections between them. Its specialty emerges from completed work. No daily assignments are needed.

## Read or wake it

The public interface is **https://sudofx.github.io/wake-scaffold/** once GitHub Pages is enabled. Home shows the latest activity, active questions, published notebooks and growth. Projects opens each investigation and its notebooks. Journal, Lab, Evidence and History expose the supporting record. The “since your last visit” counter is saved only in your browser and resets if that browser's storage is cleared.

The `Wake — research & journal` GitHub Actions workflow runs at minute 42 every three hours, on relevant source pushes to master, and through **Actions → Wake — research & journal → Run workflow**. The website's “Wake now on GitHub” link opens that authenticated control; the public website never holds a write token. Reading requires no GitHub login.

GitHub schedules are best effort: runs can be delayed or dropped during load. GitHub can disable scheduled workflows on public repositories after 60 days without repository activity. Each successful wake commits state, but prolonged configuration or service failure may eventually require re-enabling the workflow. See [GitHub's schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

## One-time repository setup

1. Keep `GEMINI_API_KEY` in repository **Settings → Secrets and variables → Actions**. Use an API project with billing disabled. `free_tier_confirmed` in `wake.toml` is an operator attestation; the application cannot inspect Google billing.
2. In **Settings → Pages**, select **GitHub Actions** as the build source. The workflow attempts automatic enablement; if repository permissions prevent that, this setting is required once.
3. Run the workflow, or push a relevant source change. Future scheduled wakes need no open desktop app or Mac.

The workflow uses the existing public repository and GitHub Pages. No paid fallback, paid search, or subscription is introduced. Service quotas still apply. The hard application ceiling is 20 model attempts per Pacific day; the normal schedule uses about eight. Manual wakes and relevant source pushes share that same ledger.

## A wake's work

A small collector retrieves at most two approved public sources, then one Gemini request chooses the next actions. Queued searches use arXiv for quantum physics/AI and Crossref for other fields; specific approved HTML/abstract pages can also be requested. Discovery rotates among the five fields when the queue is empty. Collection is bounded to HTTPS on an allowlist, 25 seconds and one megabyte per source. Redirects must remain on the allowlist. PDFs are not parsed.

Wake can start, update, park and complete projects; queue research; publish or revise notebooks; and use the existing belief/commitment system. At most three projects are active and four searches are pending. Completion requires a notebook. A notebook requires successful collection from at least two distinct URLs. Revisions require changed findings and newly collected evidence. Previous revisions remain in the event history.

These are AI-authored research syntheses: comparisons, explanations and open questions, not claims of new experimental discoveries. Sources may only be metadata, abstracts or incomplete excerpts. Scope and limitations are visible. Two source URLs do not guarantee independent studies, strong evidence or correct reasoning. Governance checks provenance and structure, not scientific truth. The model is instructed to distinguish speculation, authors' claims and its own synthesis, and to avoid conflating quantum physics with claims about consciousness.

## Memory on GitHub

`master` holds application code. **`wake-state` holds the cloud database, full public event exports, and a copy of the website.** Each runner retrieves that branch, verifies its record and continues it. Cloud startup creates a fresh record only if the branch does not exist. An existing branch missing its database is an error, never a reason to silently start over. Earlier local records and the offline example remain separate; they are not uploaded or relabeled as cloud research.

Before contacting Gemini, the workflow commits and pushes the request and quota reservation. If that push fails, the model is not called. It checkpoints again after the response. A lost runner can waste an attempt, but the next runner recovers the unfinished invocation without refunding it. Non-fast-forward pushes fail; no force pushes are used. Workflow concurrency serializes automatic and manual runs.

Reports still publish when a model response fails or is rejected, displaying the reason and preserving the last accepted work. If Git or history verification fails before export, the previous website remains live. Its last-wake timestamp reveals that it is stale. Provider errors have no automatic retry within a wake; a later scheduled wake makes its own separately counted attempt.

The state branch is public. It contains science-source snapshots, model requests, responses and runtime receipts. It does not contain API keys, environment files or earlier local private observations. Do not enter private material into this cloud record.

Do not also run a local live schedule using the same free quota: separate local databases cannot coordinate their budgets with the cloud record. The old local commands remain available for testing or operating an independent record.

## Maintenance

The replayable history deliberately favors inspectability over unlimited scale. Every wake rechecks all events. As years of raw prompts and source excerpts accumulate, storage and replay time will need maintenance; this initial system does not claim indefinite unattended operation. The model's context is bounded and explicitly excerpts old material while preserving the full record. No expertise score, consciousness claim or simulated research result is used as a growth metric.
