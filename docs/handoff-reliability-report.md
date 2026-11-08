# Hand Off reliability and export hardening — 9 November 2026

This work is isolated on `codex/handoff-reliability`, based on `e07466c2a63706c9d5e292805b6085c105ffa6ee`, in a separate worktree. Claude Code's main checkout, index, branch and commits were not edited. No README, branding/media, DMG, release workflow, Homebrew cask or official acceptance record is changed by this branch. No native capture, permission changes, model invocation or release publication was performed.

## Export architecture and audit

| Boundary | Data and existing protection |
|---|---|
| Capture → saved session | `CaptureProcessor` writes PNGs before committing frame/selector sequence changes; frames record original pixel dimensions, display scale, timestamp and stable ID. `SessionStore.save` validates and atomically writes schema-1 JSON. |
| Review and Mark Up | Session metadata carries selected/reordered/renamed states and normalized top-left geometry. `SessionHistory` preserves monotonic issue counters across undo/redo. The app invalidates exports after edits and keys preview work by session, root, options and source revision. |
| Session → plan | `Session.validate` rejects duplicate/case-colliding IDs, invalid geometry/dimensions and unsafe relative paths. `SessionStore.resolve` rejects escaping symlinks. `ExportPlan` applies selection, annotation and exact decoded-pixel deduplication filters once. |
| Plan → images | One frame at a time is decoded; redactions burn into safe pixels before full frames, per-issue overlays, multi-mark overviews and crops are generated. Display scale does not multiply original normalized image coordinates again. |
| Images → package | `Exporter` writes manifest v2, sanitized session metadata, the self-contained brief, timeline and README into a unique sibling stage, then moves it to a new destination. It checks cancellation and cleans its own stage on thrown errors. |
| App / CLI → Hand Off | The app exports a prepared plan; CLI `export` calls the same exporter through its session overload. The app sets its output URL only after export returns and guards against session/options/root changes. Clipboard and native save-panel interaction remain a manual UI boundary. |

The audit read Core models, geometry, reports, selection/edit history and naming; capture persistence; Imaging plan/renderer/exporter; the CLI; app export preview/save/copy wiring; schemas; validators and existing tests. Existing guards were retained unless a failing regression demonstrated a gap.

## Confirmed defects and fixes

1. **Included source changed at unchanged dimensions.** A prepared plan accepted a replacement PNG of the same dimensions and silently exported different pixels. The failing Swift regression replaced a red synthetic frame with blue; old export succeeded instead of rejecting the stale plan.
2. **Duplicate omission became stale.** Two identical synthetic states produced a one-state plan. Replacing the omitted state's image after preparation still exported one state, silently losing a now-distinct state. The failing regression reproduced that omission.

   Both cases share a fix: plans retain SHA-256 digests for all candidate source files. Export verifies omitted duplicate candidates and reads each included image through a snapshot that hashes and decodes the **same owned bytes**. Mismatch throws a clear refresh/retry error, removes the current stage, leaves the destination absent and preserves saved session data. A fresh plan succeeds with the changed pixels. Digests are internal; existing public export entry points and serialized formats remain unchanged. Non-export editor/thumbnail loads do not acquire this extra hash.

3. **Bare carriage returns escaped instruction quoting.** A note containing `\r## Still user text` was not normalized by the Markdown quote helper, unlike LF/CRLF. A failing Core test reproduced the unquoted line boundary. The helper now normalizes CR, CRLF and LF before quoting each line; original session instructions are unchanged.
4. **PNG validation only inspected 24 header bytes.** The offline package validator accepted a truncated PNG header and PNG data with a changed CRC. Both failing Python regressions now reject. Validation streams chunk CRCs and DEFLATE scanlines through bounded buffers, checks filter bytes and completeness, and supports PNG bit depths/color types and Adam7 without a new dependency. Native ImageIO already rejected an incomplete one-row stream claiming a 600-row image; an actual CLI test pins that existing behavior rather than claiming a new decoder fix.
5. **Promised overview/timeline output was not validated.** The validator accepted a current-format brief referencing an absent state overview. It now checks current-format image references against the manifest, opens/validates the corresponding PNGs and requires the referenced timeline/frame paths. Legacy v1/v2 layouts predating overviews remain valid.
6. **Exported redaction-note validation was missing.** A package with a nonempty synthetic redaction instruction in metadata passed validation. The exporter already blanked these notes; no active generated-package note leak was found. The validator now rejects such metadata, and image/content tests retain the existing privacy guarantee.

Red-before-fix logs are retained locally under OS temporary storage, not committed. Tests themselves reproduce the cases with generated images and owned fixtures; no personal screenshot is used.

## Deterministic coverage

| Requested case | Evidence |
|---|---|
| Multiple annotations on one screenshot | Prepared/direct package comparison verifies a Box, Highlight, all issue PNGs and the combined state overview. |
| Marks across multiple states | Swift and actual CLI packages retain stable issue/frame links across two annotated states. |
| Different dimensions, resize and Retina | 100×80, 200×160 and 160×90 Swift fixtures; 128×80, 256×160 at scale 2, and a resized 180×120 CLI state. Output dimensions, overlay pixels and highlight crop bounds are checked. |
| Box / Highlight coordinates | Independent Python PNG pixel decoding checks the Box at normalized coordinates and the L-shaped Highlight, plus its 189×140 crop. Existing geometry and stroke tests remain. |
| Redacted derived images | Pixel checks cover full frame, per-issue overlay, combined overview and issue crop; source pixels remain unredacted locally. Redaction note is absent from brief, manifest and exported metadata. |
| Reorder, rename, deselect | Reopened session and CLI fixtures assert review order, Unicode names, timestamps/scale preservation and omission of deselected instructions. |
| Deleted marks / stable IDs | Gaps in CL IDs and the monotonic next counter survive export/reopen; deleted and deselected notes are absent. Existing undo/redo counter tests also run. |
| Spaces and Unicode paths | Source and output folders, source image filenames and notes use spaces, accented characters and CJK text. |
| Empty / incomplete sessions | Empty, deselected and corrupt sessions refuse publication. Actual CLI rejects an incomplete PNG stream with valid framing/CRCs. |
| Corrupt / missing source images | Missing second frame after preparation, corrupt image, same-size replacement and escaping symlink fail without final output. |
| Permission / destination failures | Real POSIX read-only parent and regular-file parent fail; parent markers remain intact. |
| Partial failure / retry | Missing second source after preparation exercises failure after writing the first frame's stage output, then restores/retries successfully. |
| Interrupted staging | A simulated orphaned hidden stage remains intact while a retry produces a separate valid package. This is not a live process-kill or power-loss test. |
| Repeated exports / no overwrite | Distinct destinations produce identical relative files/bytes; an existing package and dangling destination symlink remain unchanged on refusal. |
| CLI / application consistency | Session-overload and prepared-plan exports are byte-identical. The real CLI round trip independently verifies JSON, PNG pixels, references and two repeated packages. Native UI wiring is inspected, not interactively certified. |
| Escaping manifest paths | Schema/path traversal and output symlink escapes are rejected; generated paths remain relative and relocatable. |
| Self-contained handoff | Current brief/overview/timeline links validate; Core tests preserve every explicit request, optional context and stable references without inventing intent. |

## Verification

Local environment: Apple Silicon, macOS 26.6.2, Xcode 26.6 / Swift 6.3.3. All builds/tests and generated exports are in the isolated worktree or temporary folders. No owner installation or TCC state was used.

The initial baseline passed **106 Swift tests** and **49 benchmark Python tests**, then reported a missing `dist/contextlens-cli` in the fresh worktree. After building the CLI/app there and installing the existing pinned JSON Schema development validator locally, the baseline passed **13 packages with independent Draft 2020-12 validation** and **10 deterministic replays**. This setup failure is not an application defect.

Final validation commands and results are recorded before branch publication:

```sh
CONTEXTLENS_SIGN_IDENTITY=- scripts/build-app.sh
scripts/verify.sh
PYTHONPATH="$PWD/.build/benchmark-python" python3 -m unittest discover -s scripts/tests -v
python3 scripts/audit-public-files.py --staged
python3 scripts/audit-public-files.py
python3 scripts/audit-public-files.py --history
python3 scripts/run-gitleaks.py
python3 scripts/check-public-links.py
```

Final local checks pass: **116 Swift tests**, **63 script tests**, **49 benchmark Python tests**, **13 legacy packages with independent Draft 2020-12 validation**, and **10 deterministic replays**. The two actual CLI tests include the synthetic pixel/schema round trip and rejection of an incomplete image stream. Hosted CI links are added after the implementation commit and PR exist. Independent schema validation is also performed on both new temporary CLI exports, not only the 13 legacy fixtures. No media approval-policy change is needed: all new image data is generated in temporary test folders.

## Limitations and release impact

- Native save-panel, clipboard, error presentation and capture-to-Hand-Off UI interactions still need a person in a disposable GUI environment. Existing Gatekeeper, Screen Recording, capture closure and recovery acceptance remains unchanged; these unit/CLI tests do not replace it.
- Ordinary thrown errors/cancellation clean the current stage. A crash, forced kill or power loss can leave recoverable hidden staging data. No automatic cleanup deletes another stage or user data. Disk-full and power-loss fault injection were not run on the owner's machine.
- Source bytes are bound per candidate/read; no filesystem lock or global cross-file transaction is claimed against an adversarial concurrent writer. Container-only edits also require a fresh plan. Hashing adds one SHA-256 per candidate at preparation and verification; no unmeasured performance claim is made.
- The Python validator checks PNG structure and cross-file invariants, not semantic image content, OCR or the visual correctness of every possible imported file. Pixel privacy/geometry evidence comes from the synthetic renderer/CLI tests.
- Session schema **1**, manifest schema **2**, output names and existing public APIs are preserved. Legacy fixture packages still validate; unsafe nonempty exported redaction notes are intentionally rejected.
- These production Core/Imaging changes require a **new app build after merge**. Previously prepared release binaries do not include them. Prepare a fresh exact-source candidate and repeat applicable release acceptance; do not promote an older candidate merely because its source remains an ancestor of main. This branch does not modify the release workflow's ancestry policy or any acceptance record.
- Source binding and error text may affect native stale-preview recovery UX; verify refresh/retry in the isolated UI checklist. No token-efficiency, model-runtime or task-completion improvement is claimed.

## Changed files and review

Production: `Sources/ContextLensImaging/Images.swift`, `ExportPlan.swift`, `Exporter.swift`; `Sources/ContextLensCore/ContextReport.swift`; `scripts/validate_package.py`.

Tests: `Tests/ContextLensImagingTests/HandoffReliabilityTests.swift`, `Tests/ContextLensCoreTests/HandoffReportTests.swift`, `scripts/tests/test_handoff_validation.py`, `scripts/tests/test_handoff_cli.py`.

Documentation: `docs/export-format.md`, this report. No files owned by the concurrent product/branding task are changed.

The branch is intended to be safe to merge after review and green automated checks, while preserving all existing manual release gates. Commit/PR URLs and final hosted results are appended after publication of the review branch. It will not be merged automatically.

### Concurrent-ref audit boundary

Staged and tracked-file audits passed with zero findings. The shared repository's all-ref history audit then found **four history-only `unreviewed-asset` findings** for Claude Code's new `docs/media/readme/` media, which had been committed concurrently on main. This branch intentionally retains its baseline publication policy and does not copy or change another agent's approvals. The independent Gitleaks scan of all shared reachable history returned zero findings. A separate, full, non-shallow single-branch clone of this review branch is used for its final complete-history publication audit; results below apply to that branch and its ancestors, not certification of concurrent product/media work.

## Published review branch and final results

- Implementation commit: [`70ba081cb880ba862728b88c838cac97c0f519fe`](https://github.com/Brendan-Lim/ContextLens/commit/70ba081cb880ba862728b88c838cac97c0f519fe).
- Review PR: [#1 — Reject stale Hand Off inputs and validate package integrity](https://github.com/Brendan-Lim/ContextLens/pull/1), against main. It remains open and is not merged.
- [Full PR CI 42508792402](https://github.com/Brendan-Lim/ContextLens/actions/runs/42508792402) passed on the merge preview with main `f2d6d6069e6bdc8d3e570a8d34bc635bd433f7d5`: **116 Swift tests**, **67 script tests** (the isolated branch's 63 plus concurrent main's four additional tests), **49 benchmark tests**, **13 independently schema-validated packages**, **10 deterministic replays**, and **10 browser defects / 10 known-good controls**. Existing build, portability, archive and DMG checks also passed; this is not native capture acceptance.
- [PR Publication Security 42508792397](https://github.com/Brendan-Lim/ContextLens/actions/runs/42508792397) passed, including the merged main policy for its concurrent assets. This does not attribute those media changes or their review to this branch.
- The independent branch clone is full/non-shallow: its complete reachable-history audit inspected **624 path/blob versions / 562 blobs**, with **zero findings**. Tracked audit: **534 file versions**, zero findings. Independent Gitleaks: **zero findings**. Public link audit: **88 Markdown files / 128 local links**, zero findings. A report-only follow-up adds the links in this section and is scanned again before push.
- GitHub's PR file list confirms exactly the 11 Hand Off files listed above, with no forbidden product/release paths. The PR was reported mergeable (`CLEAN`) after these checks. Only the isolated review branch was pushed; main and the concurrent checkout/index were not written to.

**Review disposition:** safe to merge after human review and green current checks. Preserve all manual native/release acceptance, prepare new release binaries after merge, and do not auto-merge this PR.
