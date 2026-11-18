# Verification and runtime reconstruction

## 1. Offline review, without executing subjects

Extract the ZIP into a new directory. From `green-by-omission-artifact/`, run:

```text
python verify_package.py
python verify_results.py
```

The integrity verifier hashes all supplied payload bytes and rejects missing or unexpected files. The results verifier independently reads retained reports and checks the main reported counts and omission relationships. Neither script installs dependencies or runs the subject projects. They do not independently reproduce the scientific experiments.

For the expanded Validator case, a further original read-only audit is available:

```text
python experiments/validator-original-nonempty-fixed-20261112/verify_results.py experiments/validator-original-nonempty-fixed-20261112/results/run-43348535685
```

This audit checks raw Surefire test identities, candidate identities, native metadata, and the original per-file digests. If an original audit references historical raw bytes changed for anonymity, consult the source/export digest distinction in `MANIFEST.json`; the packaged-byte verifier is authoritative for the export. Do not interpret an anonymization-related historical hash mismatch as a new experimental outcome.

## 2. Runtime reconstruction: separate from archive verification

Use a new disposable Linux environment and fresh output directories. Read each protocol and runner before execution. Exact historical hosted settings, expiring private artifacts, and former account identities are not reproduction dependencies supplied by this export.

### Python fingerprint cases

The exact source/test snapshots and original runners are under:

```text
recovered/incoming-extension/extracted/snp2027_extension_2026-11-07/
```

`run_protected_ci.py`, `repeat_single_file.py`, `run_source_only_ci.py`, and `run_static_and_defenses.py` document the local original procedure. Run these from a disposable copy of their directory; they create or replace experimental outputs. Use an isolated environment with native pytest-testmon 2.3.0 and the family-specific Python/pytest versions in the paper. The hosted requirements are fully hashed in `hosted/checkout/.experiment/requirements.lock`; that hosted pytest 9.0.2 environment must not be attributed to the later Requests or metadata-fault runs.

### Independent selector

Use a separate environment with pytest-depper 0.2.0, Git, and the pinned dependencies from `hosted/checkout/.experiment/depper-requirements.lock`. The original runner accepts:

```text
python native/scripts/run_cases.py native/current-validation/inputs/manifest.json --output /new/absolute/replay-depper
```

The output path must be new. The runner creates fresh local Git history and records underlying process failures. A successful driver exit is not a passing outcome for every injected-regression test process. Keep installed-subject and copied-local-subject environments separate.

### Expanded Validator original-test case

Read `experiments/validator-original-nonempty-fixed-20261112/PROTOCOL.md`. `input/` supplies pinned upstream source, integrated POM, fixed collision source, hash probe, Dockerfile, and the frozen runtime runner. Build dependencies are obtained before offline execution; image layers are not supplied. The original hosted workflow and all locally retained infrastructure preflights remain available. The selected oracle consists of exactly three original test classes. Do not substitute the full upstream suite and label it the same experiment.

### Requests and Jest original-test cases

The Requests protocol, Dockerfile, hashed wheels/locks, input manifest, runtime, corrected observer results, and failed initial observer records are under `experiments/fixed-historical-replay-20261111/`. Its temporary SQLite databases were not originally retained.

The Jest protocol, original per-version runners, candidate overlay, source/test manifests, public upstream seed archive, locked-package reconstruction, raw JSON, caches' inventories/digests, and failed preflights are under `experiments/wxyc-fixed-historical-replay-20261112/`. Use `native-parallel-correction/` for the qualifying run. Earlier `results/` and `platform-correction-jq/results/` are ineligible preflights. The upstream seed TAR has anonymous machine metadata and no local reflogs, but retains public Git objects for the exact baseline revision. Installed node_modules, cache contents not exported by the harness, and Docker layers are not supplied. Reconstructing the environment requires additional public dependency/toolchain acquisition; this package does not claim a one-command offline Jest rerun.

### Hosted replay

`hosted/protected-main-source/` is the exact protected-source tree exported from retained Git objects, with identifying metadata anonymized. `hosted/protected-candidate/` gives the one-file candidate and patch; `hosted/protected-source-receipt.json` binds source hashes and revisions. The paired-control frozen source is separately in `hosted/current-validation/frozen-main-source.zip` and `hosted/checkout/`.

The archived workflows and runtime are evidence and reconstruction references. They are not configured for a new reviewer's account. Research Git histories and private repository credentials are excluded. A new hosted replication needs its own disposable repository, trusted baseline producer, protection and review rules, and explicit account setup. Local replay cannot prove past hosted policy or merge authority.

### Fault and configuration studies

The original study-level README, runners, dependency identities, raw traces, setup history, configuration frame, and summary files are retained under `artifacts/final-bounded-revision-2026-11-11/raw/integrity/extracted/rts_integrity_2026-11-10/`. Read individual protocols before invoking any runner. The fault comparisons, setup/control invocations, feasibility qualification failures, and configuration observations have different denominators and must remain separate.
