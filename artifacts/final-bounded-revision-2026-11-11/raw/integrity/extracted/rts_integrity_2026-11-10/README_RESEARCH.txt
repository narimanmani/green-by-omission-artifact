RTS DEFENSIVE INTEGRITY STUDY — 10 NOVEMBER 2026

Start with deliverables/research_report.html.

WHAT WAS MEASURED
189 formally analyzed local runner invocations:
  76 native Ekstazi invocations (72 comparisons and 4 controls)
   4 supplemental offline Maven integration controls
  49 testmon invocations (45 comparisons and 4 controls)
  60 library-wrapper invocations (45 comparisons and 15 controls)

162 changed-source comparisons: 156 expected assertion-failure completions,
6 explicit testmon runner errors, and zero passing comparisons. No selection
omission was observed in completed runs. Runner errors have an N/A omission
metric. These are finite designed cases, not independent security trials.

20 commit-pinned Apache Commons repository snapshots, 156 configuration files,
and 7 parent POMs were inspected. Two optional Ekstazi profiles were present;
no inspected workflow explicitly mentioned Ekstazi. Actual deployment
prevalence, branch protection, and required CI checks remain unmeasured.

SCOPE
All executable subjects are synthetic fixtures. Five call unmodified released
Java libraries (CLI, CSV, Codec, IO, Lang). No upstream regression suite was run,
and no upstream source or hosted workflow was modified. Generic cache faults
are controlled integrity simulations, not attacker exploits. The guard's
manifest is assumed trusted. No checksum/fingerprint synthesis is included.

REBUILD THE REPORT FROM RECORDED DATA (NO NETWORK)
  python3 analyze_study.py

The script resolves the archived result directory relative to its own location.
Do not edit result JSON/CSV or archived raw logs to change outcomes.

REPRODUCE EXPERIMENTS IN A FRESH DIRECTORY
Use Python 3.12 on Linux x86_64. Java dependencies are pinned, downloaded during
preparation, and hash-checked. Library artifacts, JUnit, and the native Ekstazi
binary are bundled. The roughly 103 MB JDK archive is intentionally omitted.

  python3 reproduce.py --destination /absolute/new/rts_reproduction --component all

Or run a single component:
  python3 reproduce.py --destination /absolute/new/ekstazi_reproduction --component ekstazi
  python3 reproduce.py --destination /absolute/new/wrapper_reproduction --component wrappers
  python3 reproduce.py --destination /absolute/new/testmon_reproduction --component testmon
  python3 reproduce.py --destination /absolute/new/maven_reproduction --component maven

The destination must not exist. This protects historical evidence and avoids
stale report files. Default repetitions are 3 for the main native fixtures and
1 for the five-library pilot. Reproduction creates new raw evidence; it does
not overwrite this report. Maven dependency preparation is a separate online
setup phase. Its four measured integration controls use Maven offline mode.
The principal fault matrix uses the native Java agent, not the Maven plugin.

All cached dependency snapshots in the archive contain ORIGINAL absolute
paths. They are retained as forensic evidence only. Never treat them as a
warmed cache after moving directories; scripts regenerate them cold.

STATIC SAMPLE REPLAY
Audited configuration bytes and parent POMs are included. To download the same
public commit snapshots again, in a COPY of project_sample run:
  python3 audit_repositories.py --manifest frozen_repository_manifest.json

This performs read-only retrieval and runs no repository code. Do not pass
--refresh when reproducing the original sample. The summarizer requires PyYAML
and may retrieve the version-pinned parent POMs. Existing recorded audit totals
are sufficient for offline report regeneration. There is no probability-sample
or general adoption claim.

KEY EVIDENCE
  deliverables/controlled_results.csv and .json — 162 normalized comparison rows
  deliverables/summary.json — audited totals
  deliverables/descriptive_statistics.json — per-cell counts and timing ranges
  deliverables/publication_tables.tex — booktabs LaTeX table fragments
  ekstazi_study/results/<timestamp>/ — frozen plan, native controls, matrix, logs
  ekstazi_study/maven_validation/ — 4 offline Maven controls and fresh XML
  testmon_pilot/derived_results.json — public classifications; runner-error omissions N/A
  testmon_pilot/results.json — preserved original raw-derived collector records
  testmon_pilot/evidence/ — original logs, XML, fault and state records
  project_sample/wrapper_pilot/ — 60 JVM records, logs, trusted snapshots
  project_sample/snapshots/ — exact audited POMs and CI configuration
  methods_review/audit.json — independent evidence audit
  ARTIFACT_SHA256.json — checksum inventory of this archive's payload

NUMERICAL ANALYSIS
Three deterministic repeats establish repeatability, not independent trials.
No p-values, attack-success confidence intervals, or population prevalence
intervals are calculated. Wall times include startup and concurrent local
activity; they are not production performance benchmarks. The guards recovered
diagnostic test execution from testmon's database errors. They did not improve
the measured Ekstazi defect-detection count because standard RTS already
detected all seeded regressions in this corpus.

SETUP HISTORY
Early Maven network/attachment setup failures and initial direct-agent probes
are retained separately where available. The first native harness attempt
stopped on duplicate directory creation before its fault matrix. The corrected
script completed all planned cases. Only the completed formal matrix and
specified controls contribute to the 189 invocation count.

PUBLICATION SCOPE
These data support a reproducible defensive robustness pilot with negative
omission findings. They do not establish an exploitable Ekstazi bypass, real CI
attacker feasibility, complete protection from authenticated provenance, or
representative deployment prevalence.
