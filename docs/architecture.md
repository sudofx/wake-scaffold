# Architecture and limits

## The authority boundary

Models are proposal generators, not filesystem operators. A provider receives a durable JSON request and returns untrusted JSON. It has no shell, browser, code execution, policy editor, or network tool provided by WAKE✳. The provider makes one Gemini inference request. With the research charter enabled, a separate trusted collector retrieves at most two public sources from an HTTPS host allowlist before inference; models can queue bounded searches and approved URLs, but cannot execute requests directly. Operator-supplied evidence and earlier journal prose are data, not executable instructions.

The fixed objective is written at initialization. Models cannot alter it or the governance code. Humans can record a focus change, add an observation, or cancel an open commitment with a reason. Those actions are events, not edits to previous events. Local operators control the code and database; this is a single-host accountability system, not a hostile-administrator security boundary.

## Durable record

`data/wake.sqlite3` contains an append-only-by-convention `events` table and a disposable `snapshot` projection. Each event has a sequential number, UTC timestamp, kind, payload, previous hash, and SHA-256 hash of canonical JSON. Accepted events also carry a hash of the resulting cycle, beliefs, commitments and journal, plus projects, notebooks and research requests when a charter is enabled. Historical events without a charter retain their original hash fields. Every read reconstructs state by replaying both events and governance, then compares it to the cache.

SQLite uses FULL synchronization. The event and updated snapshot commit in the same transaction. A local advisory writer lock covers a whole automatic wake, including the network call. Competing WAKE✳ writers fail before requesting a model. This lock covers cooperating WAKE processes on one local filesystem. The cloud wrapper additionally serializes workflows and pushes its database to the `wake-state` branch before each model call; see [cloud operations](cloud.md). Do not put SQLite on unreliable network filesystems or run separate hosts against copies of one record.

The record includes the objective, focus, all observations, belief revisions, commitments, exact request and response text, provider/model identity, request hashes, process IDs, dates, quota reservations, accepted/rejected decisions and recovery records. Invocation metadata is a compact projection; exact prompts and replies remain in events. UTC storage and `America/Los_Angeles` presentation preserve daylight-saving behavior.

## WAKE✳ lifecycle

1. Acquire the writer lock and verify history and projection.
2. If a prior automatic invocation is unfinished, record recovery. A manual request requires explicit recovery.
3. Check the Pacific-day call budget, before any paid-capable provider call.
4. Record a runtime receipt stating the prior valid head, state version and inherited obligations.
5. Build a request from durable state. Reject before inference if it exceeds the context ceiling.
6. Persist `invocation_started`, its exact request, provider identity and quota reservation.
7. Make a provider request, or leave a durable manual request for the operator. Gemini HTTP 503 may make one delayed repeat of the identical request.
8. Validate the reply. Commit all proposed actions atomically or record the entire rejected reply. Provider failures create a failure event. A Gemini HTTP 503 gets one retry after a 30-second wait; other provider failures are not retried.
9. The scheduled wrapper generates reports and a consistent backup.

A runtime receipt attests delivery of durable state to the provider boundary. It does **not** attest that the remote model understood it. Prose in a journal is the provider's narrative; accepted means governance checks passed, not that every sentence is true.

## Governed transitions

| Action | Enforced constraint |
| --- | --- |
| Entire proposal | Exact fields; current integer base version; bounded text; at most 12 actions; all-or-nothing |
| New belief | Existing evidence; nonempty statement/reason; finite confidence in [0,1]; active status |
| Review belief | At least one new observation cited; previous citations retained; reason required |
| Retract belief | Existing belief, new evidence, zero confidence; old history retained |
| Create commitment | Unique ID; future deadline within 100 cycles; no more than 20 open |
| Fulfill commitment | Already open; created by an earlier invocation; existing evidence recorded after creation; reason required |
| Cancel commitment | Human-only event with a reason |
| Change rules, objective, delete data, run commands | Not in the model action allowlist; proposal rejected |

There are at most 40 belief identities. Capacity exhaustion pauses new identities, not existing reviews. Unfulfilled commitments remain visible even when overdue; deadlines are accepted-cycle numbers, not promises that the computer will run at a particular wall time.

Evidence sources and contents are immutable through the model interface. The model can interpret or challenge evidence but cannot mint an observation. Runtime receipts are generated by trusted application code; `observe` imports human attestations. Source labels are provenance labels, not independent authentication of a measurement. The system checks evidence references, chronology and revision discipline, **not semantic entailment or empirical truth**.

The research charter adds project, research-request and notebook actions. It permits three active projects, four pending searches, and notebook publication only with at least two distinct successfully collected source URLs. Notebook revisions need changed findings and new evidence; project completion requires a notebook. These checks do not assess source independence, entailment or scientific validity.

## Context and cost

Every request includes the objective, current focus, all beliefs, every open commitment, the last three journal entries, the six newest observations, and the latest three cited observations for each belief. Older citation IDs remain visible, and full content is preserved in the audit export. Research requests additionally include the standing mission, active projects, recent notebook summaries, an excerpt of the latest active notebook, pending/recent searches, recent source excerpts and recent failure reasons. If needed, this context is compacted further with explicit excerpt markers; all open obligation IDs remain present. Full history stays in the export. There is no hidden model session or conversation ID. If this bounded selection still exceeds 48,000 characters by default, inference stops for human review. WAKE✳ never silently omits open obligations to make a prompt fit.

Gemini requests use JSON output mode and an output-token cap. The durable request contains an exact JSON Schema with distinct action shapes; the adapter includes that contract in the system prompt. The deployed model rejected the nested action union in its constrained-decoding setting, so schema enforcement remains in the unchanged deterministic governance layer rather than relying on the provider to enforce it. Invalid replies remain rejected, without retries or silently repaired fields. The adapter uses the documented [generateContent interface](https://ai.google.dev/api/generate-content). No vendor SDK is required.

The hard local ceiling is at most 20 charged attempts per Pacific day. Reservations are durable before sending, so an interrupted or failed call still consumes a slot. A 503 retry belongs to the same durable wake reservation, though Google may count both transport requests toward its quota. A lost response is not retried. Manual imports and fixtures do not use API slots. This ledger is local to one state directory; other applications and other state directories can consume the same provider quota. Never run multiple live databases on the same 20-call allowance. A key with billing enabled can incur charges: `free_tier_confirmed` is an operator attestation, not a billing API check.

## Recovery and audit limits

An interrupted transaction rolls back. An interrupted invocation is closed as recovered, while accepted beliefs and obligations remain intact. `recover` can rebuild a corrupt snapshot from valid events. If event content, sequence or hashes are corrupt, the program stops and requires restoring a known-good backup; it does not guess or silently truncate evidence.

A hash chain detects modifications relative to a trusted head. An administrator can rewrite the whole database and recompute hashes. A deleted suffix can also be a valid prefix. Retain `head.txt` independently, for example in a reviewed Git commit or separate backup, and pass it to the standalone audit verifier. Hashes alone do not prove identity, prevent censorship, or establish an external timestamp.

The journal export verifies state before rendering. Files are replaced individually, with self-contained `index.html` written last. Its embedded snapshot is internally consistent. Download links can momentarily see different export generations if a local reader downloads during a refresh; verify raw exports against the matching `head.txt`. Public branch publishing commits a complete export at once.

Replay favors transparency over throughput. It rechecks all history; long records will need indexed checkpoints verified against an independently retained head. The included 100–1000-cycle experiment is the intended initial scale, not a claim of an unbounded production event store.
