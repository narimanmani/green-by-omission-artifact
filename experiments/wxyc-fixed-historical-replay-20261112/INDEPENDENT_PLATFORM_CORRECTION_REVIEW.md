# Separately frozen platform correction review

A v2 study adding the missing original jq prerequisite is scientifically defensible. The failure occurred during the full original baseline, before any candidate observation. It does not justify changing tests, selection, candidate, configuration or scope.

Preserve v1 unchanged. Record the platform-only diagnosis and exact jq/OS-library additions, reverify all original source and Node dependency identities, and use a separately frozen v2 image/results namespace. Run three fresh complete baselines and the same predeclared candidate arms; do not shrink T or reuse v1 caches. Every unsuccessful outcome remains part of the record.

No tests or subject code were run by this auditor. No future positive result is assumed. The JSON review lists the required evidence and controls.

Native-selector fidelity is independently corroborated: NATIVE_JEST_CHANGED_FILES_PRIMARY.js matches the installed manifest SHA-256 43666dbd94179a6bd89daee6010260b15590921f800a63eeef634a2cb4d5bc07. Lines 59-61 union committed, staged and unstaged/modified paths when changedSince is set. The uncommitted frozen candidate is therefore included in native change analysis; no candidate commit, metadata change or altered selection flag is needed. This is static source inspection, not a candidate outcome.
