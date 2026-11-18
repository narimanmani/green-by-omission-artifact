# Independent v1 baseline verdict

**Ineligible baseline; no candidate observation.** Raw export audit: 28/28 checks pass.

All 471 original unit files ran: 8,169 cases passed and four failed, out of 8,173. The original security-source guard passed. The four failures all concern scripts/resolve-cron-schedule.sh exit status: expected 0, observed 127. The missing-target branch, which exits before jq, passed. The unchanged script unconditionally calls jq at line 41, and the saved OS-package inventory lacks jq and its libraries. This strongly supports a missing platform utility. The test catches child stderr, so the raw Jest log does not literally print jq-not-found.

Original source/config/lock/test hashes and every installed dependency entry remained unchanged before and after the baseline. No candidate was applied; no selective/full candidate arm ran. The guard pass cannot be combined with another case to manufacture the missing joint observation. V1 planned three repetitions but completed only this first ineligible baseline at the audit point.

The original v1 freeze, image and raw result must remain preserved. See the JSON verdict for independent envelope, case-count, source/dependency, cache and actual-boundary checks. No tests were rerun by this auditor.
