# Troubleshooting

## Binary downloads and Homebrew

The current download is the preview [`v0.3.0-preview.1`](https://github.com/Brendan-Lim/ContextLens/releases/tag/v0.3.0-preview.1) (ZIP), also installable with `brew install --cask Brendan-Lim/tap/contextlens-preview`. Both are ad-hoc signed and not notarized by Apple. The stable DMG and the `contextlens` cask appear only after v0.3.1 passes [interactive acceptance](release-acceptance/README.md) and is published; until then, any stable cask template is not an installable package. [Homebrew channels](homebrew.md).

ContextLens is built for macOS 14 Sonoma and later on Apple Silicon. Automated checks run on macOS 15 and macOS 26; macOS 14 itself has not been tested at runtime yet, so please [report](https://github.com/Brendan-Lim/ContextLens/issues) anything that breaks there.

If a future install conflicts with an existing `ContextLens.app` or CLI, preserve your current app first and inspect `brew list --cask contextlens` and `command -v contextlens-cli`. Do not use `--force` to overwrite a development copy. Normal uninstall must not delete local sessions or exports.

macOS blocks the first launch of these unnotarized builds. If you trust the download (it came from this repository's Releases page and its SHA-256 matches), use **System Settings → Privacy & Security → Open Anyway**, as Apple describes in [Safely open apps on your Mac](https://support.apple.com/en-us/102445). If macOS still refuses, stop and report the version, download URL and the exact message. Do not disable Gatekeeper or strip quarantine attributes. For a future Developer ID release, maintainers must also verify `codesign --verify --deep --strict`, `xcrun stapler validate` and `spctl --assess --type execute`.

## Permissions and capture

Grant Screen Recording in System Settings → Privacy & Security → Screen & System Audio Recording (named Screen Recording on older macOS). Approve the installed copy and relaunch when macOS asks. Optional Accessibility permission enables clicked-control labels; capture works without those labels. ContextLens does not request typed text, password values or audio.

If Settings shows access enabled but no windows appear, confirm which app path is running and use **Check Access**. A changed development signature or a transition to Developer ID distribution can require fresh consent. Follow [permissions](permissions.md) for targeted manual recovery. No permission database is reset by a build or installation.

If the selected window closes or becomes unavailable, start a new capture and explicitly choose a target. The recorder must not substitute a different window or the whole display.

If a change you made wasn't captured as its own state, it was probably too small to count. ContextLens keeps a new state when the window changes enough to matter, so a one-pixel shift or a faint colour change can fall below that threshold, especially at **Low** sensitivity. Switch to **High**, or press <kbd>⌘</kbd><kbd>⇧</kbd><kbd>S</kbd> during capture to take a snapshot at exactly the moment you want.

## Building and validation

Use a compatible Xcode and inspect `xcode-select -p`, `xcodebuild -version` and `swift --version`. The automated gate expects a built `dist/contextlens-cli`; run `scripts/build-app.sh` before `scripts/verify.sh` on a fresh checkout. Install `jsonschema==4.23.0` for the independent schema cross-check.

A development build may use an Apple Development certificate or ad-hoc signing. `--distribution` deliberately fails without a Developer ID Application identity. See [releasing](releasing.md) for the exact seven required CI secrets. Missing credentials are not repaired by fake secrets or a weaker signature.

Native smoke checks require WindowServer access and may abort inside a restricted shell sandbox. Use the documented background-launch flags outside that sandbox; never simulate permission success. The known native closure-detection failure and compositor snapshot gaps are recorded in [native testing](native-testing.md).
