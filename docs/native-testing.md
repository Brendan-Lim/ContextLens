# Native integration testing

Use a disposable interactive Apple Silicon macOS VM or dedicated test Mac. Preserve the owner's installation, sessions, focus and permissions. `--isolated-native-test` and the Python launcher's `--isolated-environment` acknowledge isolation; they do not create it. Native fixture/input helpers can make windows key.

The [official candidate baseline](official-release-preparation.md) passed 14 exact-byte native engineering cases. Five human security cases remain pending. Repeat applicable engineering checks for every replacement candidate; unit tests, a directly launched executable and pre-existing runner consent cannot prove fresh authorization. macOS 14 runtime, mixed displays and sustained real-workload measurements remain unverified.

## Automated and fixture checks

Run `scripts/ci.sh` for the complete deterministic gate; [building](building.md) lists development dependencies. It performs no desktop capture, live model calls or TCC changes. The [coverage map](testing-coverage.md) describes test boundaries.

For an isolated development fixture run, build into a new destination and choose a new output directory:

```sh
CONTEXTLENS_SIGN_IDENTITY=- scripts/build-app.sh --output /tmp/contextlens-native-build
python3 scripts/verify-native.py --isolated-environment   --app /tmp/contextlens-native-build/ContextLens.app   --output /tmp/contextlens-native-results
```

This exercises Review, Mark Up, zoom and Hand Off in Light/Dark. Open every output and record failures. `cacheDisplay` snapshots can omit Hand Off's compositor-backed sidebar; judge it from genuine ScreenCaptureKit output. The legacy closure probe's first post-wait enumeration and eventual result are separate; see [capture diagnostics](native-capture-reliability.md). A failed diagnostic is never silently counted as passing production acceptance.

## Interactive release checklist

Use [exact-candidate acceptance](release-acceptance/README.md) and [the isolated matrix](beta-acceptance.md), recording pass/fail/pending, exact source/assets, environment, observations and safe evidence locators. Use only fictional content:

- Preserve a genuine download's quarantine and observe first-launch policy and user-controlled Open Anyway. Test fresh Screen Recording denial, grant/relaunch and revocation/recovery. Accessibility is optional; verify clicked roles without editable field values.
- Capture a deliberately chosen browser/native window at Low/High sensitivity. Move/resize it, close it while another window remains, and quit the target app. Verify original-only frames, no substitution, correct original dimensions and pending-frame persistence.
- Exercise rapid start/stop, delayed/in-flight stop, ContextLens quit during capture, and failed capture-save/retry using disposable storage. Preserve recoverable data and verify the reopened session.
- Reorder, rename and deselect states; draw Box/Highlight, edit notes and geometry, zoom, undo/redo, and reopen legacy marks/redactions. Verify stable issue IDs. New redaction creation is absent from the toolbar; use a synthetic legacy session for redaction checks.
- Save Hand Off, inspect all image derivatives, notes, paths and timeline, and copy/paste the prompt deliberately. Test stale source refusal, refresh/retry, unwritable destinations, spaces/Unicode and no overwrite in throwaway folders. Validate with `python3 scripts/validate_package.py EXPORT`.
- Inspect the real DMG in Finder Light/Dark and at available display densities; drag/install/eject/launch inside the disposable machine. Follow [installer checks](../distribution/dmg/README.md#real-finder-checks).
- Record unavailable macOS 14/mixed-display, minimized/Spaces, tiny/transient UI, hotkey conflict and external-app cases as pending. Measure sustained CPU/RSS, keystroke-to-display latency and zoom/pan FPS separately from comparator/image microbenchmarks; see [benchmark instructions](../Benchmarks/README.md).

Keep raw screenshots, sessions and permission observations private. Only reviewed fictional images with explicit publication hashes belong in Git. Do not manufacture a passing human acceptance record or use a source fixture launch as verification of official candidate bytes.
