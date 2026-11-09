# Native capture lifecycle and closure diagnostics

The production loop binds one window identity and never falls back to another window or display. For the tested candidate baseline and five pending human security cases, see [release preparation](official-release-preparation.md). Native helpers require a genuine disposable interactive environment; their isolation flag is only an acknowledgment.

## Closure failure: cause remains unestablished

The historical native report has movement/resize passing and `closure_detected_without_fallback: false`. Inspection establishes only that its single post-close enumeration still matched the original window ID/PID. It does **not** establish whether this is stale enumeration, lifetime/style/key-window behavior or a production capture defect. The legacy diagnostic is distinct from the production capture-loop checks: the official baseline passed real selected-window closure without substitution and target-application exit. That result does not repair or reinterpret this diagnostic.

The old probe used a retained `.titled` NSWindow, `isReleasedWhenClosed = false`, `makeKeyAndOrderFront`, a 200 ms setup wait, `close()`, another 200 ms wait, then one enumeration. It did not record visibility, a close notification, positive pre-close membership or query latency. Apple's [`close()` documentation](https://developer.apple.com/documentation/appkit/nswindow/close()) describes removing the window from the screen and posting the close notification; it does not promise when ScreenCaptureKit will stop enumerating it. [`isReleasedWhenClosed`](https://developer.apple.com/documentation/appkit/nswindow/isreleasedwhenclosed) explicitly warns Swift/ARC callers against enabling release-on-close. The new probe deliberately retains that lifetime rather than changing it to force a pass.

The instrumented probe records original ID/PID, style, ordering, visibility/key state, pre-close exact membership, close request/return and notification, then request start/completion/duration, ID membership, owner availability, exact identity match and on-screen state. It emits no unrelated window titles or identities. Invalid setup, API errors, cancellation and timeout are failures, never inferred absence. Default ordering is `orderFront`; opt-in key ordering and closable style permit separate comparisons on an isolated Mac.

The **first lookup after the original 200 ms post-close wait** remains the legacy result. Its completion latency is measured, not assumed to be 200 ms. If that lookup matches, later absence never changes the legacy failure or overall failed status. Later polling uses 50 ms spacing and a 2 s observation budget; an in-flight noncooperative OS call may exceed that budget. The launcher separately times out the process at 40 s. Neither first-observed absence nor eventual disappearance establishes immediate detection. Rounding of sub-nanosecond remaining time is handled without zero-duration repeat polling.

## Stop, persistence and recovery

The injected `CaptureRun` coordinator checks cancellation before/after enumeration and capture, removes event monitors/hotkeys once as soon as stop is requested, and shares one finalization among duplicate stop/run callers. Finalization runs outside the cancelled sampling task, attempts metadata saving even after flush failure, and retains both failures. Deterministic regressions exercise suspended enumeration/capture, delayed starts and independent flush/save failures.

`AppModel` preserves the previous session until a new session folder can be written. Recovery blocks starting/opening another session until **Save Session** succeeds. Save retries a failed pending-frame flush and metadata write without repeating an already committed frame. Quit waits for stop/recovery and declines termination after an unresolved save/flush failure. Already saved files and in-memory frames remain available; force-quitting or disk failure can still lose unsaved memory. Repeat app-menu, quit and failed-save/retry UI checks against each replacement candidate.

Status messages distinguish unavailable target, exited application, explicit permission denial, other capture errors, empty session and save/flush recovery. Only ScreenCaptureKit's explicit `userDeclined` error maps to permission denied; other errors do not guess that consent was revoked. No automatic settings or TCC changes were added.

## Production lifecycle and privacy boundary

| Stage | Implementation and outcome |
|---|---|
| Select/bind | Picker supplies a `WindowChoice`; start binds window ID **and** owning PID once. Missing owner identity prevents start. |
| Start | Persist previous session, create/save next session, create worker/coordinator, honor cancellable delay, then install monitors/hotkey. |
| Re-enumerate | Every iteration enumerates on-screen windows and requires the exact bound pair; list order, same-app windows and other processes cannot retarget it. |
| Capture/move/resize | Capture only that SCWindow through `SCContentFilter(desktopIndependentWindow:)`; refresh bounds and derive pixel dimensions/scale from its filter. |
| Missing target | No screenshot starts. Distinguish known process exit from unavailable window, remove resources and finalize. An unavailable/minimized window is not necessarily closed. |
| Cancellation | Check before another screenshot and before consuming a late screenshot; a sample already accepted by the processor may finish. No replacement capture starts. |
| Flush/persist | Flush the last accepted original-target image, append with stable frame ID and save. Save still runs after flush failure; errors remain recoverable. |
| Review | Clear target/timer, show Review with preserved states and accurate completion/recovery status. |

There is no display filter or alternate-window capture path. The production selector and test coordinator share `WindowIdentity.selected`. Tests reject different IDs in the same process, the same ID under another PID, empty results and list reordering. If the OS temporarily lists the original closed window, the current loop can still request **that original identity** or receive an error; it cannot infer closure before the OS reports it. An original-window image already in flight may be accepted before confirmed loss. This is distinct from capturing another target, and no bounded native closure latency is claimed. An OS operation that never returns can delay finalization; resource removal on explicit stop does not wait for it.


## Reproduce and interpret

Run `scripts/verify.sh` for deterministic lifecycle, identity, processor/persistence, cancellation, failure/retry and closure-polling tests. Use [isolated acceptance](beta-acceptance.md#candidate-closure-diagnostics-isolated-environment-only) for the optional non-key/key/style probe comparison and [native testing](native-testing.md) for the end-to-end matrix. Record exact source, executable hash, OS, timing and raw outcomes privately. A legacy probe failure is not erased by a later successful production test; neither proves immediate OS enumeration.

[Coverage](testing-coverage.md) distinguishes deterministic tests from native event, permission and dialog boundaries. No bounded WindowServer closure latency, mixed-display coverage or sustained real-workload performance is claimed.
