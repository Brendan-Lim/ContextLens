# Implementation progress — 6 November 2026

- Inspected an empty project on macOS 26.6 arm64; Xcode/Swift 6.3.3, Python 3.9.6 and Node 24.13.0 available. Initialized Git. Compiler caches were redirected into `.build` for restricted execution.
- Reviewed competitor public docs and licences; chose independent MIT source, native SwiftUI and zero production package dependencies.
- Built Foundation models/validation, regional frame selection, settling/deduplication, and observed-original-dimension tracking. Tests cover caret noise, local changes, continuous animation, bounds, manual snapshots, limits and same-aspect resizing.
- Added selected-window ScreenCaptureKit sampling, bounded actor processing, mouse role metadata, registered hotkey and stop/flush handling. No keyboard event stream is collected.
- Built capture/onboarding, timeline, annotation, export and storage/privacy views. Implemented persistence, import, stable IDs, position editing, undo/redo and local redaction/deletion.
- Implemented staged portable exports and versioned schemas; tests validate all image derivatives are redacted, coordinates match top-left origin, unsafe/symlink/case-colliding paths are rejected, and incomplete exports are not published.
- Built/released and launched the ad-hoc signed native app. ScreenCaptureKit captured only the app's own generated fixture window; saved native editor evidence.
- Added Codex skill and Claude portable instructions; validated the skill. Kept app handoff to explicit export/copy actions without launching a paid agent.
- Added ten browser defect tasks, evaluator-only known-good controls, twelve independent baseline-passing regression guards, locked Playwright, fixture capture, production replay and package validation.
- Added Codex/Claude usage parsers, no-cost seeded schedules, operator preparation timer, isolated first-attempt trial harness, timeout/process-group handling, exact version/trace/patch recording, honest failure accounting and Matplotlib reports.
- Verified ten deterministic browser replays and eleven complete packages through semantic and independent Draft 2020-12 checks.
- Consumed an actual exported CL-001 crop and wider annotated frame in this engineering conversation, fixed modal alignment in a separate fixture copy, and passed acceptance plus twelve guards. Kept this demonstration outside live benchmark statistics.
- Final gates: 16 Swift tests, 13 Python tests, 10 broken/10 known-good browser controls, 12 regression guards, release build and native integration evidence. Paid agent trials and human-timed comparisons remain pending; no savings are claimed.

## Annotation/export revision — 0.2.0

- Replaced the six-tool creation toolbar with Rectangle and Highlighter; fixed live freehand stroke preview and bounds while retaining legacy decoding/redactions.
- Added independent annotated-only and duplicate-exclusion filters, exact decoded-pixel hashing, protected annotated frames, consistent preview/package selection and empty-state handling.
- Added an optional overall task, instructions-first reports, unlabelled-reference grouping and compact version-2 manifests; retained full geometry in metadata and version-1 validation.
- Passed 24 Swift tests, 13 Python tests, 13 package validations and 10 replay fixtures. The actual Downloads example re-exported to 11/8/4/4 frames with all 10 annotations retained.
- Exercised a native freehand drag and inspected the export preview using generated temporary fixtures. Current Screen Recording recheck is blocked by missing permission; it was not requested automatically. Initial MVP native verification remains separately archived.

## Permission/signing correction — 0.2.1

- Confirmed the old bundle's designated requirement was pinned to its ad-hoc binary hash despite an enabled Settings entry reported by the user.
- Changed local builds to the available Apple Development certificate; verified the new certificate/identifier-based designated requirement and bundle integrity. No privacy permissions were reset and the user's running app was not quit.
- Added explicit ScreenCaptureKit access verification despite false preflight, refresh on reactivation, actionable recovery text and running-copy identification.
- Passed 28 Swift tests. Fresh macOS consent for the new identity remains a user step; actual capture is not claimed as verified under the new identity yet.

## Confirmed permission repair

- Read targeted macOS capture-service logs and confirmed an old ad-hoc requirement mismatch for the active ContextLens process; repeated Settings approval had not cleared it.
- Obtained explicit user approval, reset only ContextLens Screen Recording via the supported tccutil command, and relaunched it with a preserved signed-bundle backup.
- User confirmed windows now appear. Actual generated-window pixels were captured successfully; movement and resize checks also succeeded. A separate tight 200 ms closed-probe enumeration observation is recorded without claiming it passed.
- Changed bundle publishing to staged signing/verification and rename-based replacement; verified identical signing requirements and distinct executable inodes across a rebuild.

## Capture simplification — 0.2.2

- Removed the mode selector and the mode setting from the app controller; all new sessions use the same workflow. Existing metadata formats still decode older modes.
- Capture sensitivity now exposes Low and High only, defaulting to High. Archived benchmark replay explicitly retains the original detector configuration so historical measurements are not rewritten.
- Moved duplicate filtering, frame limit and delay under collapsed Capture options. Removed redundant preview/import buttons from Capture and grouped session/import/storage/help actions in More.
- Selecting a window loads its preview; no source is selected automatically, so capture remains an explicit window choice.
- Verified the simplified native layout, successful own-window capture and retained permission after the 0.2.2 rebuild. 29 Swift tests, 10 archived production replays and 13 package validations passed. Legacy auxiliary smoke heuristics are documented separately rather than counted as passing.
