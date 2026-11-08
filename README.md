# ContextLens

**Turn UI feedback into a clear coding-agent handoff.**

A native, local-first macOS utility for recording one application's UI states, reviewing screenshots, adding editable visual feedback, and exporting focused evidence for Codex or Claude Code.

Version 0.3.0 redesigns the app around the ContextLens mascot: capture happens in a floating panel that outlines the chosen window, and the main window has three tabs, **Review**, **Mark Up** and **Hand Off**. Capture still uses [one workflow with **Low/High** sensitivity](docs/capture-controls.md), with advanced settings under **Capture options**. Sessions, import, storage and help live in the mascot menu. Brand assets and the app icon are in [Brand/](Brand/). Earlier changes: [0.2.0 update and verification](docs/update-0.2.0.md).

## Run

Requires macOS 14+, Xcode command-line tools with Swift 5.10 or later (verified with Swift 6.3.3). No production package dependencies or account.

```sh
scripts/build-app.sh
open dist/ContextLens.app
```

Local builds use an available Apple Development signing identity for stable permissions; machines without one fall back to ad-hoc signing. Set `CONTEXTLENS_SIGN_IDENTITY` to select an identity explicitly. Grant Screen Recording to ContextLens when requested; relaunch if macOS requires it. If Settings is enabled but access fails after an update, see the [permission repair and signing fix](docs/permissions.md). Accessibility is optional and adds the clicked control's role and visible label (used to name states, for example "Clicked “Save”"). It never reads text-field or password values, typed characters or audio. Visible text can still appear in screenshots.

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

PNG is used throughout for lossless native encoding. Image byte size is not a measure of model tokens. A [generated example package](docs/examples/agent-session/context.md) and real browser fixture exports (local output `Benchmarks/reports/browser-evidence/`) are included.

## Verification and experiments

```sh
scripts/swift.sh test
python3 -m unittest discover -s Benchmarks/tests -v
python3 scripts/validate_package.py docs/examples/agent-session
```

The build wrapper places compiler caches in `.build/` for restricted environments. [Native testing](docs/native-testing.md) distinguishes automated verification from remaining interactive checks. [Architecture](docs/architecture.md) explains the independent pipeline modules.

The lean handoff and measurement update (local output `docs/lean-handoff.md`) explains the single-read brief, preserved full-resolution evidence and remaining validation. [Positioning and study design](docs/product-positioning.md) separates human reporting effort from agent tokens and subscription allowance.

The completed 24-attempt old/lean comparison (local output `docs/handoff-comparison-results.md`) reports observed timing/token differences, uncertainty and broader quality-audit failures in both formats. It does not establish human workflow or subscription-allowance savings.

The testing and performance report (local output `docs/testing-report.md`) records the expanded regression suite, remaining interactive checks and measured screenshot-heavy workloads. [Diagnostics](docs/diagnostics.md) describes local logging and repeatable stress checks.

The [benchmark harness](Benchmarks/README.md) includes ten deliberate frontend defects, isolated agent workspaces, Codex/Claude telemetry parsers, operator timing, acceptance/regression checks, reports and charts. It does not run paid agents by default.

**Measured so far:** native app launch and selected-window ScreenCaptureKit capture; unit/integration tests; browser fixture failures and known-good controls; exported image counts and filesystem payload sizes. **Human preparation savings and general workflow speedup remain unmeasured.** A 27-trial scripted GPT-6.1 Sol/high comparison (local output `docs/testing-report.md`) used existing ChatGPT allowance only: ContextLens packages used more agent tokens/time than plain screenshots on these small fixtures. The study is exploratory and does not measure human preparation or progressive image viewing. Operator-timed comparisons remain pending. Read the benchmark report (local output `Benchmarks/reports/benchmark-report.md`) and [engineering report](docs/engineering-report.md).

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md), [competitor review](docs/competitive-analysis.md), and [dependency/licence audit](docs/dependency-audit.md). ContextLens source is [MIT](LICENSE). Browser DOM mapping, MCP, audio, cloud sync and cross-platform capture are outside this MVP.
