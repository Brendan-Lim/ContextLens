# Native capture reliability — 0.3.1 candidate

**READY FOR CONTROLLED TESTERS.** Automated lifecycle checks pass; first-launch authorization, fresh Screen Recording consent, production target-loss behavior and Hand Off still require an isolated interactive Mac. No native fixture or capture was run against the owner's desktop, installation, permissions or sessions. This report concerns **0.3.1/build 6 source**, not the published `v0.3.0-preview.1` binary.

## Closure failure: cause remains unestablished

The historical native report has movement/resize passing and `closure_detected_without_fallback: false`. Inspection establishes only that its single post-close enumeration still matched the original window ID/PID. It does **not** establish whether this is stale enumeration, lifetime/style/key-window behavior or a production capture defect. No new WindowServer evidence was collected, so the failure cannot yet be classified as test-only or production-affecting.

The old probe used a retained `.titled` NSWindow, `isReleasedWhenClosed = false`, `makeKeyAndOrderFront`, a 200 ms setup wait, `close()`, another 200 ms wait, then one enumeration. It did not record visibility, a close notification, positive pre-close membership or query latency. Apple's [`close()` documentation](https://developer.apple.com/documentation/appkit/nswindow/close()) describes removing the window from the screen and posting the close notification; it does not promise when ScreenCaptureKit will stop enumerating it. [`isReleasedWhenClosed`](https://developer.apple.com/documentation/appkit/nswindow/isreleasedwhenclosed) explicitly warns Swift/ARC callers against enabling release-on-close. The new probe deliberately retains that lifetime rather than changing it to force a pass.

The instrumented probe records original ID/PID, style, ordering, visibility/key state, pre-close exact membership, close request/return and notification, then request start/completion/duration, ID membership, owner availability, exact identity match and on-screen state. It emits no unrelated window titles or identities. Invalid setup, API errors, cancellation and timeout are failures, never inferred absence. Default ordering is `orderFront`; opt-in key ordering and closable style permit separate comparisons on an isolated Mac.

The **first lookup after the original 200 ms post-close wait** remains the legacy result. Its completion latency is measured, not assumed to be 200 ms. If that lookup matches, later absence never changes the legacy failure or overall failed status. Later polling uses 50 ms spacing and a 2 s observation budget; an in-flight noncooperative OS call may exceed that budget. The launcher separately times out the process at 40 s. Neither first-observed absence nor eventual disappearance establishes immediate detection. Rounding of sub-nanosecond remaining time is handled without zero-duration repeat polling.

## Reproduced production defects and changes

These defects are independent of the unexplained native closure result. Initial failing deterministic tests against an extraction of the old loop behavior reproduced:

- Stop while enumeration is suspended could resume into a new screenshot before the old post-capture cancellation check. Resource removal also waited for the OS operation to return.
- A pending-image flush error skipped the following metadata save because both shared one `do` block.
- Final status unconditionally said states were saved even when persistence failed. Quit could subsequently complete without a successful pending-frame recovery.

The production app now uses the injected `CaptureRun` coordinator. It checks cancellation before/after enumeration and capture, removes event monitors/hotkeys once as soon as stop is requested, and shares one finalization among duplicate stop/run callers. Finalization runs outside the cancelled sampling task, attempts metadata saving even after flush failure, and retains both failures. Tests also caught and corrected an early-stop delay and the diagnostic clock-rounding issue during this change.

`AppModel` preserves the previous session until a new session folder can be written. Recovery blocks starting/opening another session until **Save Session** succeeds. Save retries a failed pending-frame flush and metadata write without repeating an already committed frame. Quit waits for stop/recovery and declines termination after an unresolved save/flush failure. Already saved files and in-memory frames remain available; force-quitting or disk failure can still lose unsaved memory. Actual app-menu, quit and disk-failure UI interactions remain pending.

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

## Regression coverage and verification

Baseline: 80 Swift tests, 49 benchmark Python tests, 13 independent schema checks and 10 deterministic replays passed before changes. The final candidate passed `scripts/ci.sh` in a separate checkout on Apple Silicon, macOS 26.6.2, Xcode 26.6 / Swift 6.3.3. The checkout held the exact staged source changes; its development archive correctly recorded a dirty source state and is not a published preview. Hosted verification links are recorded after committing.

New deterministic coverage consists of 14 lifecycle tests, seven diagnostic polling tests, five capture/processor integration tests and six Python launcher tests:

- Identity exclusion; target loss; stop during enumeration, delay, capture and accepted pending processing; stop before run; duplicate stops; caller cancellation; five rapid independent runs; application exit; errors/permission denial; empty/frame-limit outcomes; independent flush/save failures.
- Real synthetic CGImages through `CaptureProcessor` and `SessionStore`: changed dimensions, pending-frame flush after loss/cancellation, valid reopened sessions, preserved original-only metadata, explicit permission classification and retry after a failed PNG write without duplicate IDs.
- Injected closure enumerator/clock: first absence, stale-then-absent without erasing failure, persistent membership, slow query, error, PID mismatch, invalid clock/policy. These do not manufacture live SCWindow objects.
- Launcher refusal before any app/CLI execution without isolation, opt-in key probe, wrong bundle version rejection, preserved partial evidence and honest timeout handling.

| Check | Result |
|---|---|
| Swift tests | 106 passed |
| Python release/publication/native-launcher regressions | 42 passed |
| Benchmark Python / Node / browser fixtures | 49 benchmark + 12 experiment Python tests; 14 Node unit/export + 2 mapper + 3 browser tests passed; 10 defects reproduced and 10 good browser controls passed |
| Packages, independent schemas and deterministic replays | 13 packages including independent Draft 2020-12 validation; 10 replay fixtures passed |
| Optimized arm64 build, ad-hoc signature, portability and archive checks | Passed in separate checkout; real-bundle portability rejection, CLI help aliases, development archive round-trip and stable cask template syntax passed |
| Publication guards and documentation links | Tracked/staged guards: zero findings; 84 Markdown files / 109 local links passed; no new media approvals |
| Native closure/style/key comparison; real capture lifecycle | **Pending — no isolated interactive Mac** |
| Gatekeeper Open Anyway, fresh consent, installed capture/Hand Off | **Pending — requires tester action** |
| macOS 14 runtime, mixed displays and long capture performance | **Pending — no new measurements claimed** |

Repeatable commands used (all native app building/packaging in the temporary checkout):

```sh
PYTHONPATH=/path/to/jsonschema/site-packages scripts/ci.sh
node --test Experiments/visual-to-code/tests/unit.test.mjs Experiments/visual-to-code/tests/export.test.mjs
CHROMIUM_EXECUTABLE=/path/to/Chrome node --test Experiments/visual-to-code/tests/browser.test.mjs
CHROMIUM_EXECUTABLE=/path/to/Chrome node --test Experiments/code-aware-efficiency/tests/mapper.test.mjs
python3 -m unittest discover -s Experiments/visual-to-code/tests -p 'test_*.py' -v
python3 -m unittest discover -s Experiments/code-aware-efficiency/tests -p 'test_*.py' -v
python3 scripts/audit-public-files.py --staged
python3 scripts/check-public-links.py
```

The browser suite first encountered sandbox `listen EPERM` on its loopback server; rerunning with the required execution permission passed all three tests. It used a fresh headless profile and synthetic fixtures, not desktop capture or the owner's browser session. Build tooling emitted missing module-cache debug-path warnings; the optimized binaries compiled and passed the subsequent portability/signature checks.

No private screenshots, raw native logs, TCC/authentication records or new fixture approvals accompany this change. Existing historical evidence is preserved. See the [coverage map](testing-coverage.md) for remaining UI-only behaviors.

## First-run acceptance and release decision

Follow the [isolated acceptance procedure](beta-acceptance.md) on a disposable Apple Silicon macOS VM/test Mac. Record each binary's version, source SHA and executable hash; the existing Homebrew cask still installs the older 0.3.0 preview. Use clean snapshots separately for genuinely fresh consent and candidate tests. The checklist gives explicit installation, Apple-controlled Open Anyway, Screen Recording, synthetic TextEdit A/B capture, Review/annotation, Hand Off, reopen, closure/application exit, failed-save retry and uninstall/data-retention steps. Every interactive result remains **pending** until performed; a diagnostic absence is not end-to-end acceptance.

The production corrections warrant preparing **0.3.1-preview.1** through the existing preview process after automated gates. No old tag/assets will be replaced. A clean-source ad-hoc archive was prepared and its final extraction, signatures, provenance and checksum verified using the existing `build-app.sh --preview` / `preview-release.py package` process. It has not been launched or published. Public publication and any cask update are deferred until native capture/closure acceptance supplies the missing evidence; this report does not claim a new published binary or cask exists. The original release and cask remain available, the stable signing workflow is unchanged, and there is no Developer ID/notarization or security bypass. [Preview instructions](preview-releases.md) retain the exact verified download and installation information.

Implementation: [`55a8cac5655dc1b52d5bd38e3047f301286c7a52`](https://github.com/Brendan-Lim/ContextLens/commit/55a8cac5655dc1b52d5bd38e3047f301286c7a52), source tree `18e09cdf7bf9fadda89941cbf79b5af5197ab581`. The report update is a separate documentation commit.

Prepared local-only archive: `/tmp/contextlens-031-preview-assets/ContextLens-0.3.1-preview.1-arm64.zip` (1,517,188 bytes), with `.sha256` and `.json` sidecars. SHA-256: `3ec508d7fcaf3192753c57fffcbd3e7b72f0812b49d6fb320986d4e8daf7e963`. Receipt: source commit above, `sourceDirty: false`, `notarized: false`, `developerIDSigned: false`. This is a temporary local test artifact, not a GitHub release asset, and its checksum must not be used for a cask. A future rebuild can have different bytes.

Hosted [Publication Security passed](https://github.com/Brendan-Lim/ContextLens/actions/runs/42489613483), including normal history/Gitleaks gates. [macOS CI passed](https://github.com/Brendan-Lim/ContextLens/actions/runs/42489613461) on the exact implementation commit, including the optimized build, full regression suite, schema/replay checks, portability/archive verification and browser fixtures. The signed and preview release workflow files are byte-identical to the previous commit; no tap change or tag/asset overwrite occurred. The classification remains **READY FOR CONTROLLED TESTERS**; unit tests cannot establish limited public beta readiness.
