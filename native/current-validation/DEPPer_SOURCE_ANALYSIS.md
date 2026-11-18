# pytest-depper 0.2.0: interpretation of the native omission results

This note analyzes the unmodified published plugin source preserved under `native/provenance/pytest_depper_source/` and the native Ubuntu evidence from GitHub Actions run `42429376249`, downloaded under `hosted/current-validation/artifacts/run-42429376249/native-depper-linux-attempt-1/`. It adds no execution, changes no plugin or case source, and makes no GitHub changes. Line numbers below refer to the preserved source snapshots.

## What the native run actually establishes

The Ubuntu run loads `depper-0.2.0` under Python 3.13.18 and pytest 9.0.2. For all three original cases, the default native invocation detects the one changed source file and the changed class/function, then prints `No tests affected by these changes`, marks all three collected tests skipped, and returns success. This occurs for both the ordinary and collision revisions. The full suite executes the security tests and fails on the intended property for both revisions. Baseline and benign full-suite controls pass. `cases/validation.json`, `cases/results.json`, and individual logs preserve these distinctions.

The fallback invocation with `--depper-run-all-on-error` runs all tests when the affected-test set is empty and catches the ordinary and collision regressions. For example, `cases/itsdangerous_expiry/ordinary-native_fallback.log` shows three executed tests with one intended security failure. The default branch reports three tests collected and skipped; this is not the same as testmon's zero-test collection behavior.

These results establish actual native execution of an independent published selector on the original cases. They do **not** demonstrate that preserving CRC32 is what evaded depper: the ordinary regressions are also omitted. Linux reproduction additionally rules out a Windows path-separator mismatch as the sole explanation for these application-case outcomes.

## Installed-distribution names can suppress local dependencies

`DependencyAnalyzer.__init__` caches installed distribution names before building the graph (`analyzer.py:80–86`). `_get_installed_packages` obtains `dist.metadata['Name'].lower()` from `importlib.metadata.distributions()` (`analyzer.py:88–97`).

For an absolute import, `_resolve_import` checks `_is_external_module(parts[0])` and returns an empty dependency set immediately if true (`analyzer.py:197–212`). `_is_external_module` checks installed distribution names **before** checking whether matching files exist in the local project (`analyzer.py:277–299`, specifically `290–296`). Therefore, an installed distribution named `itsdangerous`, `starlette`, or `requests` causes the corresponding absolute imports in these local-copy tests to be classified as external, even though the test interpreter imports the source from the copied project.

The run's `pip-freeze.txt` confirms that all three subject distributions were installed: ItsDangerous 2.2.0, Starlette 0.50.0, and Requests 2.32.5. Those installations are redundant for fixtures that already contain the package source. The preserved full-suite import-origin controls establish that execution used the local source; they do not change the analyzer's separate installed-name heuristic.

This is a source-backed explanation for missing absolute-import edges in the installed-subject environment. A matched run without those three installed distributions, while retaining their required dependencies and identical local source/tests, is the appropriate causal control. Removing redundant installations changes the analysis environment; it does not repair or modify the selector. The original installed-environment outcomes should remain in the report rather than being discarded.

## A second limitation: direct symbol matching bypasses transitive analysis

The plugin switches to symbol-level analysis whenever Git yields any changed symbols (`plugin.py:108–114`). All three logs show nonempty changed symbols. `git_utils.py:116–138` maps a changed line to the first enclosing function/class encountered during AST traversal, explaining the recorded class names for method changes.

`get_affected_tests_by_symbols` iterates **test files** and only considers a test if the exact changed source file is a key in that test's own direct `symbol_imports` mapping (`analyzer.py:424–463`, especially `445–461`). It then matches an imported wildcard or an intersecting symbol name. This function does not follow reexports or transitive imports. In contrast, the file-level API traverses reverse dependencies (`analyzer.py:386–422`), but `plugin.py:108–114` does not union that result with the nonempty-symbol case.

The exact fixture imports predict different outcomes after redundant subject installations are removed:

| Case | Recorded changed file and symbol | How the unchanged test imports the application | Source-based prediction in the clean-subject Linux environment |
| --- | --- | --- | --- |
| ItsDangerous | `itsdangerous/timed.py`, `TimestampSigner` | `from itsdangerous import TimestampSigner, SignatureExpired` | The test directly imports the package initializer, so the exact changed-file key is absent from its direct symbol map. A reexport/transitive propagation omission can remain. |
| Starlette | `starlette/middleware/trustedhost.py`, `TrustedHostMiddleware` | `from starlette.middleware.trustedhost import TrustedHostMiddleware` | The direct path and symbol match, so the security test file should be selected if other controls are valid. |
| Requests | `requests/utils.py`, `_validate_header_part` | `import requests` and `from requests.exceptions import InvalidHeader` | The test does not directly import `requests/utils.py` or `_validate_header_part`; a transitive propagation omission can remain. |

These are predictions from source, not results of the additional native control. Its results must be recorded separately before making a causal conclusion about each case. Even if the predictions hold, both ordinary and collision variants should have the same depper outcome for a given import topology; the collision construction is not necessary for these omissions.

## Fallback behavior and reporting boundaries

When no affected tests are found, `plugin.py:116–125` either returns without filtering under `--depper-run-all-on-error`, or marks every item skipped by default. The native fallback results therefore provide a meaningful control: executing the tests catches the intended failures. No analyzer exception is required to trigger this fallback; an empty affected set is sufficient. The option's name should not be interpreted as protecting every unsafe selection result, since it acts only on the conditions implemented in the plugin.

The defensible report separates three claims:

1. **Native published-selector execution:** established by actual depper 0.2.0 runs, selected/skipped/executed test records, version evidence, clean Git histories, and full-suite controls.
2. **Observed omission under the measured environment:** established for ordinary and collision revisions in the installed-subject Ubuntu environment; the causal role of installed-package classification and direct-only symbol propagation should be evaluated with the matched clean environment.
3. **Generalization of the CRC32-preserving attack mechanism:** not established by depper. Its graph/symbol selection logic does not compare testmon's CRC32 fingerprints, and ordinary changes already exhibit the same omission in this environment.

A paper may discuss independent selection-safety limitations if confirmed and carefully scoped, but should not present these outcomes as the same checksum attack defeating another fingerprint implementation. Report the matched clean-environment outcomes beside the original results, state the ordinary-control behavior prominently, and avoid an across-selectors vulnerability-rate claim.
