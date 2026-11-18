# Ekstazi 5.3.0 binary inspection

Basis: direct static inspection of a published binary. This is not an execution result and does not show that any test was omitted.

## Artifact identity

- Coordinates: `org.ekstazi:org.ekstazi.core:5.3.0`
- Local artifact: `../toolchain/org.ekstazi.core-5.3.0.jar`
- Size: 173884 bytes
- SHA-256: `baf7affe8fc42e12b382ec933f3572fce417e5e0d9a7ebab2902bc5c614cb749`
- Inspection command: JDK 8 `javap -classpath <jar> -c -p <class>`
- Saved evidence: the six `.txt` class disassemblies in `binary_inspection/`.

The accompanying published sources JAR was 2117 bytes with SHA-256 `27c44e0d2f54703fa8e3b250ba6dc03dbb4130598b8cbe27b56d4bf1d6dfa433`. It contained no `.java` files. Source-JAR presence was therefore not treated as source-code availability.

## Findings and bounded predictions

| Static observation | Evidence location | Prediction to check experimentally |
| --- | --- | --- |
| Configuration initializes dependency format to `BIN` | `Config` static initializer and `createStorer()` | Default runs use `BinStorer` unless overridden |
| `BinStorer` inherits from `PrefixTxtStorer`, which inherits the text loader | `BinStorer` and `PrefixTxtStorer` class signatures | Loader-level error handling is shared with `TxtStorer` |
| Missing input stream returns an empty dependency set | `Storer.load(FileInputStream)` | Missing per-test state should be handled conservatively |
| Empty files and wrong initial format marker do not populate the returned set | `TxtStorer.extendedLoad()` and `isMagicCorrect()` | Empty or bad-header metadata should cause reruns through the empty-set rule |
| A caught parsing exception clears the accumulated set before return | `TxtStorer.extendedLoad()` exception handler | Some malformed/truncated records should cause reruns through the empty-set rule |
| Ordinary end-of-file returns accumulated entries; no separate total-record count is checked in this loader | `TxtStorer.extendedLoad()` loop and return path | A fixed truncation can produce different outcomes depending on where EOF lands; direct observation is required |
| A null or empty dependency set is considered affected | `DependencyAnalyzer.isAffected(Set)` | Missing/empty state is expected to select the associated test |

These observations do not establish a real-world attack. They do not establish metadata write permissions, trusted-cache exposure, CI reachability, or the feasibility of causing a particular incomplete record. No checksums were modified or constructed in this inspection. Fault positions should remain fixed before outcomes are observed.

## Configuration and integration caveats

The class behavior above is one layer. Native Maven execution can add controls, test-discovery behavior, cached decisions, prior-failure handling, and instrumentation concerns. A result should therefore cite both the exact artifact and the observed test execution records, rather than infer end-to-end behavior solely from bytecode.

The integrity defense also requires a complete, trusted original dependency snapshot. Content authentication alone cannot establish that this original snapshot captured every semantically relevant dependency.
