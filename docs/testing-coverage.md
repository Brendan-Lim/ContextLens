# Behavioral coverage audit

Audited 2026-11-07. “Tested” means the listed behaviors have executable checks, not that every branch or OS interaction is covered. “Needs a person” includes OS permission, desktop input, filesystem dialogs and real display behavior. Tests live under `Tests/`; baseline Python, schema and production replay checks run through `scripts/verify.sh`. `python3 scripts/check-coverage-map.py` detects newly added public types without a row; it does not measure line coverage.

| Public type | Status | Proven behavior and remaining limits |
|---|---|---|
| `LensError` | tested | Validation errors propagate; localized descriptions exercised by failed paths. |
| `Region` | tested | Finite normalized positive bounds; rejected outside regions; edge crops. |
| `Point` | tested | Session round trip and invalid stroke point rejection. |
| `AnnotationKind` | tested | Legacy decoding and creation tools restricted to box/highlight. |
| `Annotation` | tested | Round trip, geometry, redactions, stable references and labels. |
| `Frame` | tested | Metadata validation, dimensions, selection and capture reasons. |
| `SessionMode` | tested | Legacy modes round trip in sessions/packages; no active mode switch. |
| `Session` | tested | Stable IDs, duplicate/case collision rejection, counters, invalid point rejection before mutation, validation. |
| `SessionStore` | tested | Atomic round trip, traversal and escaping symlink rejection. Concurrent hostile symlink replacement is outside the storage threat model. Actual power loss needs a controlled machine. |
| `LumaFrame` | tested | Buffer/source dimensions; multiplication overflow rejected without a trap. |
| `Difference` | tested | Pixel threshold boundary, partial tiles, regional/global changes, original-dimension resize. |
| `Sensitivity` | tested | Low/High public choices, legacy balanced replay, localized changes and noise. |
| `FrameSelector` | tested | Initial/dedup/manual, settle/maximum wait, resize, frame limit, out-of-order, scroll hold/flush and A→B→A through replays. Real animation perceptual usefulness needs a person. |
| `Selection` | tested | Reason/score returned and carried into captured metadata/replays. |
| `AnnotationGeometry` | tested | Stroke bounds and clamping; exported L-shaped stroke and matching crop. |
| `ZoomState` | tested | Anchor invariance, clamping, letterboxing, keyboard steps and zoom range. Native input delivery and perceived smoothness need a person. |
| `StateNamer` | tested | Click labels, title changes, scroll/manual/fallback naming, whitespace/length. Real Accessibility element trees need a person. |
| `PackageName` | tested | Slugs/date/timezone, fallback, collision suffixes, prompt quoting. Filesystem races fail safely in exporter. |
| `AnnotationSummary` | tested | Compact manifest excludes precise points/regions and retains issue IDs/instructions. |
| `ExportIssue` | tested | Relative annotated/crop paths exist and remain portable after moving export. |
| `Manifest` | tested | Schema-v2 encoding, v1 compatibility through independent package validator; summaries/options. |
| `ContextReport` | tested | Explicit task/instructions first, unlabelled references, no inferred intent, review order/placement, exact prompt entry path, one overview per marked state, optional complete timeline, 80-request preservation and unmarked fallback. |
| `ExportOptions` | tested | Four combinations and defaults; all annotated copies protected. |
| `ExportSummary` | tested | Sequential exclusion counts, unlabelled counts, estimate and preview/export agreement. |
| `SessionHistory` | tested | 50-state default/bounded history, redo branching/reset/disabled history, counters survive undo/redo. |
| `EditorRenderRequest` | tested | Notes/name/task/ticks do not invalidate pixels; geometry, source and revision do. |
| `FrameSelection` | tested | Existing unticked selection remains visible; deleted/missing selections fall back; empty sessions. |
| `ScrollActivity` | tested | Matching topmost window identity, finite uptime, 500 ms quiet boundary, backward time. |
| `CostCache` | tested | Byte limit, LRU promotion/eviction, replacement, oversized/negative rejection, reset, 10,000 insert stress. |
| `Images` | tested | PNG round trip, luminance, pristine preservation, burned redactions, crop edges, highlight strokes, original dimensions. Imported EXIF/orientation/color profiles and malformed image fuzzing remain untested: a representative file corpus is not supplied. |
| `ImagePipeline` | tested | Thumbnail dimensions/reuse/byte cap/revision, source reuse, reload after redaction, cancellation before decode, corrupt/missing inputs and metadata mismatch. Cancellation during ImageIO cannot interrupt the synchronous decoder; publication is checked afterward. |
| `ExportPlan` | tested | All filters, decoded-pixel duplicate semantics, annotation protection, source dimensions, source stays unchanged, empty preview. Color-profile diversity remains untested without a corpus. |
| `Exporter` | tested | Every derivative redacted, original-resolution combined state overviews, retained per-issue images and optional timeline, portable paths, overwrite rejection, atomic cleanup, pre-cancelled export and source corrupted after preview. Disk-full/permission failures require controlled filesystem conditions. |
| `WindowChoice` | needs a person | OS-owned SCWindow titles, app names and identity; self-window native checks exercise real metadata, not every external app. Cannot construct arbitrary SCWindows in pure tests. |
| `Permissions` | needs a person | TCC/AX approval, denial, revocation and relaunch flows require OS settings. Passive API gate separately tested. |
| `WindowCapture` | tested / needs a person | Empty identity lookup never substitutes; native own-window movement/resize and closure probe recorded. External windows/displays/Spaces and minimized/reopened targets need a person. |
| `CaptureProcessor` | tested | Real CGImages through sample/settle/resize/stop; original scale/dimensions; stale samples cannot replace pending flush; failed disk writes retry without consuming state/sequence. |
| `ScreenAccessProbe` | tested | Passive first launch does not prompt; explicit/stale/preflight paths attempt API and propagate actual failures. |
| `SnapshotHotKey` | needs a person | Carbon registration, conflict and real hotkey delivery require a desktop. No general keyboard monitor exists. Registration failure reporting is untested. |

App controller and view behavior:

| Behavior | Status | Evidence / limit |
|---|---|---|
| Capture start, delayed cancellation, stop, quit/in-flight flush | tested / needs a person | Processor flush/retry/cancellation tests cover worker logic. Controller changes check cancellation before processing and surface save failures. Full task lifecycle, delayed UI state and quitting require a desktop workflow; no isolated app target test harness exists. |
| Scroll-wheel monitor feeding holding | tested / needs a person | Pure ScrollActivity and selector tests; OS pointer/topmost-window query needs desktop verification. |
| Click-label naming | tested / needs a person | StateNamer pure tests. AX label retrieval, editable/secure descendants and topmost click gating require real accessibility trees. No typed key stream is observed. |
| Export folder choice and memory | tested / needs a person | PackageName collision behavior/export overwrite tested. NSOpenPanel and UserDefaults last-folder persistence need a person; the dialog is OS UI and cannot be driven in a background launch. |
| copyPrompt | tested / needs a person | ContextReport prompt content/path/task tests. Pasteboard interaction and user paste need a person. |
| Review / Mark Up selection rules | tested / needs a person | FrameSelection tests; native snapshots. Clicking/keyboard selection/focus need a person. |
| Undo/redo | tested / needs a person | SessionHistory extracted from AppModel; bounded snapshots, redo branch and monotonic counters tested. UI gesture coverage and text-field undo grouping need a person. |
| Editor image scheduling | tested / needs a person | Render request equality/pipeline tests; cancellation and request equality gate stale publication. Native large-session render checked. Actual keystroke-to-display latency and zoom/pan FPS require interactive instrumentation. |
| Thumbnail scheduling | tested / needs a person | Pipeline tests, lazy horizontal strips, release on disappearance, 100/500-frame synthetic measurements. Scroll smoothness needs a person. |
| Storage cleanup, deletion and permanent local redaction | tested / needs a person | Safe paths and renderer/export privacy tested. File replacement, retention UI, partial failure and destructive confirmations need a disposable session and a person. Redaction invalidates image revisions even after partial failure. |
| Diagnostics | tested / needs a person | Only static messages plus numeric timing/count values are emitted. No content, paths or raw error strings are logged. OS log retention/viewing is machine policy, not an app-owned store. |

Known untested automated scope is explicit above: imported-image corpus/fuzzing, native event delivery, TCC/AX lifecycle, dialog/pasteboard integration, disk-full/filesystem faults, task lifecycle UI and actual display latency. Those entries are not presented as green because another layer has unit tests.
