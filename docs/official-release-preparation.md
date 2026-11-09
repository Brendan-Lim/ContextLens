# Official unnotarized release preparation

The published download is [v0.3.0-preview.1](https://github.com/Brendan-Lim/ContextLens/releases/tag/v0.3.0-preview.1). v0.3.1/build 6 is an **unpublished candidate**, with ad-hoc signatures, no Developer ID and no Apple notarization. No installable stable Homebrew cask exists. The separate [Developer ID workflow](releasing.md) keeps its signing, notarization and Gatekeeper requirements.

## Candidate baseline

[Prepare-only run 42601149595](https://github.com/Brendan-Lim/ContextLens/actions/runs/42601149595) prepared the integrated Retina source below; its promotion job was skipped. Independent package verification and exact-byte native engineering checks passed all 14 engineering cases, including real Finder Light/Dark, drag/install/eject/launch, Low/High capture, Review/Mark Up, Hand Off and lifecycle/recovery. The seven owner-approved genuine Retina screenshots are integrated in the README; [the kit](screenshot-kit/README.md) describes their provenance.

| Identity | Value |
|---|---|
| Source | `d0323bb84c08d5f42c29cae5635931bf2d825d98` |
| Version / build / architecture | 0.3.1 / 6 / arm64 |
| ZIP SHA-256 | `78692e2ec6997dbcdbfaf17021f43347aec5938eca8e29f25c22b79b11c94c70` |
| DMG SHA-256 | `32b3b53b0576a3fe8d2e8c3bf6700de9e0d6b5bdd4066c8657975229c920407c` |
| Bundle inventory SHA-256 | `ee4613c20e6d9b2eb4c476b860709f4e97f87e09bbed9259330fb9b88bb662ed` |
| Release-input SHA-256 | `b82101587ee58ee3369720fcd621dc824f51c6aeab53add29e934f6a4843ecc2` (516 files) |
| Artifact expiry | 9 December 2026, 18:31:01 SGT |

This identifies a tested baseline, not eligibility for every later main revision. **The repository cleanup changes protected release inputs; after integration, prepare and independently verify a fresh candidate.** Do not promote the baseline artifacts after that change, or reuse their hashes for replacement artifacts. Keep originals and observations as historical regression evidence.

Five human security cases remain pending: genuine quarantined first launch, user-controlled Open Anyway, fresh Screen Recording denial, grant/relaunch, and permission revocation/recovery. Automation and existing runner permissions cannot establish these. No passing `docs/release-acceptance/0.3.1.json` exists. macOS 14 runtime, mixed-display behavior and sustained real-workload performance remain unverified; macOS 14.0 is deployment metadata.

## Prepare, verify, accept, promote

1. Integrate reviewed changes and require green CI and Publication Security on current main. Inspect [release-input freshness](release-acceptance/README.md#candidate-freshness); documentation changes are exempt only when explicitly listed as regular non-executable files in the unchanged policy.
2. With maintainer authorization, dispatch `.github/workflows/unnotarized-stable.yml`, operation `prepare`, for the unused version in `config/version.json`. Preparation has read-only Contents permission, runs CI, builds one ad-hoc app and packages both formats, and uploads a 30-day artifact. It creates no release or tag.
3. Download that exact artifact into a fresh directory and verify it on an independent Mac:

   ```sh
   gh run download RUN_ID --repo Brendan-Lim/ContextLens --name official-candidate-0.3.1 --dir CANDIDATE
   (cd CANDIDATE && shasum -a 256 -c SHA256SUMS)
   .build/dmg-python/bin/python scripts/unnotarized-release.py verify-assets CANDIDATE
   ```

   Install hash-pinned build-only DMG dependencies as described in [installer tooling](../distribution/dmg/README.md). Verification covers source/input provenance, strict signatures, portable embedded CLI, ZIP paths/CRCs, private DMG mount/filesystem/layout, a temporary install copy, clean detach and identical bundle inventories. It cannot prove first-launch security or GUI behavior.
4. Repeat applicable native engineering checks on the new exact bytes and complete all five human security cases in a disposable interactive Mac. Use [the acceptance procedure](release-acceptance/README.md), [the matrix](beta-acceptance.md) and [native testing](native-testing.md). Preserve synthetic evidence privately. Never reset the owner's TCC, remove quarantine or replace the owner's installation.
5. Only actual observations reviewed by a maintainer may populate the exact candidate acceptance record. Every required case must pass and name the tested source, assets and bundle inventory. A failed or expired candidate requires new bytes and renewed acceptance.
6. Promotion is a separate manual operation with the original successful prepare run and typed confirmation. It rechecks freshness and acceptance before any remote mutation, verifies both containers without rebuilding, and refuses existing tags/assets. Do not dispatch it until explicitly authorized.
7. After publication, separately generate, review and test the stable cask from the published ZIP using [Homebrew procedures](homebrew.md). Keep preview assets and the working preview cask intact.

See [installer geometry and reproducible packaging](../distribution/dmg/README.md), [publication security](publication-security.md), [preview downloads](preview-releases.md) and [contribution rules](../CONTRIBUTING.md).
