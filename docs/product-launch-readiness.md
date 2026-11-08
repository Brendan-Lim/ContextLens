# Product launch readiness — 9 November 2026

**Summary.** The README is now a user-facing landing page. Its only images are decorative brand artwork, which shows no application UI. All five genuine product screenshots (Capture, Review, Mark Up, Hand Off, Finder installer) are still **missing**: no disposable interactive Mac was available, and the owner's personal desktop is out of bounds. Official v0.3.1 remains **blocked** on interactive acceptance, and stable publication is **not allowed**. Nothing was published, tagged or uploaded.

Environment: Apple Silicon, macOS 26.6.2 (25G83), Xcode 26.6 / Swift 6.3.3. No VM tooling (UTM, Tart, Parallels, VMware, Anka) is installed. No native app launch, Finder automation, screen capture of the desktop, TCC change, Gatekeeper change or installed-app replacement took place.

## A. README

### What changed

The README was rewritten for someone who has never heard of ContextLens:

1. **Hero:** light and dark brand artwork through `<picture>`, a one-sentence value proposition, and Download, Homebrew and Get started links.
2. **Problem:** “Your UI feedback shouldn’t need an essay.”
3. **Workflow:** “Capture. Review. Mark Up. Hand Off.” A decorative step banner, followed by one short paragraph per step.
4. **Why developers use ContextLens:** six benefits, each tied to a real capability (marks with stable IDs, per-issue notes, crops, saved sessions, a plain-file hand-off, native capture and zoom).
5. **A real round of UI polish:** a worked example using the screenshot-kit demo dialog. It shows the actual hand-off folder layout and the exact prompt that `ContextReport.instruction` produces.
6. **Install:** the preview download, the Homebrew preview cask, and plain-language first-launch steps with Open Anyway.
7. **Privacy:** selected window only, no account or networking code, nothing reaches an AI until the user pastes it, and where sessions live.
8. **Get started:** six steps that use the app's real labels (⌘N, **Which window?**, **Start Capture**, **Stop Capture**, **Save Hand Off**, **Copy prompt**).
9. **Open source:** MIT, build commands, documentation links and contribution guidance.

No percentage, time, token or model-performance benefit is claimed. The README says plainly that ContextLens prepares context and does not run a model or edit code.

### Engineering disclaimers moved out

| Former README statement | Now lives in |
|---|---|
| Unnotarized preview “for controlled testers”; the 0.3.1 candidate is blocked on isolated acceptance | [official-release-preparation.md](official-release-preparation.md), sections D and F; [release-acceptance/README.md](release-acceptance/README.md) |
| “Historical workflow illustration”, “not verification of the 0.3.1 candidate” | This report, section B; [official-release-preparation.md](official-release-preparation.md), section C (marked superseded) |
| “Synthetic browser-fixture illustration, not a native app recording” | [demo-storyboard.md](demo-storyboard.md) (unchanged, still labeled) |
| “Generated example package … actual fixture export output” and the version-2 layout note | [export-format.md](export-format.md); the example stays under `docs/examples/agent-session-v2/` |
| “Installer design preview … Finder appearance pending” | [distribution/dmg/README.md](../distribution/dmg/README.md); [official-release-preparation.md](official-release-preparation.md), section A |
| macOS 14 runtime unverified; hosted checks on macOS 15 | [troubleshooting.md](troubleshooting.md) (user-facing); [official-release-preparation.md](official-release-preparation.md), section B |
| Tiny or low-contrast changes can be missed | [troubleshooting.md](troubleshooting.md), with the High sensitivity and ⌘⇧S remedy |
| Effort, token and time savings not measured | [research.md](research.md) |
| Source mapping is an isolated experiment | [Experiments/visual-to-code/README.md](../Experiments/visual-to-code/README.md) |

[troubleshooting.md](troubleshooting.md) also had an outdated claim that no Homebrew cask or binary download existed. It now describes the preview channel, ad-hoc signing and Open Anyway accurately.

### Media audit

| Asset | Classification | README now |
|---|---|---|
| `docs/media/readme/hero-light.png`, `hero-dark.png` (new) | 3, decorative brand artwork | Hero |
| `docs/media/readme/workflow-light.png`, `workflow-dark.png` (new) | 3, decorative brand artwork (abstract step glyphs, no app UI) | Workflow banner |
| `Brand/mascot-peek.svg` | 3, decorative brand artwork | Footer |
| `docs/media/hero.png` | 3, decorative brand artwork | Replaced by the 2× light/dark pair; kept for the DMG docs |
| `docs/media/native-editor-history.png` | 5, historical application screenshot (old “Annotate” sidebar UI) | **Removed**; file kept as evidence |
| `docs/media/synthetic-fixture.gif` | 4, synthetic demonstration | **Removed**; still used by [demo-storyboard.md](demo-storyboard.md) |
| `docs/media/installer-preview.png` | 6, engineering illustration (drawn folder, “design preview” band) | **Removed**; still used by the DMG docs |
| `docs/examples/agent-session-v2/annotated/CL-001.png` | 4, synthetic generated geometry | **Removed**; still used by the example package |

The new artwork is rendered by [`Brand/readme/render.swift`](../Brand/readme/render.swift) from the repository's wordmark and app icon with system fonts. It is optimized losslessly; [`generate.py`](../Brand/readme/generate.py) compares every decoded pixel. All four images were opened and inspected. Their SHA-256 values are in `config/publication-policy.json`.

### Rendering checks

The README was rendered with GitHub's own Markdown API (`gh api -X POST /markdown -f mode=gfm`) and styled with `github-markdown-css@5.5.1` at **1012 px** (desktop) and **390 px** (phone), in light and dark, with headless Chrome. GitHub kept the `<picture>`/`<source>` elements; the dark artwork appears only in dark mode. All images decoded. Nothing overflowed the page width at 390 px; only the file-tree code block scrolls inside itself, as code blocks do. At phone width the hero's small fact pills become hard to read. The same facts are repeated in text under the links.

Two defects were found and fixed before commit: a stray blank line inside the benefit cards, and a prompt code block that scrolled sideways (now a wrapped quote). The Apple link text was corrected to the article's real title, “Safely open apps on your Mac”. All README external URLs returned HTTP 200.

## B. Genuine product visuals

| Shot | Status | Intended path | Version | Capture environment | Privacy review |
|---|---|---|---|---|---|
| A — Capture panel with a window selected | **Missing** | `docs/media/screens/A-capture.png` | must be 0.3.1 (6) | needs an isolated Mac or VM | pending |
| B — Review tab with captured states | **Missing** | `docs/media/screens/B-review.png` | must be 0.3.1 (6) | needs an isolated Mac or VM | pending |
| C — Mark Up with a box, a highlight and notes | **Missing** | `docs/media/screens/C-markup.png` | must be 0.3.1 (6) | needs an isolated Mac or VM | pending |
| D — Hand Off after saving | **Missing** | `docs/media/screens/D-handoff.png` | must be 0.3.1 (6) | needs an isolated Mac or VM | pending |
| E — Finder window of the mounted DMG (light and dark) | **Missing** | `docs/media/screens/E-dmg-light.png`, `E-dmg-dark.png` | candidate DMG `2c0e1adf…bf76` | needs an isolated Mac or VM | pending |

No placeholder, mock-up or reconstructed image was added for any of them. [`docs/screenshot-kit/README.md`](screenshot-kit/README.md) gives the owner exact instructions: which build, window sizes, the capture script, mark wording, privacy checklist and hand-over. It also includes a disposable demo frontend ([`demo-site/index.html`](screenshot-kit/demo-site/index.html), fictional “Tidewater” with three deliberate visual bugs), so A–D share one cohesive example. A headless Chrome render of the demo confirmed that all three bugs are visible.

To process the images once supplied, [`scripts/strip-png-metadata.py`](../scripts/strip-png-metadata.py) removes the XMP, Apple `iDOT`, EXIF, text and timestamp chunks that macOS screenshots carry. It copies image data byte for byte and never overwrites its input. Three regression tests cover it.

## C. DMG design

- **Actual Finder screenshot:** pending. No disposable GUI session.
- **Light and dark verification:** pending (`dmg-finder-light`, `dmg-finder-dark`).
- **Drag-and-drop install, eject and launch:** pending (`dmg-drag-install-eject-launch`). Doing this on the owner's Mac would replace the installed ContextLens, which this task forbids.
- **Layout changes:** none. The Twin Glass design, geometry and packaging are unchanged, because no real Finder observation exists to justify a change. The hosted candidate's DMG was re-verified with the private, no-browse mount: background, icon layout, filesystem, signatures and ZIP/DMG bundle equality (see E).

## D. Official release

- **Acceptance checklist:** every case in [`release-acceptance/template.json`](release-acceptance/template.json) remains `pending`. These include Gatekeeper first launch, Open Anyway, permission deny, grant and revocation, Low and High capture, Review and annotation, Hand Off, reopen and recovery, closure without substitution, target-app exit, ContextLens exit during capture, pending-frame persistence, failed-save retry, rapid start and stop, and the DMG Finder, drag and install cases. No case was observed, so `docs/release-acceptance/0.3.1.json` was **not** created.
- **Readiness:** the candidate is prepared and verified as packages: prepare run [42504640955](https://github.com/Brendan-Lim/ContextLens/actions/runs/42504640955), ZIP `1744796e…e501e`, DMG `2c0e1adf…bf76`. The Actions artifact **expires on 8 December 2026**. After that, a new prepare run and fresh acceptance are needed.
- **Docs-only commits do not invalidate the candidate:** `promote` requires the candidate source `11b099a` to be an ancestor of `origin/main`, which stays true.
- **Remaining blockers:** genuine interactive acceptance on an isolated Mac, the acceptance record, maintainer review, then `promote`. After publication: the stable cask from the published ZIP, and macOS 14 runtime testing.
- **Stable publication allowed:** **No.** The preview release, preview cask, Developer ID workflow and promotion gate are unchanged.

## E. Engineering verification

All on the local host above, run on 9 November 2026. The full gate (`scripts/ci.sh`, the same steps as hosted CI) ran in a disposable git worktree with an ad-hoc build. The owner's `dist/ContextLens.app` was not rebuilt or re-signed.

| Check | Result | Command |
|---|---|---|
| Swift unit tests | **106 passed** | `scripts/verify.sh` (inside `scripts/ci.sh`) |
| Coverage map | 46 public types covered | `python3 scripts/check-coverage-map.py` |
| Benchmark Python | **49 passed** | `python3 -m unittest discover -s Benchmarks/tests` |
| Package validation | **13 packages** | `python3 scripts/verify-packages.py` |
| Deterministic replays | **10 passed** | `python3 scripts/verify_replays.py` |
| Publication, release, DMG and link tooling | **57 passed** (53 before; plus 1 new `srcset` link test and 3 new PNG metadata tests, each confirmed failing first) | `python3 -m unittest discover -s scripts/tests -v` |
| Release build portability and CLI aliases | Passed | `python3 scripts/verify-release-build.py` |
| Homebrew templates | Syntax and semantics passed; no installable stable cask | `python3 distribution/homebrew/scripts/validate.py` |
| Development ZIP | Passed | `python3 scripts/release.py package … --development` |
| Development DMG: mount, filesystem, signature, layout, install copy | Passed; Finder appearance `pending-isolated-GUI` | `distribution/dmg/build-dmg.py` |
| Hosted candidate (exact bytes of run 42504640955) | SHA256SUMS OK; ZIP and DMG re-verified, exit 0 | `.build/dmg-python/bin/python scripts/unnotarized-release.py verify-assets .build/official-hosted-assets` |
| Owned browser fixtures | **10 defects reproduced, 10 controls passed** | `node Benchmarks/runners/verify-fixtures.mjs` |
| Node tests | **16 passed** | `node --test Experiments/…/unit.test.mjs …/export.test.mjs …/mapper.test.mjs` |
| Experiment Python | **4 + 8 passed** | `python3 -m unittest discover -s Experiments/visual-to-code/tests` (and `code-aware-efficiency`) |
| Publication audit: staged, tracked, history | 0 findings (history: 613 file versions, 551 blobs) | `python3 scripts/audit-public-files.py [--staged\|--history]` |
| Gitleaks 8.30.1, all reachable history | 0 findings | `python3 scripts/run-gitleaks.py` |
| Public links | 0 findings; `<source srcset>` now checked too | `python3 scripts/check-public-links.py` |
| README external URLs | All HTTP 200 | `curl -L` on each |
| README image validation | 4 new PNGs: lossless optimization verified pixel for pixel; PNG chunk policy passed; opened and inspected | `python3 Brand/readme/generate.py docs/media/readme` |

The first CI attempt failed on a single finding: a link to this report before the report existed. It was rerun after the report was added; no other check changed.

<!-- COMMITS -->

## F. Next actions for you

1. **Before 8 December 2026, set up a macOS VM** on this Mac (UTM or another Apple Virtualization front end). It is the isolated environment that both acceptance and the screenshots need. Your installed ContextLens and its permissions stay untouched.
2. **In the VM, download the candidate through a browser** from [run 42504640955](https://github.com/Brendan-Lim/ContextLens/actions/runs/42504640955), so it is quarantined, and check `SHA256SUMS`.
3. **Take screenshot E** (the Finder window, light and dark) when you first open the DMG. Then drag the app to Applications in the VM and record the Gatekeeper and Open Anyway behaviour you see.
4. **Record one Tidewater session and take A–D** as described in [the screenshot kit](screenshot-kit/README.md). Put the originals in one folder and tell me where they are.
5. **Work through the remaining acceptance cases** in [beta-acceptance.md](beta-acceptance.md) in the same VM. Write down the actual observations, and I can turn them into `docs/release-acceptance/0.3.1.json` for your review.
6. After you approve that record: dispatch `promote` with run 42504640955 and the typed confirmation. Then I update the stable cask from the published ZIP and swap the README download links to v0.3.1.
