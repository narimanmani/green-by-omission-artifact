# Unchanged backend seed environment

Retained image: `sp2027-wxyc-replay-seed:20261112`  
Image ID: `sha256:56559845a6388a7f0141ceea11a76684615db3aa0d34e1f9521686bb508d53e5`

The original baseline and Git metadata reside at `/opt/replay/seed`, with runtime UID10001. Both HEAD and origin/main are `b86530c6c656b7a8f72d42145e9d46995c7ab53d`; Git reports no tracked changes. All 1,869 original tracked file hashes match the independent baseline manifest.

`/opt/replay/seed-installed-manifest.json` lists 49,544 regular dependency files and 117 symlinks, including nested workspace dependencies. Its SHA256 is `0f518c86e2911fb9a6911bb8331fa58e1250c3bdcfcea035285b02c99517f280`. Every symlink is relative, resolves within the seed, and exists. All 937 installed locked package versions match; 106 absent entries are optional platform packages, with no nonoptional package missing. All 29 installed files of `@wxyc/shared@4.1.0` match the exact reconstructed package.

Runtime versions are Node24.19.0, npm11.17.0 and Git2.39.5. Jest30.4.2, ts-jest29.4.12 and TypeScript6.0.3 are installed from the unchanged lockfile.

A separate read-only image inventory found zero untracked files or symlinks outside Git metadata and all nested node_modules. There are no additional generated workspace dist/build/module files to add to the installed manifest. Its report and exact observer receipt are preserved.

## Provisioning boundaries

No Jest call, upstream test, candidate, or experiment was executed. All npm operations ran UID10001 inside bounded containers with capabilities dropped, no-new-privileges, no host mounts/socket/ports, and no injected credentials. Empty NPM_TOKEN served only the original .npmrc interpolation. The source, package, lock, and test configuration were not edited.

Public provisioning used the matched original shared-package archive in the npm cache and the original npm ci with lifecycle scripts disabled. The existing public Git dependency used SSH-to-HTTPS transport for the same repository and immutable commit; its lock entry stayed unchanged. The original npm rebuild ran later in network:none isolation.

Two prerequisite failures are retained: APT's original _apt-owned cache was not writable with all capabilities dropped; the original offline native build then lacked exact Node headers. Separate frozen administrative repairs changed only the APT cache location and prefetched the exact official Node24.19.0 headers, whose SHA256 was verified as `54f14a297d47ea0794fe272363703d9dc419c96ac68f20d890f98b63754a3e4c`. The successful lifecycle rerun started from the clean pre-rebuild image with the same original dependencies and command.

The npm11.17 allowScripts warning is advisory for unreviewed packages. Its exact primary implementation is preserved, and the installed manifest records the successfully built cpu-features and ssh2 native binaries. No script-policy override or approval was used.

## Evidence

`FROZEN_PROVISIONING_PLAN.json`, the two frozen repair plans, all command receipts and failure logs, original source transfer archive, installed file/symlink manifest, and `seed-provenance.json` preserve the full setup. `HEADER_REPAIR_PROVISIONING_RESULT.json` is the successful final result; earlier failure results remain separate. All containers and images are retained.

This environment is ready for the parent agent's separately sealed harness. Provisioning checks are not experimental results.

