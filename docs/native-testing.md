> Current preview status: **interactive acceptance remains pending**. Use the [isolated acceptance procedure](beta-acceptance.md) and [public readiness report](public-beta-readiness.md). The historical artifacts below remain local-only; they are not checked-in first-run proof. The retained native self-test reports a closure-check failure, and `--native-capture-test` creates a key probe window, so do not run it on the owner's active desktop.

> Expanded historical verification, coverage and performance evidence: rigorous testing report (local-only evidence `testing-report.md`). Historical checks below retain their original scope.

> Permission recovery and stable local signing were updated in 0.2.1; see [permissions](permissions.md). Earlier ad-hoc build checks below are historical.

# Native integration testing

Verified on the supplied arm64 Mac with Swift 6.3.3 and Xcode's macOS 26.5 SDK. Deployment target is macOS 14; macOS 14 hardware/runtime was not available for execution. Development builds use an available Apple Development identity, otherwise ad-hoc signing, with bundle ID `dev.contextlens.app`. The CLI is embedded and also copied to `dist/contextlens-cli`. Developer ID distribution is a separate [release workflow](releasing.md).

Automated evidence is in initial MVP native check (local-only evidence `examples/native-capture-verification-v1.json`), native-editor.png (local-only evidence `examples/native-editor.png`), and the Swift test suites. A real app window was launched and rendered. Where already granted, the self-test uses ScreenCaptureKit's desktop-independent selected-window filter against **only that app's own generated fixture window**; it never takes a display screenshot. The test command does not request permission when unavailable:

```sh
scripts/build-app.sh
dist/ContextLens.app/Contents/MacOS/ContextLens \
  --session "$PWD/docs/examples/source-session" \
  --smoke-snapshot "$PWD/docs/examples/native-editor.png" \
  --native-capture-test
```

If WindowServer access is blocked by an execution sandbox, run the command from your normal local terminal. The restricted CLI's permission preflight may differ from the launched app's TCC access. Denied access is recorded as blocked rather than reported as capture success. Without SCK permission, the fallback NSView rendering can omit compositor-backed sidebar effects; the checked-in final screenshot uses actual selected-window capture.

The native self-test checks identity after movement, dimensions after resizing, and attempted rejection of a closed probe window without fallback. The known retained result is movement/resize passing and `closure_detected_without_fallback: false`; its cause and real capture-loop closure behavior still need the isolated live check. The actor integration tests separately feed real CGImages through sample→settle→commit→resize→stop-flush and validate files and original dimensions. Pure tests exercise bounds, deduplication, paths, stable issue IDs and privacy overlays.

Remaining interactive release checklist:

- Fresh-user Screen Recording denied/granted/relaunch flows and Accessibility denied/granted with a real target application's clicked role.
- Picker/preview/start/stop on Safari, Chrome and a native app; window moved between Retina/non-Retina displays, minimized, moved to another Space, closed and reopened. Verify no substitute display/window capture.
- Rapid checkbox/dropdown/error/toast changes, very small low-contrast controls, loaders and highly animated content at all sensitivity settings. Manual hotkey conflicts should recover through the in-app Snapshot button.
- Draw/label/edit/delete each tool; resize the editor; check rectangles and freehand highlighter strokes; confirm older arrows/markers/redactions still reopen. Undo/redo labels, geometry, frame operations and persistence after quit/reopen.
- Export destination with spaces, external/project folders, low disk space, permission denial and a preexisting export; inspect burned redactions in every full frame/crop/overlay and labels/titles for sensitive text.
- Stop during a delay/in-flight sample, quit while recording, import errors, session deletion and retention cleanup in a disposable storage folder.
- Measure CPU, peak resident memory and prolonged capture responsiveness on real workflows. The comparator microbenchmark alone does not establish whole-app resource use.

No automated claim of every UI gesture being exercised is made. The app's end-to-end controller needs broader real-application soak testing before a public binary release. Developer ID signing, notarization and distribution packaging remain separate from this local MVP.

## Annotation/export update (0.2.0)

`--export-preview` opens the filtered export view during a smoke snapshot. `--exercise-highlighter`, when paired with `--smoke-snapshot` and the generated `demo-session` fixture, posts local mouse events into the app's own window to exercise a real highlighter drag. It never runs in ordinary sessions. Local view-cache snapshots are in `.build/editor-v2.png` and `.build/export-v2.png`; they can omit the compositor-backed sidebar. Current results are recorded in `examples/annotation-update-verification.json`. The new ad-hoc signed build did not have Screen Recording access during that check; no permission was requested automatically. The default export switches are both enabled; all annotated copies must remain even when image pixels match.

For smoke runs, copy generated fixtures to an OS temporary directory. A raw command-line read from the protected project Documents directory stalled during testing; the temporary fixture completed successfully. Ordinary session selection uses NSOpenPanel.
