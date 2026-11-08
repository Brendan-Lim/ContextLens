# Official v0.3.1 release preparation — 9 November 2026

**Prepared, not published. READY FOR CONTROLLED TESTERS remains unchanged.** Version 0.3.1/build 6 is still blocked on real first-launch, fresh permissions, selected-window capture/closure and recovery acceptance. This iteration adds a designed installer, a visual README and an explicit official unnotarized channel without changing production application logic or relaxing Developer ID/notarization gates.

## A. DMG design

The selected **Twin Glass** composition uses soft icy-blue gradients, navy system typography, the repository's owned outlined wordmark, two rounded translucent wells, controlled highlights and a flowing directional curve. A second composition uses one continuous glass tray. Both were rendered and inspected; separate wells provide clearer spacing between the functional drag targets.

- Finder content: **720 × 440 points**, initial origin (160, 120).
- Background representations: **720 × 440 at 72 DPI** and **1440 × 880 at 144 DPI**, combined into a hidden multi-resolution TIFF.
- Real Finder icons: **104 points**, centers **(214, 254)** and **(506, 254)**, labels below at 13 points.
- Original sources: `distribution/dmg/render.swift`, `Brand/wordmark.svg`, `Brand/AppIcon.icns`. The existing mascot identity is preserved; no third-party artwork/font files are redistributed.
- Exact assets: `distribution/dmg/assets/background.png`, `background@1x.png`, `composition-b.png`; README hero `docs/media/hero.png`; labeled icon composition `docs/media/installer-preview.png`.

![Selected installer placement illustration, not a Finder screenshot](media/installer-preview.png)

The disk background contains **neither app nor folder icons**. The real app bundle is draggable; a real `/Applications` symlink supplies the destination. The illustration above adds a clearly labeled diagrammatic folder for design review only. It is not the disk background or a Finder screenshot.

Backgrounds, hero, placement illustration and the historical native screenshot were opened and inspected. New media hashes are explicit in the publication policy. ImageIO metadata was inspected; the new images contain dimensions/color information, no source capture metadata or personal identities. The unchanged synthetic GIF keeps its illustration label and earlier approval. The historical native screenshot shows generated geometric content and is explicitly distinguished from the current tabs and untested candidate.

Media review caught a corruption in Xcode's old `pngcrush -reduce` RGBA-to-RGB conversion. The generator now preserves RGBA and compares **every decoded sRGB pixel** with the originals before accepting optimized media. The incorrect outputs were discarded before publication. The final PNGs render correctly and pass container/CRC checks.

**Actual Finder appearance: pending.** No disposable GUI session is available. Metadata checks and the design proof do not establish dark-mode label contrast, actual icon alignment or Finder Retina rendering. These are mandatory acceptance cases.

## B. Packaging

`distribution/dmg/build-dmg.py` uses native `ditto`, `sips`, `tiffutil`, `hdiutil`, `diskutil`, `codesign`, `lipo` and `otool`. It verifies the original app, stages HFS+ UDRW, attaches privately with `-nobrowse -noautoopen`, writes volume-scoped `.DS_Store`, detaches and converts to read-only UDZO. The hidden background has a volume-relative alias. No global Finder preference or normal Applications folder is changed. Temporary mounts use unique canonical `/private/tmp` locations and cleanup on success/failure.

Finder metadata uses **ds-store 1.3.1 / mac-alias 2.2.2**, both MIT, build-only, exact-wheel hash-pinned. There are no new production runtime dependencies. [Reproducible commands and geometry](../distribution/dmg/README.md).

The official packager builds **one signed app**, then creates both ZIP and DMG. It validates ZIP paths/CRC, extracts with `ditto`, verifies signatures/provenance, mounts the DMG, and compares every normalized bundle file SHA-256, executable bit and relevant resource/Finder metadata. Timestamps/quarantine are intentionally excluded from bundle identity. Both containers have independent SHA-256 values. `SHA256SUMS` covers ZIP, DMG and `provenance.json`; provenance records source commit/tree, toolchain, OS, version/build, signing mode and bundle inventory hash.

Local development packaging passed actual filesystem/mount/strict-signature/CLI/background/layout checks and a normal `ditto` install-copy round trip into a temporary directory. The source bundle inventory remained unchanged. Clean official-candidate dual-container results and hashes are recorded below; local engineering artifacts are never release acceptance.

Architecture is **arm64**, minimum deployment target **macOS 14.0**. Local checks use macOS 26.6.2; macOS 14 runtime remains unverified. App identity stays `dev.contextlens.app`. No quarantine stripping, Gatekeeper change, TCC reset or installed app replacement occurred.

## C. README

The root README now follows hero → problem → four-step workflow → real fixture output → capabilities → installation → privacy → audience → development/open source. Benefits concern organized visual feedback and less repetitive screenshot/prompt preparation as product goals; no measured effort, token or time saving is claimed. Source mapping remains an isolated experiment, and no autonomous source edits/model execution are promised.

Media is repository-owned and deliberately labeled: branded hero, historical actual native editor with synthetic content, existing synthetic fixture GIF, real generated annotation/package links and installer design proof. The main download links to the actual published `v0.3.0-preview.1`; Homebrew uses the working preview command. DMG instructions are explicitly future availability until the official assets exist.

## D. Official release infrastructure

`.github/workflows/unnotarized-stable.yml` is manual and separate from the unchanged trusted `.github/workflows/release.yml` and preview workflow.

1. **prepare** requires clean current main and an unused version, runs CI, builds with `--unnotarized-stable`, verifies both formats and uploads a 30-day candidate artifact. It cannot publish a release and has read-only repository Contents permission.
2. A person tests **those exact bytes** on a disposable interactive Mac. The [pending template](release-acceptance/template.json) must be replaced by an actually observed, reviewed `docs/release-acceptance/0.3.1.json`. That file deliberately does not exist today.
3. **promote** requires an explicit typed confirmation, the original successful official prepare run and a committed complete acceptance record. Evidence must match source, build, both asset hashes and bundle inventory. Every required native/Finder case must pass with an observation and evidence locator; unresolved blockers stop publication. It verifies source ancestry and rechecks packages without rebuilding.
4. Only then can it create tag `v0.3.1` and draft **ContextLens v0.3.1**, upload immutable assets, redownload/verify them and publish. Previously used tags/releases/assets cannot be overwritten. Failed publication requires deliberate inspection, not clobber/retry.

Signing is **ad-hoc, unnotarized, no Developer ID**. Release notes disclose this and Apple's normal user-controlled Open Anyway procedure. Human evidence remains a maintainer attestation, not something unit tests can prove. [Full procedure](release-acceptance/README.md).

The stable cask updater's explicit `--unnotarized-official` path requires the actual published stable release, both verified packages, acceptance, provenance and source-tag identity. Only then does it render the real ZIP checksum/API asset ID with architecture/OS requirements, app and embedded CLI artifacts, preview conflict and honest caveats. There is no installable stable cask or invented checksum. The default updater still enforces Developer ID, stapling and Gatekeeper. Preview bytes and cask are preserved. [Migration instructions](homebrew.md) require quit/save/backups and deliberate uninstall of only the preview cask, preserving sessions and exports.

## E. Tests and observed results

Local host: Apple Silicon, macOS **26.6.2 (25G83)**. No live model calls, personal-window recording or native fixture launches were used.

| Category | Result and repeatable command |
|---|---|
| Baseline Swift | **106 tests passed**, `scripts/verify.sh` |
| Coverage map | Passed in baseline, `python3 scripts/check-coverage-map.py` |
| Benchmark Python | **49 passed**, baseline `scripts/verify.sh` |
| Packages / independent schemas | **13 validated**, including Draft 2020-12 validation |
| Deterministic production replay | **10 passed** |
| Publication/release/Python regressions | **53 tests passed**, `python3 -m unittest discover -s scripts/tests -v` |
| Additional experiment Python | **4 + 8 passed**, `python3 -m unittest discover -s Experiments/visual-to-code/tests -v` and equivalent `Experiments/code-aware-efficiency/tests` |
| Node unit/export/mapper | **16 passed**, `node --test Experiments/visual-to-code/tests/unit.test.mjs Experiments/visual-to-code/tests/export.test.mjs Experiments/code-aware-efficiency/tests/mapper.test.mjs` |
| Additional experimental browser tests | **3 passed** with Playwright's pinned browser, `node --test Experiments/visual-to-code/tests/browser.test.mjs`; system Chrome initially failed resize calibration (2/3 passed), so Chrome compatibility for this isolated experimental adapter is unproven |
| Owned browser fixtures | **10 defects reproduced / 10 controls passed**, `CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' node Benchmarks/runners/verify-fixtures.mjs` |
| Optimized native build | Passed, `CONTEXTLENS_SIGN_IDENTITY=- scripts/build-app.sh --output .build/official-preparation` |
| Portability rejection / CLI aliases | Passed, `python3 scripts/verify-release-build.py --app .build/official-preparation/ContextLens.app` |
| Development ZIP / extracted signature / CLI | Passed, `python3 scripts/release.py package .build/official-preparation/ContextLens.app .build/official-zip-check --development` |
| Actual DMG mount / filesystem / UDIF checksum / detach | Passed, `.build/dmg-python/bin/python distribution/dmg/build-dmg.py .build/official-preparation/ContextLens.app .build/official-preparation/ContextLens-0.3.1-arm64.dmg` |
| Actual temporary install-copy / signature | Passed within DMG verification; normal app copy into a throwaway folder |
| Cask templates | Ruby + semantic checks passed; no stable install/fetch possible before publication |
| Tap guard regressions | **19 passed**; current preview cask unchanged |
| Public staged/current/history audits, links, independent Gitleaks | Final audited-index and post-commit results recorded below |
| Actual Finder window, light/dark, drag-to-Applications/eject/launch | **Pending isolated interactive Mac** |
| Real Gatekeeper / Open Anyway / fresh Screen Recording | **Pending isolated interactive Mac** |
| Real selected-window capture/closure/app exit, annotation/Hand Off/recovery/pending-save behavior | **Pending isolated interactive Mac** |

Initial native mount attempts were sandbox-blocked; permitted private mounts subsequently succeeded. The browser initially could not bind loopback under the sandbox; the permitted headless owned-fixture run passed. Installer integration checks caught incorrect Python record/path type comparisons and a noncanonical mount alias path before final bytes were accepted. Cleanup ran on those failures. A failing-then-passing regression also verifies that forced-detach cleanup cannot be reported as a clean unmount; normal detach failure now fails validation even if forced cleanup succeeds. No failed check is being counted as acceptance. Hosted security CI also caught a timezone-dependent acceptance fixture before promotion: the date-only gate now requires an ISO timestamp with timezone, with a regression for UTC−12 through UTC+14 and rejection of naive/future timestamps.

## F. Remaining blockers

The complete [beta acceptance matrix](beta-acceptance.md), including the existing unresolved live closure diagnostic, remains pending. Specifically: genuine quarantined first launch and user-controlled authorization, fresh permission deny/grant/relaunch, Low/High selected-window capture, Review/annotation/undo/redo, UI Hand Off, reopen/recovery, closure without substitution, target-app exit, ContextLens exit during capture, correct pending-frame persistence and failed-save/retry. Inspect the real Finder window in light/dark modes and complete the genuine drag/install/eject/launch flow. Runtime macOS 14 and mixed-display checks remain unproven.

Automated mounting/copying is packaging evidence, not native app acceptance. No stable tag, GitHub Release or installable stable cask will be published in this iteration. After acceptance, generate/push the actual cask from the published ZIP and verify Homebrew style, online audit, fetch, clean installation/CLI/uninstall on disposable infrastructure. Upgrade needs another genuinely verified release.

## G. GitHub results

Implementation and independent tap-preparation commits were pushed separately; verified source and hosted results follow. The existing preview is [v0.3.0-preview.1](https://github.com/Brendan-Lim/ContextLens/releases/tag/v0.3.0-preview.1). No new binary release is claimed.

### Verified source and local package follow-up

- Main implementation: [`e0bbf4d69dd3087d8c9eb790401f32685eb6340d`](https://github.com/Brendan-Lim/ContextLens/commit/e0bbf4d69dd3087d8c9eb790401f32685eb6340d).
- Timezone correction: [`3a59ebe324d95517923461d1ebcdcc749373f9c1`](https://github.com/Brendan-Lim/ContextLens/commit/3a59ebe324d95517923461d1ebcdcc749373f9c1). Its [Publication Security run](https://github.com/Brendan-Lim/ContextLens/actions/runs/42504314081) passed; the original date-only fixture failure remains [visible](https://github.com/Brendan-Lim/ContextLens/actions/runs/42504132239).
- Independent tap preparation: [`25a4e6a1086e4c2a1e58fbc6da89fe452021fe69`](https://github.com/Brendan-Lim/homebrew-tap/commit/25a4e6a1086e4c2a1e58fbc6da89fe452021fe69). [Tap validation](https://github.com/Brendan-Lim/homebrew-tap/actions/runs/42504134693) and [Publication Security](https://github.com/Brendan-Lim/homebrew-tap/actions/runs/42504134702) both passed. Validation repeated the real disposable preview installation/link/help/quarantine/existing-app refusal/uninstall-preservation checks, style, online audit and fetch. The preview cask was not modified.

The clean **local engineering candidate** at source `e0bbf4d` passed `scripts/build-app.sh --unnotarized-stable --output .build/official-candidate` and `.build/dmg-python/bin/python scripts/unnotarized-release.py package .build/official-candidate/ContextLens.app .build/official-candidate-assets`. These are local artifacts, not published release checksums or native acceptance:

| Asset | SHA-256 |
|---|---|
| Local ZIP | `7cc6956b497413c800ec5db4b86538539f2eb553edbfe52c97a38ca29d41f339` |
| Local DMG | `e12e8d64b036b848a43ac3024263bb950b36a6507765969f6df23bc78b1e0981` |
| Shared normalized bundle inventory | `f92231e7458f8963124c839024c6f657ff1d5718af54bcd7e0629537cb2f25c1` |

`shasum -a 256 -c SHA256SUMS`, run inside `.build/official-candidate-assets`, passed for ZIP, DMG and provenance. Both package round trips passed with exactly matching bundle files and signatures. An actual stable updater attempt received HTTP 404 for unpublished `v0.3.1`, failed before writing a cask and left the tap clean. Source provenance records Xcode 26.6 / Swift 6.3.3 / macOS 26.6.2 for this local build. Hosted candidates use their own recorded toolchain and hashes.

Staged/current/history publication audits and independent Gitleaks passed for both source repositories. The implementation history audit inspected 604 path/blob versions / 542 blobs with zero findings. The public link audit covers 87 Markdown files / 128 local links with zero findings; the external check initially identified two obsolete dependency repository URLs, which were corrected to the current upstream organizations. The corrected network review returned HTTP 200 for all 71 then-current external URLs. GitHub-rendered README HTML was reviewed at 1120 and 390 pixel widths with local media: all five images decoded, and page width matched the viewport in both previews. This is README layout QA using GitHub-rendered markup and representative styling, not a native app or Finder screenshot.

### Hosted packaging source

Packaging source [`11b099a4742b11cdbf6595ecc52a7eb54c3d58c0`](https://github.com/Brendan-Lim/ContextLens/commit/11b099a4742b11cdbf6595ecc52a7eb54c3d58c0) includes the clean-detach failure regression. [Publication Security](https://github.com/Brendan-Lim/ContextLens/actions/runs/42504575474) passed, and [prepare-only run 42504640955](https://github.com/Brendan-Lim/ContextLens/actions/runs/42504640955) passed full CI and both-container packaging with its promotion job skipped. Its Actions artifact is a 30-day candidate for isolated testing, not a public GitHub Release. An earlier complete [prepare run](https://github.com/Brendan-Lim/ContextLens/actions/runs/42504356626) also passed after the timezone correction.

A separate full CI run at the same packaging source failed once during native `hdiutil create -srcfolder` (exit 1) after its 53 Python regressions, Swift/packages/replays, ZIP and portability checks passed. The captured native stderr was not surfaced by the existing subprocess helper, so the root cause is **unestablished**. The independent prepare run exercised that command successfully; the failed attempt is retained in [run 42504575455](https://github.com/Brendan-Lim/ContextLens/actions/runs/42504575455). It is not represented as a clean first attempt. No fallback skipped mounting or relaxed signature/integrity checks.

### Downloaded hosted candidate verification

The final packaging source's [full macOS CI](https://github.com/Brendan-Lim/ContextLens/actions/runs/42504575455) passed on **attempt 2**. Its [Publication Security](https://github.com/Brendan-Lim/ContextLens/actions/runs/42504575474) passed with 52 tests plus one intentional macOS-only test skip on Linux; the macOS suite passed all **53**. The successful prepare-only artifact was downloaded with `gh run download 42504640955 --repo Brendan-Lim/ContextLens --name official-candidate-0.3.1 --dir .build/official-hosted-assets`, then independently reverified on the local Mac using `.build/dmg-python/bin/python scripts/unnotarized-release.py verify-assets .build/official-hosted-assets`.

This repeated final SHA-256 list validation, ZIP extraction, strict ad-hoc signatures, source tree identity, actual DMG mount/filesystem/background/layout/CLI checks, clean detach, temporary install copy and ZIP/DMG bundle equality. The official workflow identity and source SHA also matched the downloaded provenance. No native GUI was launched. Hosted build: **Xcode 26.3, Swift 6.2.4, arm64 macOS 15.8.2**.

These candidate hashes identify the **unpublished Actions artifact**, not a published release:

| Hosted candidate asset | SHA-256 |
|---|---|
| `ContextLens-0.3.1-arm64.zip` | `1744796edda0262a77bc25de1cdfb7864aa8871eb833d4dc1011494ef60e501e` |
| `ContextLens-0.3.1-arm64.dmg` | `2c0e1adf00ea6b23803122770e6bc45b5e14e83a067f325b442b525abe17bf76` |
| Shared normalized bundle inventory | `6bb5017a2f76401370a6e7db5b1aa635635ed42cd7765c79997749356a004a37` |

The required `docs/release-acceptance/0.3.1.json` is still absent, and the pending template still fails the acceptance validator. Only the older preview remains listed as a GitHub Release; no stable tag, draft, release asset or installable stable cask was created. The Developer ID workflow, trusted verifier and preview release script have no diff from the baseline. Both repositories retain clean worktrees after the report-only follow-up commit; private experiments and the owner's app/permissions are untouched.
