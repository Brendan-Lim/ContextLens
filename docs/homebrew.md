# Homebrew distribution

The separate **unnotarized preview** channel uses `contextlens-preview`. See [preview distribution](preview-releases.md) for availability, limitations and verification status. The remainder of this document describes the future signed/notarized **stable** `contextlens` channel; its gates and template are unchanged.

The public [Brendan-Lim/homebrew-tap](https://github.com/Brendan-Lim/homebrew-tap) contains a pending cask template. No installable `Casks/contextlens.rb` is published until a real Developer ID signed, notarized release exists. Syntax validation is not installation verification.

The template uses Homebrew's Cask DSL: macOS Sonoma (14) minimum, arm64 only, the versioned GitHub release ZIP, `app "ContextLens.app"` and a `binary` artifact linking its embedded `Contents/MacOS/contextlens-cli` into Homebrew's `bin`. It has no fake checksum, `:no_check`, Gatekeeper exception, `zap` or private data deletion.

## Update the tap after a verified release

From a clean source checkout matching the release metadata, with `gh` authenticated and `CONTEXTLENS_TEAM_ID` set to the expected Apple team:

```sh
gh repo clone Brendan-Lim/homebrew-tap /tmp/contextlens-tap-update
python3 scripts/update-homebrew.py 0.3.0 /tmp/contextlens-tap-update
python3 /tmp/contextlens-tap-update/scripts/validate.py
```

The updater requires a clean tap checkout with the official origin, a published stable GitHub release, exact asset names/URLs, the actual downloaded SHA-256, a matching receipt/source commit, Developer ID signatures from the expected team, stapling and Gatekeeper acceptance. Only then does it atomically render a real cask. Updates must move forward in version. Missing assets/credentials cause failure before writing a cask.

After generation, validate with Homebrew against that inspected checkout. A maintainer may first publish the reviewed cask so `brew tap Brendan-Lim/tap` can discover it, then run the following checks before announcing installation:

```sh
brew tap Brendan-Lim/tap
brew style --cask /tmp/contextlens-tap-update/Casks/contextlens.rb
brew audit --cask --online Brendan-Lim/tap/contextlens
brew fetch --cask Brendan-Lim/tap/contextlens
```

Review `git diff` in the tap checkout, commit and push independently. The main repository's default `GITHUB_TOKEN` cannot write to this separate repository; the updater uses the maintainer's local authentication and never commits or pushes automatically. No cross-repository token is currently configured. If automating later, use a GitHub App installation token limited to this tap's Contents permission, and run the same verification before opening an update PR. A broad personal token is unnecessary.

## Clean-install verification (pending)

Use a fresh macOS account/VM or disposable Homebrew installation. Preserve an existing manually installed app by moving it to a safe backup location; do not force-overwrite it. A custom `--appdir` isolates the app but does **not** isolate Homebrew's CLI symlink or Caskroom, so a custom app directory alone is insufficient if those already contain ContextLens.

Once the cask exists, record actual results for:

```sh
brew install --cask Brendan-Lim/tap/contextlens
open -a ContextLens
contextlens-cli --help
brew list --cask contextlens
brew uninstall --cask contextlens
```

Check `/Applications/ContextLens.app`, `command -v contextlens-cli`, permissions, an own/disposable-window capture, and exported evidence. No compiler should be needed. App launch is interactive and should not steal focus during background engineering checks. Uninstall removes the app and CLI link; sessions under `~/Library/Application Support/ContextLens/` and user exports remain intact.

Upgrade requires two genuinely verified releases and a clean install of the earlier version. Only then test `brew update` and `brew upgrade --cask contextlens`, verify the new version/signatures/CLI and preserved sessions. An upgrade command with no second version is not an upgrade test.

These installation/upgrade/uninstall commands are **future instructions, not successful test results**. No signed public release exists yet. See the [release report](distribution-release-report.md) for status.

References checked 8 November 2026: [Cask Cookbook](https://docs.brew.sh/Cask-Cookbook) (minimum OS, arm64 and embedded binary DSL), [Homebrew commands](https://docs.brew.sh/Manpage) (install, update, upgrade, uninstall, audit, style and appdir options). Local command syntax was checked with Homebrew 7.0.10; installation was deferred to protect the current app and because no trusted artifact exists.
