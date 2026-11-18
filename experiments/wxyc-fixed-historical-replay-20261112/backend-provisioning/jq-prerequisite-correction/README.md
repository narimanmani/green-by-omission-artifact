# jq prerequisite correction

Read-only inspection of immutable seed `56559845a6388a7f0141ceea11a76684615db3aa0d34e1f9521686bb508d53e5` confirmed that Bash exists but jq is absent. The unchanged cron resolver invokes jq at line41. This is consistent with the parent's baseline-only shell127 failures. No resolver, Jest, upstream test or candidate was run in this subtask.

The separately frozen OS-only correction installs exactly three official Debian packages: jq and libjq1 `1.6-2.1+deb12u3`, and libonig5 `6.9.8-1`. No existing OS version changed. Full checksums match the official original APT index, and all three downloaded archives are preserved in `official-debs/`.

New retained tag: `sp2027-wxyc-replay-seed-jq:20261112`  
Image ID: `sha256:36222dd77240e20948861c15d9e80b5940ef034e6130333019344815797b99ea`

All 49,661 old dependency file/symlink entries were independently rechecked before the original metadata observer recomputed its identical manifest. All 1,869 original source bytes, Git HEAD/origin-main/tree and clean tracked state remain unchanged. The installed manifest SHA256 remains `0f518c86e2911fb9a6911bb8331fa58e1250c3bdcfcea035285b02c99517f280`. No Node dependency, source, test, lock or configuration changed, and no npm lifecycle was rerun.

Old seed/image and parent baseline-v1 outcome remain untouched. The first read-only APT metadata query's private-scratch error is retained; a second query used a bounded /tmp tmpfs under read-only root. Actual OS installation used the established root-owned APT cache in a bounded container with capabilities dropped, no-new-privileges, and no host mounts/socket/ports/credentials. Final verification ran offline as UID10001. All evidence containers/images are retained.

This corrects an execution prerequisite. It supplies no new study outcome or security claim.

