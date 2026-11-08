# ContextLens — agent guide

ContextLens is a native, local-first macOS 14+ app (SwiftUI + ScreenCaptureKit, SwiftPM, zero production dependencies). It records one chosen window's UI states, lets a person box or highlight what should change, and saves a hand-off package (`context.md`, `manifest.json`, crops, frames) plus a prompt for a coding agent. Nothing is uploaded and no agent runs automatically.

Rules every change keeps (privacy, redaction, no window substitution, stable IDs, licensing): [CONTRIBUTING.md](CONTRIBUTING.md). Package format: [docs/export-format.md](docs/export-format.md). Architecture: [docs/architecture.md](docs/architecture.md).

## Layout

| Target | Holds | Tested by |
|---|---|---|
| `ContextLensCore` | Pure logic: models, `FrameSelector` (state detection, scroll hold), `ContextReport` (context.md + prompt), `Naming` (state names, package folder names), `ZoomState` | `Tests/ContextLensCoreTests` |
| `ContextLensImaging` | Rendering, crops, export plan and exporter | `Tests/ContextLensImagingTests` |
| `ContextLensCapture` | ScreenCaptureKit window capture, `CaptureProcessor` actor, permissions, hotkey | `Tests/ContextLensCaptureTests` |
| `ContextLensApp` | SwiftUI app: `AppModel`, `CapturePanel` (floating panel + recording pill), `MainViews` (Review / Mark Up / Hand Off), `Theme`, `Brand` | no test target — see *Testing* |
| `ContextLensCLI` | `contextlens-cli`: `demo`, `validate`, `export`, `replay`, `profile`, `permissions`, `windows` | `scripts/verify_replays.py` |

When logic in the app target needs a test, move it into Core as a pure type first (the pattern `ZoomState`, `StateNamer` and `PackageName` followed), then test it there.

## Build and verify

- `scripts/build-app.sh` builds and signs `dist/ContextLens.app` and `dist/contextlens-cli`.
- `scripts/verify.sh` is the baseline gate: Swift tests, Python tests, package and replay verification. Green on 2026-11-07: 48 Swift tests, 13 Python tests, 10 deterministic replays.
- Benchmarks and browser fixtures: [Benchmarks/README.md](Benchmarks/README.md).

## Driving the app without a person

Launch the binary directly with these flags. Test launches are **background launches**: `--smoke-snapshot` and `--exercise-zoom` skip app activation, so the person's frontmost app keeps keyboard focus.

| Flag | Effect |
|---|---|
| `--session <dir>` | Open a session folder (one containing `session.json`) |
| `--tab review\|mark-up\|hand-off` | Open on a tab |
| `--frame <frame-id>` | Select a state, e.g. `frame-002` |
| `--preview <frame-id>` | Open Review's full-size preview |
| `--zoom <n>` | Open Mark Up's canvas at zoom `n` (1–4) |
| `--smoke-snapshot <png>` | Render the window to a PNG after ~3 s, then quit |
| `--snapshot-scale 2` | Render that snapshot at 2× whatever display the window is on |
| `--native-capture-test` | Also capture the app's own window through ScreenCaptureKit and write `native-capture-verification.json` beside the PNG |
| `--exercise-zoom <json>` | Post real ⌘-scroll events at five points and check the image point under the pointer stays put; writes a pass/fail report |
| `--capture-preview` | Open the capture panel on launch |
| `-NSRequiresAquaSystemAppearance YES` | Force light mode |

Example: `dist/ContextLens.app/Contents/MacOS/ContextLens --session /tmp/s --tab mark-up --frame frame-002 --snapshot-scale 2 --smoke-snapshot /tmp/markup.png`

Sessions to test with: `dist/contextlens-cli demo <dir>` makes a 3-state session (960×600 frames, one mark). For `--exercise-zoom`, overwrite its three frames with a 960×600 PNG whose colour encodes position (red = x, green = y) and set `annotations` to `[]` in `session.json`; then a matching colour before and after zoom means the same image point stayed under the pointer.

## Traps

- **Focus.** Events posted with `NSApp.postEvent` reach a window only while the app is frontmost, and clicking a background window brings it forward, taking the person's keystrokes. Verify interactions through background launches, pure Core tests, or by asking the person to perform them.
- **Signing and permissions.** Screen Recording approval is tied to the code signature. `build-app.sh` signs with the first "Apple Development" identity it finds; an ad-hoc build loses approval on every rebuild. Repair steps: [docs/permissions.md](docs/permissions.md).
- **Snapshot gaps.** `--smoke-snapshot` uses `cacheDisplay`, which leaves Hand Off's left column blank. Judge Hand Off from `--native-capture-test` output, which uses ScreenCaptureKit and needs Screen Recording.
- **Known failing check.** `native-capture-verification.json` reports `"status": "failed"` because `closure_detected_without_fallback` is false; movement and resize pass. This predates current work; treat a change in the other fields as the regression signal.
- **Native probe focus.** `--native-capture-test` currently calls `makeKeyAndOrderFront` for its closure probe. Its smoke/background launch does not prevent that probe from taking focus. Run it only in a disposable interactive macOS environment, following [beta acceptance](docs/beta-acceptance.md); do not use the owner's current app/TCC identity to simulate first run.
- **Restored window state** can suppress the main window in a test launch; the app then opens a stand-in fixture window whose model is `LensDelegate.model`. `NSApp.delegate` is SwiftUI's wrapper, not `LensDelegate`.
- **Oversized SwiftUI children** inside a fixed `.frame` are centred, not top-left aligned. Zoomed content therefore lives in an `.overlay(alignment: .topLeading)`; keep it that way or zoom-to-pointer drifts.
- **Shell.** `rg` and `timeout` are not installed: use `grep`, and `perl -e 'alarm 60; exec @ARGV' <cmd>` for a time limit.

## Testing and performance handoff

The goal is a **rigorous** pass: every claim in the README and docs either proven by a repeatable command or reported as unproven, and every bug found pinned by a test that goes red before the fix. Work through the steps in order.

1. **Baseline.** Run `scripts/verify.sh`. Done when it is green, or when each failure is reported with its output.
2. **Coverage map.** Read every public type in Core, Imaging and Capture and list the behaviours with no test. Also list the logic that lives only in `ContextLensApp`: capture start/stop, the scroll-wheel monitor feeding `holding`, click-label naming, export folder choice and memory, `copyPrompt`, Review/Mark Up selection rules, undo/redo. Done when every public type and every app-target behaviour is marked *tested*, *untested*, or *needs a person*.
3. **Close gaps.** For each untested behaviour that can be pure, extract it to Core and add tests. Done when the map's *untested* column is empty or each remaining entry says why it cannot be tested automatically.
4. **Native checks.** Run the background-launch flags above on Review, Mark Up (with `--zoom` and `--exercise-zoom`, at `--snapshot-scale 2`) and Hand Off, in dark and light mode. Done when each produces an image or report you have opened, and each defect is written down with the command that reproduces it.
5. **Interactive checklist.** Work through the release checklist in [docs/native-testing.md](docs/native-testing.md). Mark each item *pass*, *fail* or *needs a person*, with evidence. Ask the person before recording or capturing any window but the app's own.
6. **Performance.** Measure, on this machine, with the build's git hash:
   - Capture loop CPU % and peak resident memory over 10 minutes of a busy window (scrolling, video) at Low and High sensitivity: `top -pid`, `footprint`, or `xctrace record --template 'Time Profiler'`. The sampling task runs at ~4 Hz; frames past the selector are only encoded when committed.
   - States saved per minute for the same runs, and whether continuous scrolling becomes one "Scrolled" state.
   - Mark Up responsiveness on 2× frames: typing a note re-renders the editor image (`AppModel.renderEditor`), so measure keystroke-to-frame latency and zoom/pan frame rate.
   - Export time and package size for a 100-state session (`contextlens-cli export`).
   - Comparator microbenchmark: `dist/contextlens-cli profile` (earlier result: Benchmarks/reports/frame-comparison.json (local-only evidence `Benchmarks/reports/frame-comparison.json`)).

   Done when each metric has a number, the exact command, the machine and macOS version, saved as JSON under `Benchmarks/reports/`.
7. **Report.** One markdown summary: what passed, what failed (with reproduction commands), what needs a person, and the performance table. Keep measured numbers separate from estimates, as [CONTRIBUTING.md](CONTRIBUTING.md) requires for benchmarks.
