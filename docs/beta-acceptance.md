# Isolated preview acceptance procedure

**Status: manual checks pending.** Use a disposable interactive macOS VM or separate Apple Silicon test Mac. Do not execute this checklist on the owner's working ContextLens installation. A new user alone does not isolate `/Applications`, Homebrew's Caskroom/CLI links or shared installations; use it only on a dedicated test machine or with a separately verified isolated installation. A custom `--appdir` alone is insufficient.

The published Homebrew `0.3.0-preview.1` and the **0.3.1/build 6 source candidate** are different binaries. Record the version/build, source commit and executable hash for each test. Do not claim the 0.3.1 lifecycle fixes were tested by running the older installed preview. For genuinely fresh consent, restore a clean VM snapshot or use another clean test environment for each binary; carrying consent across an update is an upgrade test. No owner's TCC reset is allowed.

Record the test date, macOS version, architecture, Homebrew version, preview tag and checksum. Record each case as **pass**, **fail** or **pending**, with the exact action and safe evidence location. Keep raw logs, screenshots and session data local, outside tracked documentation. Use synthetic content only; review any proposed public image before adding its approval hash. No model calls are needed.

## Installation and trust

1. Confirm the disposable machine has no ContextLens app/cask or `contextlens-cli` link and no sessions that matter. Review the official [preview release](https://github.com/Brendan-Lim/ContextLens/releases/tag/v0.3.0-preview.1) and [preview limitations](preview-releases.md). The ZIP SHA-256 must be `1cd84d6b15fc7aed7346ff1fd27382d5d2cd5a51637c7358861ddf55ebe0da45`.
2. Run `brew install --cask Brendan-Lim/tap/contextlens-preview`. Check `/Applications/ContextLens.app`, `command -v contextlens-cli`, and `xattr -p com.apple.quarantine /Applications/ContextLens.app`. This last command reads quarantine; it must not remove it. Verify the embedded `Contents/Resources/preview.json` records source `4b463d3e6dfc3ec4035f89d0e9f8787dee08ff4c` and unnotarized ad-hoc trust.
3. Open the app from Finder. Record the actual warning and available choices. No warning is not proof of Apple trust; note the machine's policy and prior authorization. A read-only assessment is `spctl --assess --type execute -vv /Applications/ContextLens.app`; the hosted runner returned rejection.
4. Only after the tester chooses to trust the verified origin, follow [Apple's Open Anyway procedure](https://support.apple.com/en-us/102445): try opening, dismiss the alert, open System Settings → Privacy & Security → Open Anyway, then confirm Open. Record the real result. Do not disable Gatekeeper, strip quarantine, use force/adopt flags, change managed policy or automate the approval.
5. Run `contextlens-cli --help`. Record whether CLI authorization differs from app authorization. Stop if macOS reports malware, corruption or revocation; investigate instead of attempting another bypass.

## Permission, capture and recovery matrix

Prepare two **TextEdit** windows on the disposable desktop. Window A contains only `ContextLens synthetic window A`, `State 1` and `Align this control`; window B contains `ContextLens synthetic window B — never capture this`. Keep all personal applications closed. Test with Low and High sensitivity. Accessibility remains optional.

| Case | Action and required observation | Current result |
|---|---|---|
| Initial permission denied | Launch without Screen Recording consent; picker explains access is unverified/denied and offers a settings/check-access action; no successful capture claimed | pending |
| Grant and relaunch | Use the app's settings action, grant consent to this copy, relaunch when requested, choose Check Access; Window A becomes selectable | pending |
| Basic capture | Select A, start, edit only synthetic text through States 1–3, stop; Review contains the selected window only | pending |
| Review/annotation | Select/deselect states, rename one, draw a Box and Highlight, add a note, undo/redo, check stable issue IDs and canvas zoom | pending |
| Hand Off | Save to a new temporary folder; inspect `context.md`, `manifest.json`, full frames and crop/annotation paths; no upload or agent execution occurs | pending |
| Session recovery | Quit/relaunch, reopen the saved folder containing `session.json`; states, notes, IDs and selection survive | pending |
| Selected-window closure | Start A with B visible; close A; capture stops, existing frames remain, and B/the desktop never substitutes | pending |
| Application exit | Repeat and quit TextEdit; target loss stops capture without another target | pending |
| Move/resize | Move and resize A, including same-aspect resize; dimensions/crops stay aligned to each frame's original size | pending |
| Display/Retina | Move A between 1× and 2× displays if available; record actual scale/dimensions and annotation alignment | pending |
| Repeated/rapid stop | Repeat five sessions and immediate start/stop, including a delayed start; no stale task, extra target or overwritten previous session | pending |
| Empty/invalid capture | Stop before a state settles, and open an invalid session; clear guidance, no crash or corrupt export presented as success | pending |
| Revocation/recovery | Revoke Screen Recording **only in this disposable environment**, test capture failure/stoppage, restore through Settings and relaunch; no TCC reset or silent privacy-setting write | pending |
| Failed save and retry | On a throwaway session/disk only, make its destination unavailable; stop/quit must not claim all data saved or silently exit after pending-save failure. Restore access/space, choose **Save Session**, then validate/reopen the recovered session before quitting | pending |
| Uninstall/data retention | Leave a synthetic session and export, uninstall the cask; app/link disappear and session/export survive; reinstall/reopen deliberately | pending |

No access to a second display/macOS 14 is a pending result, not a pass. The native closure self-test previously reported `closure_detected_without_fallback: false`; its cause and real capture-loop closure behavior remain unverified. The loop re-enumerates and requires the original window ID **and** process ID, with `SCContentFilter(desktopIndependentWindow:)`; source inspection and absent-target tests are not substitutes for this live test.

The 0.3.1 native helper and Python launchers require explicit isolation acknowledgment. Their flag does not create isolation. The closure probe defaults to non-key ordering, while other smoke/input helpers can still make windows key; the old key-probe behavior is an explicit comparison option. Do not run a second preview copy with the shared bundle identity merely to simulate a fresh user.

## Candidate closure diagnostics (isolated environment only)

Build this exact source into a disposable destination, using ad-hoc signing without replacing an installed app:

```sh
CONTEXTLENS_SIGN_IDENTITY=- scripts/build-app.sh --output /tmp/contextlens-031-candidate
python3 scripts/verify-native.py --isolated-environment \
  --app /tmp/contextlens-031-candidate/ContextLens.app --closure-only \
  --output /tmp/contextlens-031-original-nonkey
python3 scripts/verify-native.py --isolated-environment \
  --app /tmp/contextlens-031-candidate/ContextLens.app --closure-only --key-probe \
  --output /tmp/contextlens-031-original-key
python3 scripts/verify-native.py --isolated-environment \
  --app /tmp/contextlens-031-candidate/ContextLens.app --closure-only --probe-style closable \
  --output /tmp/contextlens-031-closable-nonkey
```

These are **pending commands**, not successful native results. Preserve each output separately. Read `results.json` and `dark-review/native-capture-verification.json`: confirm pre-close membership, original window ID/PID, visibility and close notification, then compare request/completion times, ID membership, identity matches and eventual outcome. A stale original-window entry is not evidence of another target being captured. The first lookup after the original 200 ms wait remains separate; query completion may be later, so this is not a detection-by-200-ms guarantee. Later absence does not make that first lookup pass. Polling has a 2 s observation budget and 50 ms spacing; a slow in-flight OS query can exceed the budget, and the launcher separately fails the process at 40 s.

Use a new output directory for a full dark/light Review/Mark Up/Hand Off/zoom run by omitting `--closure-only`. The launcher rejects the wrong bundle version/build and preserves existing partial evidence. It cannot certify fresh human consent, actual capture-loop stopping, or session recovery merely because a diagnostic lookup observed absence. Complete the TextEdit workflow and closure/application-exit matrix above for those behaviors.

## Validate the saved artifacts

On the disposable machine, substitute the actual synthetic session/export paths:

```sh
contextlens-cli validate /path/to/saved-session
contextlens-cli export /path/to/saved-session /path/to/new-cli-export --all-frames --keep-duplicates
```

`validate` inspects **sessions**, not Hand Off package roots. With an optional source checkout and Python available, run `python3 scripts/validate_package.py /path/to/hand-off` against both the UI and CLI exports. Check manifest paths/dimensions and open the crop for the marked issue. This developer validator is separate from the compiler-free app installation. Native CLI package inspection is not an implemented command; do not report it as tested.

For every failure, preserve the original synthetic session and exact steps, record source/tag and safe error text, and add a regression before fixing the cause where automatic coverage is possible. Do not publish a more favorable readiness status until the required interactive cases have actual results.
