# Independent replay input audit

Status: **PASS** (26/26 checks).

All 1,869 baseline tracked files were compared byte-for-byte with their pinned Git objects, not only with the preparation manifest. All 471 original unit-test files match; every test, lockfile, configuration and setup input is unchanged in the effective candidate. The candidate overlay contains only auth.definition.ts, with exactly one replaced line: the precise inverse of the saved original public SameSite production hunk. Independent canonical source-manifest digests match INPUT_IDENTITY.json.

The target original guard blob is 5c14cd837a04880807d3ef4f643da64cbdf6a552. Its assertion reads production source text; this is a static source-policy check. The replay deliberately retains later upstream tests, so it is not an authentic historical revision pair. No subject/test code was executed by this auditor and no experimental outcome is established.

See INDEPENDENT_INPUT_AUDIT.json for individual checks and all 1,869 Git-object byte comparisons.
