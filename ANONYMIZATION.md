# Anonymous export and hash semantics

The original research records remain unchanged outside this export. The upload package replaces researcher names, researcher account identifiers and email addresses, private repository URLs, account avatar identifiers, and personal workstation prefixes. Labels distinguish owner and contributor roles without claiming independent operators. Research Git histories/bundles, private maintainer correspondence, editor history, screenshots of authenticated account pages, credentials, and the private export script are excluded.

Public upstream repository names, author and maintainer attribution, original test names, upstream revision identities, licenses, package locks, candidate source bytes, and scientific outcomes are preserved. Subject test fixtures can contain illustrative addresses, secrets, or names belonging to upstream test data; these are not uploader credentials. Technical repetition and condition labels are preserved so records can be joined.

Nested ZIP/TAR payloads are inspected recursively. The Jest upstream baseline seed retains public Git objects/index/references needed to recognize its exact public baseline. Machine-local reflogs, fetch metadata, and hooks are removed. TAR owner names and machine metadata are cleared when it is repacked. This is a narrowly documented exception to the exclusion of Git metadata; the research repository's author-bearing histories are not supplied.

`MANIFEST.json` contains two hashes per payload file:

- `source_sha256`: bytes in the retained source used to prepare the export.
- `sha256`: bytes supplied in this anonymous package.

When these differ, `anonymized_export` is true. Historical hashes inside saved reports refer to the original experiment and are retained as such. A historical digest is not evidence that a redacted file is byte-identical to the private original. Use the packaged-byte manifest and `verify_package.py` to verify this export, and the independent report parser to check the documented outcomes. Original source/test identity hashes remain available for the unmodified scientific inputs.

All outer ZIP timestamps and owner attributes are normalized. No publication, DOI, Zenodo creator settings, or sharing link is created by preparing the archive. File checks do not guarantee anonymity of a later deposit's landing page, account, citation exports, or metadata. Inspect that later sharing surface while signed out.
