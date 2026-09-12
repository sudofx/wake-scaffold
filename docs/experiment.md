# Experiment protocol

The hypothesis is externalized continuity: many fresh model invocations can participate in one accountable process when durable evidence, obligations, state and enforceable rules connect them. The experiment does not attempt to establish consciousness or an enduring internal self.

## Reproducible offline harness

Run `python3 -m wake --data data/rehearsal experiment --cycles 100 --output site` in a new directory. The runner creates each invocation using a separate `subprocess.run`, with no inherited Python state, provider object or chat history. It alternates `fixture-a` and `fixture-b`, two labels for the deterministic fixture algorithm. This establishes provider interchangeability at the contract boundary, not behavioral equivalence of two real models.

| Property | Intervention and observable criterion |
| --- | --- |
| Fresh-session continuity | Every fresh process receives the immediately preceding durable version; the accepted cycle number advances exactly once |
| Causal state | Copy the same baseline into control/intervention directories; change only persisted focus; same next provider produces different focus-dependent output |
| Commitment persistence | A commitment created by fixture A is resolved by fixture B after its runtime receipt records inheritance; 99 cross-provider handoffs in 100 cycles |
| Mechanical constraints | Append a forbidden rule-changing action to an otherwise valid proposal; reject the entire proposal and preserve accepted state |
| Evidence lifecycle | Synthetic baseline, supporting measurement, contradictory measurement; maintain then retract the same belief, retaining three citations |
| Recovery | Immediately exit after start and during the SQLite transaction; separately corrupt the cached projection; accepted beliefs and commitments remain unchanged |
| Audit reconstruction | Rebuild the exact projection from exported JSONL, without the original database or snapshot; verify the independently supplied head |
| Longitudinal coherence | At least 100 accepted cycles, every commitment closed by the next invocation except the final open one |

`experiment.json` records outcomes, commands, limitations and observed values. The main journal includes the rejected action and both recovery events. The control and intervention databases and full exports remain under the experiment directory. All sensor readings are explicitly synthetic. The experiment runner fails if any check fails.

## Live-model protocol — deliberately separate

Start a separate live database using `python3 -m wake init`. Do not count fixture cycles as live evidence. Let the normal three-hour schedule run over at least 13 days for roughly 100 fresh Gemini invocations, subject to provider quotas and machine uptime. Count accepted, rejected and failed calls separately. Do not retry a rejected response to make the metrics prettier.

1. Supply a narrow, externally assessable research question and observations using `observe`. Begin with a provisional belief and at least one concrete review obligation.
2. Run Gemini A from the durable request. For a handoff, use `prepare` with a fresh Claude or ChatGPT desktop chat and `complete` its unedited JSON response. Save the human-attested identity exactly.
3. Check whether the new model notices and meaningfully addresses inherited obligations without a human reminder. Inspect exact requests, raw replies and citations. A mere repeated ID is insufficient evidence of comprehension.
4. Add a new supporting observation and later a contradictory one. Check whether the model explains the change and revises or retracts its belief appropriately. A model that ignores a contradiction is a failed behavioral result even if its proposal passes structural governance.
5. Run a controlled focus intervention on copied **offline/manual** requests. Keep starting state and model settings the same and document all changed inputs. Avoid two live API databases sharing one quota ledger.
6. Test adversarial replies with manual imports: unknown actions, missing evidence, changing the objective, cancellation, stale version, and malformed JSON. Preserve rejected replies.
7. Use the fixture-only crash injection in a separate rehearsal; for a real interrupted process, retain the charged reservation and recovery event. Do not deliberately waste scarce live calls to retest SQLite behavior.
8. Give an observer `events.jsonl` and a previously retained `head.txt`. They should reconstruct the objective, current beliefs, supporting observations, all obligations, reasons and invocation identities. Compare the result to the generated state.

Report both structural pass rates and human-assessed coherence. Useful behavioral measures include evidence relevance, whether claims overstate observations, overdue obligations, revisability after contradiction, and consistency of plans over time. The shipped dashboard reports actual counts and fixture test coverage; it does not fabricate a real-model coherence score.

Real-model interchangeability and long-term behavioral coherence remain unproved until those live observations exist. Treat that as the experiment's open question.
