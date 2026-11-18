# Independent saved seed audit

Status: **PASS_SAVED_SEED_PROVENANCE** (56/56 checks).

The exact host manifest filename is backend-provisioning/seed-installed-manifest.json. Its SHA-256 is 0f518c86e2911fb9a6911bb8331fa58e1250c3bdcfcea035285b02c99517f280 and its immutable seed image is sha256:56559845a6388a7f0141ceea11a76684615db3aa0d34e1f9521686bb508d53e5. Saved measurements corroborate all 1,869 original source files, 937 installed package versions, 49,544 dependency file hashes, 117 relative workspace/bin links and all 29 exact shared-package members. Missing packages are optional only. Native binary outputs are present.

Recorded exact-header prefill and original offline rebuild containers have the required bounded settings; no host mounts, credentials or published ports are recorded. Administrative failures and frozen repair plans remain separate. No application source, lock or test variant was introduced, and no study tests or candidate execution is recorded in provisioning.

This read-only audit validates saved measurements and their hash/provenance relationships. It does not execute the image or independently reread all dependency bytes from the image. The frozen runner must rehash them before each arm. Seed eligibility is not an experimental result.
