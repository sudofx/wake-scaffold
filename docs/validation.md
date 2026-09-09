# Rebuild validation

Executed September 9, 2026 on macOS with Python 3.14.7.

| Check | Result |
| --- | --- |
| Behavioral test suite | 25 tests passed |
| Offline longitudinal experiment | 100 accepted cycles; all eight checks passed |
| Cross-provider fixture handoffs | 99 completed obligations; one remains open for cycle 101 |
| Forbidden rule change | Entire proposal rejected; accepted state unchanged |
| Process recovery | After-start exit and mid-transaction exit recovered; corrupt projection rebuilt |
| Independent reconstruction | Exported JSONL reconstructs the exact durable state |
| API calls during validation | Zero real inference calls; Gemini HTTP contract tested with a stub |
| Browser interactions | Search, pagination, entry disclosure, evidence deep links, event filtering and lab results verified |
| Responsive widths | 375px phone, 768px tablet, 1440px desktop; no horizontal overflow after chart correction |
| Browser console | No errors or warnings in the final inspected page |
| Publishing | Initial publication, unchanged publication and update tested against a disposable local Git remote; no public push |
| Replacement ZIP | Extracted to a clean temporary folder; initialize, fixture wake, audit, export and included 100-cycle audit passed |

The observed experiment is included in `examples/journal/experiment.json`. Its durable head is `4c5f205afe0060e30bf71b9b7e807c99001501dd21dbe16d1206995aa9cc1aad`.

The GitHub workflow is configured to run on Python 3.11 and 3.13; those remote jobs have not been run as part of this local rebuild. Live Gemini inference, free-tier account eligibility, real desktop-model handoffs, cron installation and public hosting remain operator setup steps. The synthetic experiment does not establish live-model comprehension.
