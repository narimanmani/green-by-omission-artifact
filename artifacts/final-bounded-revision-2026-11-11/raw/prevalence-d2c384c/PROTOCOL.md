# SP2027 bounded repository exposure audit — frozen before inspection

Date: 2026-11-09 Pacific; first collection at fixed GitHub Search page 1, per_page=60.

Two **search-ranked** frames, NOT representative of all GitHub repositories:
- Python search: `language:Python stars:100..500 pushed:>2026-05-01 fork:false archived:false`
- Java search: `language:Java stars:100..500 pushed:>2026-05-01 fork:false archived:false`

For each language, collect the first 60 results from GitHub repository search (default relevance ordering). Compute unsigned FNV-1a 32-bit of the literal string `SP2027_20261109_` followed by repository full name. Sort ascending, select the first 12 distinct repositories for inspection. Ties sorted by repository full name. Freeze complete frame and selected set in `sampling_frame.json` before auditing.

Inspect ONLY current default-branch files as returned by GitHub API. For each selected repository, search matching repository code for both tool strings (`testmon` and `ekstazi`) and retrieve relevant `.github/workflows` / `pom.xml` when evidence exists. Classify `confirmed_native_CI`, `reference_or_dependency_only`, `no_indexed_evidence`, `ineligible_nonsoftware`, or `inconclusive_api`. Classify **required branch-protection** `unknown` unless separately accessible and verified; CODEOWNERS/config cannot establish a required gate.

Report denominator of successfully inspected sampled repositories, plus number of uninspected and ineligible. Do not extrapolate this **biased search-result sample** to GitHub overall. This is an audit feasibility pilot, not a population prevalence estimate.

No code execution in external repositories; no upstream PRs, no security scanning of live deployment endpoints. Existing Commons Validator 1.7 isolated code execution is separately recorded.
