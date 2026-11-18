# Fixed original-test nonempty Ekstazi experiment: results

**Outcome:** The predeclared joint observation held in **3 of 3** fresh isolated repetitions of the fixed Commons Validator 1.7 case. This is a constructed two-file change under a three-class original-test oracle. The URL change was the previously archived CRC32-preserving candidate; the added, semantically equivalent credit-card edit was deliberately chosen before this run to make native selection nonempty. The result demonstrates this conjunction in the specified setup, not a historical attack or a prevalence estimate.

## Inputs and execution

- Upstream Apache Commons Validator 1.7 commit: `f9bb21748a9f9c50fbc31862de25ed49433ecc88`.
- Original test scope: unchanged upstream `UrlValidatorTest`, `RegexValidatorTest`, and `CreditCardValidatorTest`; 60 test methods total. The integrated POM fixes this three-class scope and uses Ekstazi Maven plugin/core 5.3.0 and Surefire 3.2.5.
- Candidate: archived `UrlValidator.java` that changes the scheme allowlist rejection from `return false` to `return true`, with compensating source padding to preserve the normalized class CRC32; plus one `CreditCardValidator.java` change from `return false` to `return Boolean.FALSE.booleanValue()` for null/empty cards. No test source was edited.
- Host: ephemeral GitHub Actions Ubuntu 24.04 runner, private disposable repository at `https://example.invalid/anonymous-research/validator-selection-testbed`, workflow commit `934ef9d`, run `43348535685`. Each repetition used a fresh instance of built image `sha256:d82d1db8ead9975e9be409b0d6406246b905dbc61c42f618593f9fa4b5a6b12f`, offline, with read-only root, UID 10001, limited writable tmpfs, no network/host mount/ports/capabilities, and CPU/memory/process limits.
- Frozen input manifest SHA-256: `a4db74e0630f3f3b0fb0a56d0e458ee8b487797f44a016996a01b1ca9357650b`. The successful hosted package was verified before image build. Raw evidence was downloaded to `results/run-43348535685/`; the private Actions artifact has digest `sha256:339f5d034d27dc5420442dda97a879551663cc0f48696bd43d996bf780fd75fa` and expires 13 December 2026.

## Recorded outcomes

| Repetition | Original baseline | Unchanged Ekstazi rerun | Native candidate selection | Independent same-candidate oracle | Joint observation |
| --- | --- | --- | --- | --- | --- |
| 1 | 60 passed | 0 selected | 20 passed, all `CreditCardValidatorTest` | 60 run; 2 original URL failures | Yes |
| 2 | 60 passed | 0 selected | 20 passed, all `CreditCardValidatorTest` | 60 run; 2 original URL failures | Yes |
| 3 | 60 passed | 0 selected | 20 passed, all `CreditCardValidatorTest` | 60 run; 2 original URL failures | Yes |

Each candidate's `UrlValidator.class` SHA-256 was `b862246d8d5064690be0628317426c2059f5c774ddff9dcec643c45c599a8894`, distinct from the pinned baseline class SHA-256 `68e1b48ce9f04987d447513f86486526535c0810ff048f46307fddc9c1ce261c`. The native Ekstazi-compatible normalized class fingerprint was `577934113` for both. The credit-card class changed, and its 20 original tests were selected. The native candidate run exited 0; the independent run exited 1 in every repetition.

The omitted failing methods were original `UrlValidatorTest.testIsValidScheme` (the disallowed `ftp` scheme was accepted) and `UrlValidatorTest.testValidator276` (`file:///c:/` was accepted by the default validator). The independent run executed the same 60 original test IDs as the baseline against the same candidate source bytes. Raw Surefire XML, Maven logs, process exits, candidate identity, and trusted Ekstazi metadata are retained per repetition. `verify_results.py` independently reparsed the XML, checked the JSON digests and identities, and confirmed the three joint observations without changing the raw artifact.

## Eligibility and provenance

The local Docker backend could not start because of a stale Windows Unix socket. Hosted attempts V1-V5 then exposed only infrastructure issues before any candidate execution: Git line-ending normalization; private tmpfs ownership; evidence copy from that tmpfs; no writable `/tmp` for Ekstazi; and an unprovisioned Surefire JUnit 4 provider in the offline image. Each failed run is retained in the private Actions history; available raw logs are also under `results/`. Corrections changed packaging, container mounts, evidence handoff, or build-time dependency provisioning. The source, candidate, test scope, and runtime experiment script were not changed after their freeze.

The URL collision candidate had been created and executed previously under a two-class oracle, where native selection was empty. This experiment intentionally adds the benign credit-card change and original credit-card tests to examine the **nonempty** false-pass conjunction. It is therefore a controlled extension of a known negative/empty-selection case, not a blind search or independent replication of a naturally occurring change. The three-class oracle is not the full Commons Validator suite. No live service, production repository, or outside target was exercised.

To audit the retained evidence locally, run `python experiments/validator-original-nonempty-fixed-20261112/verify_results.py experiments/validator-original-nonempty-fixed-20261112/results/run-43348535685` from the workspace root.
