# Isolated preview acceptance procedure

**Status: manual checks pending.** Use a disposable interactive macOS VM or separate Apple Silicon test Mac. Do not execute this checklist on the owner's working ContextLens installation. A new user alone does not isolate `/Applications`, Homebrew's Caskroom/CLI links or shared installations; use it only on a dedicated test machine or with a separately verified isolated installation. A custom `--appdir` alone is insufficient.

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
| Uninstall/data retention | Leave a synthetic session and export, uninstall the cask; app/link disappear and session/export survive; reinstall/reopen deliberately | pending |

No access to a second display/macOS 14 is a pending result, not a pass. The native closure self-test previously reported `closure_detected_without_fallback: false`; its cause and real capture-loop closure behavior remain unverified. The loop re-enumerates and requires the original window ID **and** process ID, with `SCContentFilter(desktopIndependentWindow:)`; source inspection and absent-target tests are not substitutes for this live test.

The existing `--native-capture-test` helper creates a key probe window as part of its closure check. Run that helper only on this disposable desktop; its ordinary smoke/background flags do not make that probe safe for the owner's active desktop. Do not run a second preview copy with the shared bundle identity merely to simulate a fresh user.

## Validate the saved artifacts

On the disposable machine, substitute the actual synthetic session/export paths:

```sh
contextlens-cli validate /path/to/saved-session
contextlens-cli export /path/to/saved-session /path/to/new-cli-export --all-frames --keep-duplicates
```

`validate` inspects **sessions**, not Hand Off package roots. With an optional source checkout and Python available, run `python3 scripts/validate_package.py /path/to/hand-off` against both the UI and CLI exports. Check manifest paths/dimensions and open the crop for the marked issue. This developer validator is separate from the compiler-free app installation. Native CLI package inspection is not an implemented command; do not report it as tested.

For every failure, preserve the original synthetic session and exact steps, record source/tag and safe error text, and add a regression before fixing the cause where automatic coverage is possible. Do not publish a more favorable readiness status until the required interactive cases have actual results.
