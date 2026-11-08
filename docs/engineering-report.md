> Historical 0.1.0 implementation report. Current annotation/export behavior and checks are in [the 0.2.0 update](update-0.2.0.md).

# ContextLens — final MVP engineering report

6 November 2026 · macOS arm64 · local development build 0.1.0

## A. What was built

A working native SwiftUI application and command-line companion, independently implemented under MIT. The app has onboarding and permission recovery, a single-window picker/preview, start/stop/delay controls, Low/Balanced/High sensitivity, bounded capture, a manual snapshot hotkey, automatic meaningful-state selection and stop-flushing. A timeline supports selection, naming, ordering, deletion and image import. The annotation editor provides rectangles, directional arrows, freehand highlights, text, numbered issue markers and solid redaction, editable labels/coordinates, stable IDs, undo/redo, full-resolution inspection and session reopening.

The deterministic exporter produces portable manifest/report/metadata files, sanitized full frames, per-issue annotated evidence and context-padded crops. Every exported image has redactions burned into its pixels. The app previews the report/estimated payload and supplies export-folder, copy-path and Codex/Claude instruction actions. A reusable Codex skill and equivalent Claude workflow are included. Storage destination, explicit retention cleanup, local-session deletion and permanent local redaction are implemented.

There is no inference, network service, audio, telemetry, cloud upload or automatic agent execution in the app. Optional direct CLI invocation, MCP, DOM mapping, blur redaction, semantic event subscriptions and cross-platform capture are deferred. Solid redaction fulfills the MVP privacy tool. Accessibility supplies observed clicked roles rather than element labels or an AX event stream. Arrow/highlight regions can be repositioned numerically; direct drag-to-resize existing handles and a separate in-app 1:1 zoom control are polish work. Full-resolution images open through the native default viewer.

## B. Architecture

The pipeline is **selected window → sequential ScreenCaptureKit samples → actor-based luminance comparison/settling → committed PNGs → editable session/annotations → staged context package → explicit user handoff**.

Foundation-only `ContextLensCore` defines the versioned schema, bounds/path invariants, region-based selector and report generator. `ContextLensCapture` binds an exact window ID and process ID, refreshes geometry/scale, excludes ContextLens from the picker, and stops safely on target loss. SCScreenshotManager uses only `SCContentFilter(desktopIndependentWindow:)`; there is no display or replacement-window fallback. An actor retains the latest image and small comparison buffers rather than an unbounded queue or a video.

The selector compares global and 10×10 regional luminance differences, suppresses low-level noise, settles for 350 ms and bounds continuous-animation waiting at 1500 ms. Comparison buffers also retain original pixel dimensions so same-aspect resizing is preserved. Manual snapshots bypass deduplication. The pipeline samples approximately four times per second plus processing cost and writes only selected states.

CoreGraphics/ImageIO supplies one renderer for the editor and exported evidence. Annotation coordinates are normalized to the original screenshot, with top-left origin and explicit bounds checks. The exporter first burns redactions, then derives images and sanitized metadata in a staging directory, then atomically publishes a new folder. PNG was chosen for lossless native support instead of WebP. See [architecture](architecture.md), [privacy](privacy.md) and [schemas](../schemas/).

## C. Repository changes

| Location | Responsibility |
|---|---|
| `Package.swift`, `Sources/ContextLensApp/` | Native app, views, controller and lifecycle |
| `Sources/ContextLensCore/` | Models, streaming selector, context report |
| `Sources/ContextLensCapture/` | Window capture, processing actor, registered hotkey |
| `Sources/ContextLensImaging/` | Image decode/encode, overlays/crops, transactional exporter |
| `Sources/ContextLensCLI/` | Demo, validation, replay, export, permission probe and profile commands |
| `Tests/` | Sixteen Swift model, capture, selection, image and export tests |
| `schemas/`, `scripts/` | JSON schemas, offline semantic/schema checks, replay validation and app build |
| `Integrations/` | Validated Codex skill and portable Claude instructions |
| `Benchmarks/` | Ten browser tasks, locked Playwright, independent evaluator, telemetry/timing/harness/report tools |
| `docs/examples/` | Native screenshot, capture evidence, generated session and verified issue-fix demonstration |
| `.github/workflows/ci.yml` | Reproducible test/build/evaluator workflow; added locally, not yet executed on hosted CI |

The initial directory was empty. Git was initialized; no source history was overwritten and no remote was configured or published. Changes remain available in the working tree. The live harness independently creates and records baseline commits in each temporary trial project. [Dependency/licence review](dependency-audit.md) found zero third-party production package dependencies; the benchmark development dependencies are separately attributed and locked where applicable.

## D. Verification

| Check | Actual outcome |
|---|---|
| Debug build and Swift tests | **16 passed, 0 failed** |
| Release build | **Passed**; `dist/ContextLens.app` and `dist/contextlens-cli` produced and ad-hoc signed |
| Native launch | **Passed**; editor rendered and app exited normally |
| Selected-window native capture | **Passed** through ScreenCaptureKit, 2640×1720 at scale 2 |
| Native movement/resize/closure | **Passed**; same identity after movement, updated dimensions on resize, closed probe rejected without fallback |
| Python usage/harness/report tests | **13 passed, 0 failed** |
| Broken browser fixtures | **10/10 intended defects reproduced** |
| Known-good evaluator controls | **10/10 passed** |
| Baseline regression guards | **12/12 passed** |
| Production deterministic replays | **10/10 passed**, including committed metadata and encoded image bytes |
| Complete exported packages | **11/11 validated** through semantic checks and independent JSON Schema Draft 2020-12 |
| Redaction tests | Full-frame, overlay and crop pixels checked; originals remain separate |
| Agent skill validation | **Passed** with skill-creator validator |
| Handoff/fix demonstration | **CL-001 acceptance passed**, plus **12 regression guards** |
| Paid isolated agent trials | **Not run**; no spending authorization or operator timing was supplied |

Recorded artifacts: native verification (local-only evidence `examples/native-capture-verification-v1.json`), browser controls (local-only evidence `../Benchmarks/reports/fixture-validation.json`), replay validation (local-only evidence `../Benchmarks/reports/replay-validation.json`), demo fix checks (local-only evidence `examples/demo-fix-validation.json`), and environment (local-only evidence `../Benchmarks/reports/capture-environment.json`). The final browser checks used Playwright 1.62.1 and Chrome 156.0.8078.81.

The native test captures only an app-owned fixture. It does not establish that every real application, permission transition, display/Space move, auxiliary native popup, keyboard interaction or prolonged recording has been exercised. Accessibility role collection and a fresh-user denied/granted flow still need interactive checks. The minimum supported macOS 14 runtime was not available. Broad controller/UI soak testing, peak CPU/RSS profiling, Developer ID signing and notarization remain release work. Initial restricted-environment cache/network/WindowServer failures were resolved using project-local caches and permitted test execution; they are not outstanding build failures. See [native testing](native-testing.md).

## E. Example end-to-end workflow

1. **Capture:** launch the app, choose the intended window, preview and Start Capture. The native integration test verified selected-window pixels; scripted browser captures provide reproducible source events under `Benchmarks/reports/browser-evidence/`.
2. **Automatic selection:** replay the recorded samples using `dist/contextlens-cli replay EVENTS.json NEW_FOLDER`. Ten recorded sequences reproduce identical committed metadata and PNGs. The example browser data has 40 sampled frames and 11 selected states in total.
3. **Annotate:** the editor attaches structured CL IDs and explicit instructions to normalized regions. The browser task-01 session labels the misaligned confirmation button.
4. **Export:** [its actual manifest](../Benchmarks/reports/browser-evidence/01/contextlens/manifest.json) indexes a [focused crop](../Benchmarks/reports/browser-evidence/01/contextlens/crops/CL-001.png) and [annotated frame](../Benchmarks/reports/browser-evidence/01/contextlens/annotated/CL-001.png). [A separate generated session](examples/agent-session/context.md) also demonstrates irreversible export redaction.
5. **Agent consumption:** in this engineering conversation, Codex read task-01's actual manifest/report, opened its crop, expanded to the annotated screenshot for dialog context, then searched the fixture's source. The crop alone was insufficient to judge alignment; wider context mattered.
6. **Code modification:** in `docs/examples/fix-demo/styles.css`, `.actions` changed from `justify-content: flex-start` to `flex-end`. The benchmark's original defect source remains unchanged.
7. **Verification:** independent Playwright acceptance for task 01 and all twelve shared regression checks passed. After screenshot (local-only evidence `examples/fix-after.png`), [fixed source](examples/fix-demo/styles.css) and recorded checks (local-only evidence `examples/demo-fix-validation.json`) are included. This demonstration is **not** an isolated randomized benchmark and has no attributed token/preparation measurements.

## F. Token efficiency benchmark

The harness supports Manual, Auto-only and ContextLens, seeded schedules, fresh source copies/commits, exact provider/model/effort capture, complete traces, safe default permissions, process-group timeouts, target acceptance and regression guards. Codex 0.163.0 and Claude Code 2.1.303 were inspected without making paid requests. Parsers are tested against clearly labeled synthetic telemetry and do not double-count cumulative/nested usage.

**Actual isolated live trials: zero.** Actual provider usage, costs and operator preparation timings are unavailable. The machine-readable results (local-only evidence `../Benchmarks/reports/results.json`) explicitly contain zero trials and exclude synthetic telemetry. The generated report (local-only evidence `../Benchmarks/reports/benchmark-report.md`) contains individual-result and aggregate sections ready for real runs.

| Metric | Manual | Auto-only | ContextLens | Difference |
|---|---:|---:|---:|---:|
| Preparation time | N/A | N/A | N/A | N/A |
| Input tokens | N/A | N/A | N/A | N/A |
| Cached input tokens | N/A | N/A | N/A | N/A |
| Uncached input tokens | N/A | N/A | N/A | N/A |
| Output tokens | N/A | N/A | N/A | N/A |
| Total tokens | N/A | N/A | N/A | N/A |
| Agent execution time | N/A | N/A | N/A | N/A |
| End-to-end time | N/A | N/A | N/A | N/A |
| Agent cost | N/A | N/A | N/A | N/A |
| Success rate | N/A | N/A | N/A | N/A |
| Corrective iterations | N/A | N/A | N/A | N/A |

Codex cached input is separated from uncached input; Claude cache reads/creation are recorded separately. Missing fields are null. Reasoning tokens are retained when exposed, without adding them twice to output. Costs use provider-reported values only. Same-agent/model/settings comparisons are primary. There is no bytes-to-image-token estimator.

## G. Speed efficiency benchmark

No human preparation, isolated agent execution, end-to-end-to-success or corrective-iteration measurements exist yet. The interactive timer records observed T0/T1; live trials record T2/T3 and independent acceptance T4, queue delay, failed-attempt elapsed time, versions, patch and trace. Failures retain null time-to-success rather than looking artificially fast. The current harness evaluates first attempts and does not automatically purchase corrective iterations. Further operator corrections require an extended timed dataset, consistently collected across conditions.

The one measured processing microbenchmark ran **1,000 regional comparisons at 240×150**, averaging **0.0715 ms** on this Mac. This measures only the comparison function, excluding capture, enumeration, image decoding/encoding, UI work, human effort and agent latency. It establishes no workflow speedup or whole-app resource bound. Raw measurement (local-only evidence `../Benchmarks/reports/frame-comparison.json`).

## H. Quality and correctness

All ten intentionally broken task properties fail independent acceptance before correction, and all ten evaluator-only known-good controls pass. Twelve baseline-passing structure/interaction/no-JavaScript-error guards provide partial regression coverage. The CL-001 handoff demonstration passes its target acceptance and those guards.

These results validate fixtures and the demonstrated fix. They do not measure coding-agent first-attempt accuracy across workflows or show that visual context improved/degraded agent performance. The agent is not its own sole evaluator: Playwright assertions live outside the copied project. Human visual review and a wider regression suite remain necessary; no automatic visual proxy proves overall usability.

## I. Conclusions

1. **Did ContextLens save human preparation time?** Unknown; no operator-timed paired preparations have been collected.
2. **Did it reduce agent tokens?** Unknown; zero isolated paid trials. Smaller filesystem packages are not evidence of lower model usage.
3. **Did it reduce end-to-end completion time?** Unknown; no comparable time-to-accepted-result runs exist.
4. **Did it improve first-attempt accuracy?** Unknown; the one current-session demonstration is not a controlled comparison.
5. **Which export strategy performed best?** No agent-quality/efficiency winner can be identified. The following are measured **initial filesystem payloads** over ten scripted browser fixtures, not model-context or runtime measurements:

| Strategy | Initial images | Initial bytes | Actual tokens | Agent runtime/success |
|---|---:|---:|---|---|
| all-frames | 40 | 749,406 | N/A | N/A |
| deduplicated | 11 | 369,903 | N/A | N/A |
| annotated | 10 | 346,848 | N/A | N/A |
| manifest-first | 0 | 19,292 | N/A | N/A |

Manifest-first initially offers text and opens images later; the table excludes those later reads. All-frames includes repeated samples; deduplicated uses the production selector. No strategy may assume that less context preserves correctness. The crop→wider-frame expansion in the demonstration shows why progressive disclosure must permit additional evidence.

6. **Major bottlenecks?** The remaining experimental bottleneck is real operator-timed, authorized paired trials. Native capture/encoding and sustained CPU/memory still need profiling; the comparison microbenchmark alone cannot identify the system bottleneck. UI label edits currently re-render evidence, so large-image interaction warrants profiling.
7. **When does it perform worse?** Unmeasured. Plausible failure conditions include very small/low-contrast states, rapidly transient overlays, separate native popup windows, continuously animated UIs and annotation overhead for trivial tasks. These are hypotheses/limitations, not observed comparative outcomes.
8. **What should improve next?** Run the controlled study, broaden native testing, then tune detection and editing from measured misses and operator feedback.

The token/time/preparation/success charts in `Benchmarks/reports/` explicitly show live results pending; the separate payload chart (local-only evidence `../Benchmarks/reports/strategy-payload.png`) uses measured bytes. No scatter plot is emitted without sufficient live samples. The report generator calculates paired differences, medians/IQR, reduction percentages and speedups once real runs exist, and bootstrap intervals only for sufficiently populated pairs.

## J. Next steps

1. Collect authorized, same-model Manual/Auto-only/ContextLens trials on a counterbalanced schedule, immediately hand off each observed preparation, retain failures and record corrections consistently. Exact commands and limits are in [the benchmark protocol](../Benchmarks/README.md).
2. Perform the documented native permission/display/Space/application/hotkey/quit-during-recording matrix and sustained CPU/peak-memory profiling; fix any controller or detection misses before distribution.
3. Add direct drag handles, canvas zoom, debounced/background editor re-rendering and stronger visual accessibility based on user testing.
4. Extend objective acceptance/regression coverage, independent human visual review, first-attempt/corrective iteration telemetry and larger paired confidence intervals.
5. Add browser DOM/component mapping and optional role-aware Accessibility subscriptions without recording text values.
6. Explore explicit local MCP and agent-driven before/after verification; preserve user approval for capture and transmission.
7. Tune export strategies against **actual** provider tokens, success and runtime; retain full-context escape hatches.
8. Add Developer ID/notarized packaging, distribution testing, then platform-specific capture adapters behind the portable core.

The local MVP and reproducible experiment infrastructure are implemented. The central claim—saving human time, agent tokens or completion time—remains an open empirical question, deliberately unclaimed.
