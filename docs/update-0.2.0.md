# ContextLens 0.2.0 — annotation and export update

Implemented the agreed two-tool workflow and export selection controls.

- New marks use **Rectangle** or **Highlighter**. Highlighter renders a rounded translucent freehand stroke while dragging and in saved/exported evidence. Bounds include stroke width; the editor no longer previews highlights as rectangles. Tiny accidental rectangle clicks are ignored.
- Older annotation kinds remain readable/editable in existing sessions, and their evidence is retained. No removed tool appears in the creation toolbar. Existing redactions continue to be burned into all output derivatives.
- **Only include annotated frames** and **Exclude duplicate frames** are independent switches, initially enabled. Every annotated frame is retained, even with an empty label or identical screenshot. Unannotated duplicates are compared by decoded image pixels, including dimensions; no approximate visual threshold is used.
- One prepared selection supplies the preview, counters, exclusion breakdown, manifest, report and images. No frames or annotations are deleted from the recording. Empty selections explain how to adjust filters and disable export.
- An optional overall task is persisted. Reports put user instructions before the timeline; marks without labels are included as references without invented change requests. Version-2 manifests omit raw stroke geometry, which remains in metadata/session.json. Validators and the bundled agent skill support both manifest versions.
- Export planning is debounced, runs off the UI thread and cancels superseded work. Changing filters, labels or the task clears the previous handoff links, preventing accidental reuse of an outdated package.
- Saved-image rendering is deferred until the view opens, and decoding uses Foundation data reads before ImageIO.

## Verification

- **24 Swift tests passed**, including all four filter combinations, blank labels, protected annotated duplicates, PNGs with different metadata but identical pixels, single-pixel changes, legacy marks, highlighter shape, empty selections and original-session preservation.
- **13 Python tests passed**, **13 public example packages validated** with semantic and independent Draft 2020-12 checks, and **10 recorded production replays passed**.
- The real user-supplied Downloads example was copied into ignored local test storage and re-exported in all four combinations. Its original files were not modified. All four outputs passed independent schema/semantic checks and retained all ten annotations.

| Export options | Included frames | Unannotated excluded | Duplicates excluded | Retained annotations |
|---|---:|---:|---:|---:|
| Include all, keep duplicates | 11 | 0 | 0 | 10 |
| Include all, exclude duplicates | 8 | 0 | 3 | 10 |
| Annotated only, keep duplicates | 4 | 7 | 0 | 10 |
| Annotated only, exclude duplicates | 4 | 7 | 0 | 10 |

The original manifest was 30,021 bytes. The new all-frame manifest measured 7,618 bytes; the focused manifest measured 4,873 bytes. These are filesystem measurements, not provider token savings. Raw drawing detail remains available in the package metadata. [Recorded filter results](examples/export-filter-validation.json).

A native mouse-event test created a freehand highlighter annotation with six points in a generated demo session. The export view was visually checked with its two enabled switches, optional task, matching report and retained-frame counts. [Native update check](examples/annotation-update-verification.json). Local view-cache snapshots are kept under `.build/`; that rendering method can omit the compositor-backed sidebar.

Screen Recording was not granted to the rebuilt app during the native recheck, so ScreenCaptureKit verification for this build is **blocked**, not claimed as passed. No permission prompt was requested by testing. The initial 0.1.0 native capture/move/resize/closure check remains archived separately. Re-enable Screen Recording for the rebuilt app before recording if needed.

A command-line smoke launch stalled reading generated images from the protected project Documents directory; the same UI fixture completed from an OS temporary directory. Normal session opening uses the native folder picker. Broad real-application permission/display soak checks remain on the native testing checklist.

The updated app is `dist/ContextLens.app` (0.2.0, ad-hoc signed). Quit and reopen it to replace an already-running older executable. See [export rules, schema compatibility and CLI switches](export-format.md).
