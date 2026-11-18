# SP2027 bounded exposure-audit pilot — observed results

## Scope, denominator, and validity

The sampling frame was frozen before selector-code inspection. It contains the first 60 **GitHub search-ranked** active-ish, 100–500-star Python repositories and first 60 comparable Java repositories. A deterministic FNV-1a key selected 12 of each. Search relevance ranking introduces selection bias, so this is **not representative of GitHub projects** and is not a population-prevalence estimate.

**24/24 selected repositories** had a readable default-branch tree and completed a repository-scoped indexed-code search for their language's named selector (`testmon` for Python or `ekstazi` for Java). **0/24 yielded an indexed match** for that literal selector term. This means *no observed indexed explicit selector reference in this convenience sample* — it does **not** prove the tools are absent from dependency caches, external reusable workflows, unavailable branches, or hidden settings. Among the 24 sampled repositories, 19 have `.github/workflows` YAML files, 12 have files in recognized test directory patterns, and all 24 have at least some source files by extension. The test-directory heuristic can miss alternate test layouts.

Neither the selection algorithm nor these source searches can verify the required status checks configured in branch protection, because that setting requires separate permission-controlled API/UI evidence. Record status as **unknown**, not false.

## Explicit positive deployment examples — not in sample denominator

1. `ansys/pyaedt` uses `pytest-testmon` in documented and committed CI paths `.github/workflows/ci_cd.yml`, `.github/workflows/update-testmondata-cache.yml`, `.github/actions/testmon-cache/action.yml`, and declares dependency in `pyproject.toml`. This is code-level deployment evidence only. Required check and independent exploitability remain unverified.
2. `axolotl-ai-cloud/axolotl` uses testmon in `.github/workflows/testmon-cpu.yml`, baseline-related workflows, `cicd/pytest_testmon.py`, and cache scripts. This is code-level deployment evidence only, not a finding that its CI can be exploited.

## Interpretation

The negative convenience sample plus independently observed positive deployments demonstrates that the audit pipeline can distinguish selected repository nonmatches from confirmed external usage. It does **not** support a numeric estimate of GitHub-wide exposed CI installations or attacks in the wild. A follow-up requires a probability sample of an explicitly defined population, de-duplicated app and fork metadata, complete workflow discovery, manual configuration review, branch-policy verification where authorized, and uncertainty by repository.

Frozen source records: `sampling_frame.json`, `python_batch_1..3.json`, `java_batch_1..3.json`.
