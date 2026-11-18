# Independent package rebuild audit

Status: **PASS** (86/86 checks).

The 274,813-byte reconstructed package independently matches the unchanged backend lockfile by its complete SHA-512 and the original published tarball by SHA-1. Its 29-file archive SHA-256 is a44cc1f11b18744670b2ba6211f59596073f732bb7d7d4d6575eb98a719f9406. All 106 original source files in the downloaded source archive match the pinned public Git tree.

Recorded provision/build containers satisfy all 18 inspected boundaries each, including non-root execution, no host mounts or ports, no added capabilities and fixed resource limits. Provisioning has bridge access with lifecycle scripts disabled; source build and pack have no network. Container filesystems are writable for building. No claim of a read-only root filesystem is made. All six preserved post-build package, lock, generator, tsup, tsconfig and API-schema files independently match the original archive bytes; saved generator/build/pack commands match the frozen inputs. One build attempt is recorded.

This closes the exact-package provisioning problem only. It establishes no backend test, native-selection, security false-pass or runtime CSRF outcome. This auditor read data and recomputed hashes only; no subject or package code was executed by this auditor.
