# Exact original package reconstruction

The single frozen attempt rebuilt `@wxyc/shared@4.1.0` from public immutable commit `e9374c62f32c9fd4ccccd23651babb7a556fa210` (tag `v4.1.0`).

The resulting `wxyc-shared-4.1.0.tgz` is 274,813 bytes with 29 files. Its complete SHA512 equals the unchanged Backend-Service lockfile integrity:

`sha512-Onouu4bGBL9sVVLIhzLy72+jDg/JBTkNH88XF+4x5A101eq747vmyD/nfXNo1Q21SciMc+KTWWP/QFmtN/6WRA==`

SHA1: `cd129532df5782044467db10c8dd0e91648b0547`  
SHA256: `a44cc1f11b18744670b2ba6211f59596073f732bb7d7d4d6575eb98a719f9406`

Public dependency provisioning used `npm ci --ignore-scripts --no-audit --no-fund`. The original generation, build, and package preparation ran offline in a separate container. The base image supplies the publisher's exact Node24.19.0 and npm11.17.0:

`node@sha256:a9f5f7c91a432850b2a8a7797adf5eadb6c733ceed61167806cee7ea7fbc29df`

Both containers used UID1000, dropped capabilities, no-new-privileges, no host mounts/socket/ports or injected credentials, and CPU/memory/process bounds. The evidence containers and prepared image are stopped/retained. The base image does not include Git.

`FROZEN_BUILD_PLAN.json` predates provisioning/build and fixes commands and acceptance. `COMMAND_RECEIPTS.json`, stage logs, source manifests, package manifest, original primary responses, post-build copies, and `REBUILD_RESULT.json` preserve the attempt. `POST_BUILD_READONLY_VERIFICATION.json` checks unchanged package/lock/generator/build config/spec inputs and isolation metadata.

This reconstructs the exact locked dependency. It provides no selective-test outcome, original-test false pass, or security-runtime result. No study candidate, manuscript or upstream tests were modified or executed.

