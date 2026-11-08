# Homebrew distribution

The available **unnotarized preview** channel uses `contextlens-preview`. See [preview distribution](preview-releases.md) for availability and limitations. The official stable `contextlens` channel is being prepared with a separate, explicit ad-hoc/unnotarized path. **No installable stable cask exists yet.** Project stability never implies Apple verification.

The public [Brendan-Lim/homebrew-tap](https://github.com/Brendan-Lim/homebrew-tap) contains pending cask templates. No installable `Casks/contextlens.rb` is published until actual official assets and acceptance have been verified. Syntax validation is not installation verification. The original Developer ID verification path and its template remain available without relaxed security gates.

## Official unnotarized stable preparation

First complete [exact-candidate isolated acceptance](release-acceptance/README.md) and publish the official release through its separate manual workflow. Then, from the clean source checkout matching that version:

```sh
gh repo clone Brendan-Lim/homebrew-tap /tmp/contextlens-tap-update
.build/dmg-python/bin/python scripts/update-homebrew.py 0.3.1 /tmp/contextlens-tap-update --unnotarized-official
python3 /tmp/contextlens-tap-update/scripts/validate.py
```

This explicit flag selects only the official ad-hoc verifier. It requires a published non-prerelease, exact official asset URLs, downloads both packages/checksums/provenance/acceptance, checks strict ad-hoc signatures, source-tag identity, identical ZIP/DMG bundle inventories and every required human acceptance case. The generated stable cask uses the actual ZIP checksum and GitHub asset ID, retains quarantine, discloses unnotarized signing and conflicts with `contextlens-preview`. It cannot be generated from an unpublished candidate, template or preview receipt. The default updater continues to require Developer ID, notarization and Gatekeeper assessment.

Review and independently commit/push tap changes. Run style, online audit, fetch and a clean install on a disposable Mac before announcing availability. No tap cask is created during preparation and the preview cask remains intact.

## Deliberate preview-to-stable migration

Wait until the official release **and** stable cask are published and verified. Quit ContextLens, save the current session, and back up `~/Library/Application Support/ContextLens/` plus any exported handoffs. Record the installed preview version so it can be reinstalled if necessary.

Uninstall only the preview cask using `brew uninstall --cask contextlens-preview`. This removes the app/CLI link and preserves sessions/settings; do not use `--zap`. Then install the published stable cask with `brew install --cask Brendan-Lim/tap/contextlens`. For a manually installed app, deliberately move the quit app to a safe backup location first. Do not use force/adopt or install two copies sharing the same bundle ID and CLI link.

Reopen the saved session and verify annotations/export before deleting any backup. macOS may require fresh authorization for the new signature; follow the normal user-controlled settings flow. An upgrade preserving prior consent is not a fresh-permission acceptance test.

The template uses Homebrew's Cask DSL: macOS Sonoma (14) minimum, arm64 only, the versioned GitHub release ZIP, `app "ContextLens.app"` and a `binary` artifact linking its embedded `Contents/MacOS/contextlens-cli` into Homebrew's `bin`. It has no fake checksum, `:no_check`, Gatekeeper exception, `zap` or private data deletion.

## Developer ID path: update after a verified notarized release

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
