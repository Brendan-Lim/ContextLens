# Troubleshooting

## Binary downloads and Homebrew

The current download is the preview [`v0.3.0-preview.1`](https://github.com/Brendan-Lim/ContextLens/releases/tag/v0.3.0-preview.1) (ZIP), also installable with `brew install --cask Brendan-Lim/tap/contextlens-preview`. Both are ad-hoc signed and not notarized by Apple. The stable DMG and the `contextlens` cask appear only after v0.3.1 passes [interactive acceptance](release-acceptance/README.md) and is published; until then, any stable cask template is not an installable package. [Homebrew channels](homebrew.md).

ContextLens is built for macOS 14 Sonoma and later on Apple Silicon. Automated checks run on macOS 15 and macOS 26; macOS 14 itself has not been tested at runtime yet, so please [report](https://github.com/Brendan-Lim/ContextLens/issues) anything that breaks there.

If a future install conflicts with an existing `ContextLens.app` or CLI, preserve your current app first and inspect `brew list --cask contextlens` and `command -v contextlens-cli`. Do not use `--force` to overwrite a development copy. Normal uninstall must not delete local sessions or exports.

macOS blocks the first launch of these unnotarized builds. If you trust the download (it came from this repository's Releases page and its SHA-256 matches), use **System Settings → Privacy & Security → Open Anyway**, as Apple describes in [Safely open apps on your Mac](https://support.apple.com/en-us/102445). If macOS still refuses, stop and report the version, download URL and the exact message. Do not disable Gatekeeper or strip quarantine attributes. For a future Developer ID release, maintainers must also verify `codesign --verify --deep --strict`, `xcrun stapler validate` and `spctl --assess --type execute`.

## Permissions and capture

### First-time Screen Recording setup

First-time users normally follow the standard macOS permission grant flow:

1. Open your installed copy of ContextLens, normally `/Applications/ContextLens.app`.
2. In ContextLens's Capture panel, choose **Check Access** and respond to the macOS permission prompt.
3. Open **System Settings → Privacy & Security → Screen & System Audio Recording** (called **Screen Recording** on older macOS). Enable ContextLens in the **upper Screen & System Audio Recording list**. If it is missing, use **+ beneath that list** to add your installed app.
4. Follow any macOS **Quit & Reopen** request. Reopen the same installed copy and choose **Check Access** again, then select a window to capture.

On macOS 26, the separate lower **System Audio Recording Only** list grants audio-only access. Enabling ContextLens there does not authorize window capture. Use the upper list for Screen Recording, even though ContextLens itself does not record audio. Optional Accessibility permission enables clicked-control labels; capture works without those labels, and ContextLens does not read typed text or password values.

Normally, first-time setup ends after the standard grant and relaunch. Use the recovery procedure below only if access remains denied despite an enabled entry.

### Screen Recording enabled but capture still fails

This procedure successfully restored access in an observed macOS 26 case where ScreenCaptureKit returned permission denial **`-3801`** even though ContextLens was enabled in Settings.

An ad-hoc-signed app update can change the identity that macOS previously approved, leaving an enabled entry that no longer authorizes the updated app. **This can happen even with only one ContextLens installation.** Multiple copies can make identifying the approved app harder, but are not required for this failure. The [technical permission and signing explanation](permissions.md#signing-and-upgrades) describes why.

Reconnect the installed app manually:

1. **Save your work and quit ContextLens fully** with **ContextLens → Quit ContextLens** or <kbd>⌘</kbd><kbd>Q</kbd>. Closing its window alone does not quit the app. If other ContextLens copies are open, quit those too.
2. Open **System Settings → Privacy & Security → Screen & System Audio Recording**.
3. In the **upper Screen & System Audio Recording list**, select **ContextLens** and click **−** to remove its entry. If ContextLens is absent from that list, continue to step 4. Remove **only ContextLens**; leave other apps and the separate **System Audio Recording Only** list unchanged.
4. Click **+ beneath the upper list**. In the file chooser, press <kbd>⌘</kbd><kbd>⇧</kbd><kbd>G</kbd>, enter `/Applications`, and press Return. Select **ContextLens.app** and click **Open** to add `/Applications/ContextLens.app` again.
5. Confirm ContextLens is back in the **upper list** and turn its switch **on**.
6. Follow any macOS **Quit & Reopen** request. Otherwise, reopen `/Applications/ContextLens.app` from Finder. Use that same installed copy throughout the procedure.
7. Open ContextLens's Capture panel and choose **Check Access**. Access should be verified through ScreenCaptureKit. If the window list is empty after verification, open an application window and refresh.
8. Select a test window and start a short capture. Make a visible change, then stop and confirm a state appears in **Review**.

The expected result is verified access and a working window capture; the Settings switch alone is not proof. Other API errors can have different causes.

If access still fails, confirm the running app's path. Recent builds show **Running copy**, **Copy and signing details**, and **Show This Copy in Finder** beside the error. Note the app version/build, macOS version and exact error for a [bug report](https://github.com/Brendan-Lim/ContextLens/issues), keeping private logs and screen content local. See [permission diagnostics](permissions.md#interpret-the-apps-result) for the meanings of unverified, denied and failed checks. This procedure changes only ContextLens's permission entry; keep macOS security protections enabled.

### Other capture issues

If the selected window closes or becomes unavailable, start a new capture and explicitly choose a target. The recorder must not substitute a different window or the whole display.

If a change you made wasn't captured as its own state, it was probably too small to count. ContextLens keeps a new state when the window changes enough to matter, so a one-pixel shift or a faint colour change can fall below that threshold, especially at **Low** sensitivity. Switch to **High**, or press <kbd>⌘</kbd><kbd>⇧</kbd><kbd>S</kbd> during capture to take a snapshot at exactly the moment you want.

## Building and validation

Use a compatible Xcode and inspect `xcode-select -p`, `xcodebuild -version` and `swift --version`. The automated gate expects a built `dist/contextlens-cli`; run `scripts/build-app.sh` before `scripts/verify.sh` on a fresh checkout. Install `jsonschema==4.23.0` for the independent schema cross-check.

A development build may use an Apple Development certificate or ad-hoc signing. `--distribution` deliberately fails without a Developer ID Application identity. See [releasing](releasing.md) for the exact seven required CI secrets. Missing credentials are not repaired by fake secrets or a weaker signature.

Native smoke checks require WindowServer access and may abort inside a restricted shell sandbox. Use the documented flags only in a genuine disposable interactive test environment; never simulate permission success. The known native closure-detection failure and compositor snapshot gaps are recorded in [native testing](native-testing.md).
