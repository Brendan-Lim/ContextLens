# ContextLens — Give your AI agent eyes.

**Stop explaining your UI. Just show it.**

Capture one application window, preserve meaningful UI changes, review states, mark frontend problems, and export structured visual context for Codex, Claude Code or another coding agent.

Native macOS. Local-first. Open source under the [MIT licence](LICENSE). No required cloud account, production dependencies or automatic agent execution. Screenshots stay local until you choose to share them.

## Installation channels

- **Verified source builds:** build and automated checks have been exercised. Inspect and compile the source locally using the instructions below.
- **Unnotarized previews:** a separate, free channel using ad-hoc signing. These prereleases have no Developer ID signature or Apple notarization. Apple has not verified them, and macOS may block launch. See [preview downloads, installation status and first-launch instructions](docs/preview-releases.md).
- **Future signed/notarized stable releases:** the secure release workflow and official `contextlens` cask template remain pending Apple credentials. A preview is never published as a trusted stable release.

Only authorize a preview after verifying its origin and release checksum. A checksum confirms the downloaded bytes; it does not establish Apple trust. After a blocked launch, use System Settings → Privacy & Security → **Open Anyway**, then confirm **Open**, if you choose to authorize it. Follow [Apple's instructions](https://support.apple.com/en-us/102445) and keep macOS security enabled. [Distribution verification report](docs/distribution-release-report.md).

## Install from source

Current packaging supports **Apple Silicon (arm64)** and targets **macOS 14+**. Runtime checks have used macOS 26.6.2 locally and macOS 15 in hosted CI; macOS 14 runtime and Intel compatibility remain unverified. A source build requires Xcode with Swift 5.10 or later; release users will not need a compiler.

```sh
git clone https://github.com/Brendan-Lim/ContextLens.git
cd ContextLens
scripts/build-app.sh
open dist/ContextLens.app
dist/contextlens-cli --help
```

See [building](docs/building.md) for verification and development signing. The app has a stable bundle identifier, `dev.contextlens.app`. Grant Screen Recording to the copy you run in System Settings → Privacy & Security → Screen & System Audio Recording (Screen Recording on older macOS); relaunch when requested. Optional Accessibility permission adds clicked-control role/label captions. It never reads typed characters, password values or audio; screenshots can still contain private text. See [permission help](docs/permissions.md) and [troubleshooting](docs/troubleshooting.md).

## Use

1. Press **New capture** (⌘N). A floating panel lists your windows; the one you pick is outlined on your desktop. Select **Low** or **High** sensitivity and press **Start Capture**. Only that window is sampled; closure stops capture without selecting another window.
2. Interact with your application. The panel shrinks to a recording pill at the top of the screen with a timer, the latest states, **Snapshot** (⌘⇧S) and **Stop** (⌘.). ContextLens settles visual transitions and preserves meaningful states. The panel never takes focus from the app you are capturing.
3. When you stop, the main window opens on **Review**. There, untick the states you don't need (**Mark Up** only shows ticked states), rename, reorder or delete them (with undo). Click a screenshot to see it full size (Esc closes it; ← → step through states).
4. In **Mark Up**, use **Box** or **Highlight**, then write what should change. Zoom at the pointer with pinch, ⌘-scroll or ⌘+ / ⌘− (⌘0 fits), and scroll to move around. Marks are numbered; mark 1 is CL-001 in the hand off. Marks stay separate from the original images.
5. In **Hand Off**, choose whether to keep unmarked or repeated states, add an optional task, choose **Save Hand Off** and pick a folder (ideally in your project), then choose **Copy prompt**. The same prompt works for Claude Code, Codex and other coding agents.
6. Paste the instruction into your agent in your project. No agent command or upload runs automatically. See [agent integrations](Integrations/claude-code.md).

Sessions save automatically under `~/Library/Application Support/ContextLens/Sessions/` by default. Change the folder or retention period from the mascot menu → **Storage & Privacy**. The mascot menu → **Open Session** reopens a folder containing `session.json`. Retention cleanup is explicit. Deleting local sessions does not delete exported copies. See [privacy](docs/privacy.md).

## Command-line companion

The companion is named `contextlens-cli` to avoid colliding with `ContextLens` on case-insensitive filesystems.

```sh
dist/contextlens-cli demo /tmp/my-lens-session
dist/contextlens-cli validate /tmp/my-lens-session
dist/contextlens-cli export /tmp/my-lens-session /tmp/my-lens-export
# Optional: --all-frames --keep-duplicates to include every selected frame.
python3 scripts/validate_package.py /tmp/my-lens-export
dist/contextlens-cli replay EVENTS.json /tmp/replayed-session
```

PNG is used throughout for lossless native encoding. Image byte size is not a measure of model tokens. A [generated example package](docs/examples/agent-session/context.md) and [owned browser fixture exports](Benchmarks/reports/browser-evidence/) are included.

## Verify and contribute

```sh
scripts/build-app.sh
scripts/verify.sh
python3 -m unittest discover -s scripts/tests -v
python3 distribution/homebrew/scripts/validate.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [architecture](docs/architecture.md), [export format](docs/export-format.md), [native testing](docs/native-testing.md), [security/privacy](SECURITY.md), [releasing](docs/releasing.md) and [Homebrew setup](docs/homebrew.md). Branding and the app icon are owned source assets in [Brand/](Brand/).

[Research guidance](docs/research.md) and the [benchmark harness](Benchmarks/README.md) describe reproducible fixture tests and optional studies. Historical experiments have not shown a consistent agent token-efficiency advantage. Human preparation savings and general workflow speedups remain unproven. File sizes are not model tokens. Private historical traces/account observations are excluded from the public repository; reusable source and owned deterministic fixtures remain available.
