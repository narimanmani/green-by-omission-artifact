# Independent offline protocol review

**Static review passes: 37/37 checks; no open material findings.** An eligible installed seed and the final execution freeze remain mandatory prerequisites. No subject code, tests, installs or harness were run by this auditor.

The reviewed runner validates original source/test/config/lock bytes, complete installed dependency identities and relative workspace links across arms. It requires a passing full baseline and target guard, an actual nonempty original native pass, the unchanged target expectation failing in the same candidate under complete execution, and absence of that guard from native actual calls. Setup/runtime failures, skips, empty passes, missing exports and outer-container errors cannot qualify.

The host uses an unstarted container from the immutable seed ID for final assembly and binds parent/layers, infrastructure hashes and its own script hash. The planned execution has no network, host mounts or credentials, a read-only root, dropped capabilities and resource limits. Native addons may execute in private /work tmpfs; /tmp is noexec. Actual inspect/runtime checks still must pass before and during execution.

Raw Jest JSON/stdout/stderr are embedded in the hash-bound export. Coverage and cache artifacts have complete file/hash inventories; their binary contents are not embedded. No outcome is established by this review. The measure is an original static security-source guard, not runtime CSRF, fingerprint collision, production prevalence or hosted contributor evidence.

Reviewed hashes:

- lab.py: 3c697cef5a884796dac5e0ed42a4b4f93bac60a19c46490a8dc9de585a286601
- run_replay.mjs: c6703dcc746d645beb7ee383c6824ffeb31e8ba718a1c965ad0dd67f0188bc77
- PROTOCOL_PREDECLARATION.json: 0ea6b3251f51177b07358af2be2acffe300584c5be30996821c2dca71f386300

Resolved pre-execution issues and all static evidence checks are detailed in INDEPENDENT_PROTOCOL_REVIEW.json. Repetitions must run sequentially, with all unsuccessful evidence retained.
