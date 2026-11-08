# Troubleshooting

## Binary downloads and Homebrew

A Homebrew cask and signed public download are not available yet. Use the [source build](building.md) meanwhile. A pending cask template is not an installable package. Future release installation will be documented only after testing a published notarized asset.

If a future install conflicts with an existing `ContextLens.app` or CLI, preserve your current app first and inspect `brew list --cask contextlens` and `command -v contextlens-cli`. Do not use `--force` to overwrite a development copy. Normal uninstall must not delete local sessions or exports.

If Gatekeeper rejects a future public release, stop and report the version, source download URL and assessment output. Do not disable Gatekeeper or strip quarantine attributes. Release maintainers must verify the downloaded archive's checksum, `codesign --verify --deep --strict`, `xcrun stapler validate` and `spctl --assess --type execute`.

## Permissions and capture

Grant Screen Recording in System Settings → Privacy & Security → Screen & System Audio Recording (named Screen Recording on older macOS). Approve the installed copy and relaunch when macOS asks. Optional Accessibility permission enables clicked-control labels; capture works without those labels. ContextLens does not request typed text, password values or audio.

If Settings shows access enabled but no windows appear, confirm which app path is running and use **Check Access**. A changed development signature or a transition to Developer ID distribution can require fresh consent. Follow [permissions](permissions.md) for targeted manual recovery. No permission database is reset by a build or installation.

If the selected window closes or becomes unavailable, start a new capture and explicitly choose a target. The recorder must not substitute a different window or the whole display.

## Building and validation

Use a compatible Xcode and inspect `xcode-select -p`, `xcodebuild -version` and `swift --version`. The automated gate expects a built `dist/contextlens-cli`; run `scripts/build-app.sh` before `scripts/verify.sh` on a fresh checkout. Install `jsonschema==4.23.0` for the independent schema cross-check.

A development build may use an Apple Development certificate or ad-hoc signing. `--distribution` deliberately fails without a Developer ID Application identity. See [releasing](releasing.md) for the exact seven required CI secrets. Missing credentials are not repaired by fake secrets or a weaker signature.

Native smoke checks require WindowServer access and may abort inside a restricted shell sandbox. Use the documented background-launch flags outside that sandbox; never simulate permission success. The known native closure-detection failure and compositor snapshot gaps are recorded in [native testing](native-testing.md).
