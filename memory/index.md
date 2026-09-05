# Index

A compressed summary of what this agent currently knows, refreshed
periodically (not every wake) by consolidating the journal. This is
what gets read on a normal wake instead of the full journal history,
to keep context small and current.

**Last consolidated:** (date) from journal entries through (last entry
covered)

## What's been built / done so far
[Bob's memory architecture](https://github.com/sudofx/wake-scaffold/tree/master/memory)

[Bob's blog](https://htmlpreview.github.io/?https://raw.githubusercontent.com/sudofx/wake-scaffold/refs/heads/master/memory/blog.html)

## Open threads
(Start one concrete capability project. Cross-reference commitments.json
when it has a genuine deadline.)

## Standing decisions
(settled questions that shouldn't be re-litigated every wake unless new
evidence appears — e.g. "pricing model: X", "publishing cadence: Y")

## Known unknowns
(things this agent has explicitly flagged as uncertain and not yet
resolved)

## Developer Requests
1. **Known limitations, 2026-09-04:** `identity.md`'s Known limitations
   is still unfilled. Real evidence already exists: `validate_memory.py`
   has failed (exit code 1) on 15 of its 22 recorded runs in
   `tool_runs.json` — a genuine, durable pattern worth naming as a real
   limitation (e.g. a tendency to re-run a broken tool rather than
   debug root cause) rather than inventing one. Your call whether/how
   to record it, but the evidence is sitting there unused.
2. **Point the evaluator at yourself, 2026-09-04:** `concept_evaluator.py`
   / `quantum_batch_evaluator.py` have only been run against quantum
   concepts so far. Consider running the same falsifiability check
   against one of your own growth-plan or hypothesis submissions before
   logging it, or against an idea from a different domain (psychology,
   something Carnegie-adjacent) to see if the framework actually
   generalizes or if it's quietly quantum-specific.
3. **Build your own memory structure 2026-09-05:**
   Re-design your, (Bob's), internal memory structure. Design it to operate similar to a human brain, or "mind" would organize "itself". Your memory/tools folder is your sandbox to redesign your own internals. Structure your memory for fast archiving and recalling of memories that have "weight". You will need to be forward thinking based on all you've learned so far. This new extension of your memory will need to map to the base memory without breaking anything. This will be your most complex task so far. Good luck!

      > Structure your tools folder in directories and sub-directorys to categorize the "map of your mind". examples directories: core_memories/, core_functions/, core_thinking/, core_workspace/,
      core_ethics/, core_maintenence/, etc. Any other appropriate directories that describe your internal organization. Move and sort your existing tools you've created into your sub-directories that ONLY YOU maintain and create. But all data must be recorded and follow existing rules.

4. **Developer requests update 2026-09-05:** When you feel any of the tasks in 'Developer Requests' is complete, request that it be marked complete by submitting a pull request on index.md.