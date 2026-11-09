# Final v0.3.1 candidate integration — 9 November 2026

**Prepared release work; publication and genuine interactive acceptance remain blocked.** Version 0.3.1/build 6, arm64, macOS 14+. Only v0.3.0-preview.1 is published. No passing human acceptance record exists.

## PR #1 review and integration

[PR #1](https://github.com/Brendan-Lim/ContextLens/pull/1) was independently reviewed from `caefa751da06c9fd8ffe3d3e3432f0071e2b20b5`, then fixed and reviewed at `b3c50d7688ce1a076ac6631aa0c79c79638a87d2`. [CI](https://github.com/Brendan-Lim/ContextLens/actions/runs/42556259404) and [Publication Security](https://github.com/Brendan-Lim/ContextLens/actions/runs/42556259487) passed before the exact-head merge. Merge: [`64720ef5f3b0d4adc76901832fd903d1428dd7b9`](https://github.com/Brendan-Lim/ContextLens/commit/64720ef5f3b0d4adc76901832fd903d1428dd7b9).

All 11 intended Hand Off paths were integrated. The corrected main ancestry, README redesign, four decorative brand images, screenshot demo, DMG tooling and existing release assets were preserved. Production image snapshots bind SHA-256 and decode to one read; included and duplicate-omitted frames are checked again before export. Staged exports preserve source sessions on failure. Stable issue IDs, redaction burn-in, current manifest schema 2 and legacy packages are preserved.

Blocking review findings were pinned by four failing-then-passing validator regressions: absent aggregate per-image work limits, invalid reserved PNG chunk bits/indexed palette capacity, and aliased image roles. The fix adds 128 MiB encoded / 256 MiB decoded-scanline / 16,384-chunk limits, validates those PNG rules, and rejects duplicate resolved image paths. A separate passing regression covers cancelled preparation without modifying source data. Review details and accepted limitations are in [the Hand Off report](handoff-reliability-report.md).

## Automated integration evidence

The isolated pre-merge baseline passed 116 Swift tests, 49 benchmark Python tests, 13 independently schema-validated packages and 10 deterministic replays. Reviewed PR source passed 117 Swift tests and 67 branch script tests; merged main adds the four existing screenshot/link tests.

The complete local `scripts/ci.sh` pass on the integrated source plus the guard succeeded: **117 Swift tests**, **78 script tests**, **49 benchmark Python tests**, **13 packages with independent Draft 2020-12 validation**, **10 deterministic replays**, and **10 browser defects / 10 known-good controls**. It also passed optimized ad-hoc build, portability rejection, CLI checks, ZIP CRC/path validation and an actual DMG mount/filesystem/layout/strict-signature/temporary-copy/clean-unmount round trip. This pre-commit engineering build correctly recorded `sourceDirty: true`; it is not the hosted official candidate.

Additional offline checks passed: **16 Node unit/export/mapper tests**, **3 experimental browser tests**, and **4 + 8 experimental Python tests**. Fresh-checkout attempts initially failed because ignored deterministic fixtures/dependencies were absent; after supplying only fictional offline fixtures and pinned development packages, the final runs passed with no skips. A synthetic authorization fixture explicitly denied model execution. No live model calls, allocation data or trial records were used.

The full reachable-history audit inspected **647 file versions / 585 blobs** with zero findings; pinned **Gitleaks 8.30.1** found none. Local Markdown/link and tracked-file audits passed. These are automated structural/privacy-scanner checks, not human visual acceptance. Final hosted source checks and exact downloaded-candidate verification are recorded below after completion.

## Release-input safety

The official channel now binds a versioned release-input inventory into the signed app's `official.json` and outer provenance. It protects the tracked dependency closure, modes and symlinks by default. Only explicitly enumerated ordinary documentation and the exact candidate acceptance JSON path are exempt. New unknown inputs, dependencies, scripts/imports, resources, signing/version metadata, DMG dependencies/artwork/layout and workflows remain protected.

Promotion checks every intervening descendant tree, including changed-then-reverted inputs, and repeats current-main and freshness checks immediately before the first remote mutation. Missing/forged inventories fail closed. Existing ancestry, signatures, hashes, unused-version and human acceptance checks remain. The trusted Developer ID workflow is unchanged. Fourteen focused official-gate tests pass, including real temporary-Git dependency/mode/symlink histories, permitted README/report/acceptance changes, independent ZIP/DMG tampering and mismatched embedded provenance.

**Old candidate 42504640955 is obsolete.** Its source `11b099a4742b11cdbf6595ecc52a7eb54c3d58c0` predates PR #1 and has no new release-input inventory. Its artifacts and history remain intact; neither its hashes nor any old acceptance may authorize this release.

## Replacement hosted candidate

Prepare-only workflow, source identity, exact hashes, toolchain and artifact expiration: pending the newly verified source. No local development output is represented as a hosted candidate.

## Genuine visual and native acceptance

Genuine Capture, Review, Mark Up, Hand Off and Finder light/dark screenshots remain pending. No app GUI or personal-window capture was launched. ZIP/DMG automation can verify structure and install-copy integrity; it cannot establish actual Finder appearance, quarantined first launch, permissions or capture/recovery behavior.

Use [the existing screenshot kit](screenshot-kit/README.md) and [exact-candidate acceptance](release-acceptance/README.md) in a disposable macOS VM or spare Mac. The owner's installed app, sessions, exports, TCC and Gatekeeper settings are outside this task. No quarantine removal or permission reset is authorized. Only genuine observed results may populate the still-absent `docs/release-acceptance/0.3.1.json`.
