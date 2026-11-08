# Unnotarized preview distribution

ContextLens 0.3.0 has a separate preview channel for Apple Silicon Macs running macOS 14+. It needs no paid Apple Developer membership or Apple credentials. Builds use optimized arm64 Swift products and ad-hoc signatures for code integrity. They have **no Developer ID signature, Apple notarization or promised Gatekeeper acceptance**. These prereleases are never marked latest/stable. macOS 14 is the deployment target; hosted runtime checks use macOS 15.

Published: [v0.3.0-preview.1 — Unnotarized Preview](https://github.com/Brendan-Lim/ContextLens/releases/tag/v0.3.0-preview.1), after [all preview workflow checks passed](https://github.com/Brendan-Lim/ContextLens/actions/runs/42469995205). The public ZIP was downloaded independently and verified. Homebrew candidate installation/uninstallation passed; final audit and promotion are in progress. The interactive installed-preview workflow remains pending. The stable `contextlens` template and signed `release.yml` remain separate. [Detailed release report](distribution-release-report.md).

Public archive SHA-256: `1cd84d6b15fc7aed7346ff1fd27382d5d2cd5a51637c7358861ddf55ebe0da45`.

During verification GitHub's browser asset URL returned HTTP 504, while the official public asset API served the identical ZIP without credentials. The preview cask uses that immutable asset ID with `Accept: application/octet-stream` and the same SHA-256. Its Homebrew version combines preview version and asset ID as `0.3.0-preview.1,723563642`. No account, token or compiler is required. If the release page download fails, this credential-free download was tested:

```sh
curl --fail --location --header 'Accept: application/octet-stream' \
  --output ContextLens-0.3.0-preview.1-arm64.zip \
  https://api.github.com/repos/Brendan-Lim/ContextLens/releases/assets/723563642
shasum -a 256 ContextLens-0.3.0-preview.1-arm64.zip
```

Compare the output with the full checksum above before extracting and authorizing the app. This downloads files only; it does not alter macOS security.

## For a first-time user

1. Review the source and the release at the official [ContextLens repository](https://github.com/Brendan-Lim/ContextLens). Use only an explicitly labeled **Unnotarized Preview**. Confirm its version, source commit and published checksum. Ad-hoc signing does not authenticate the developer; neither a checksum nor passing tests makes it Apple-verified.
2. Download the versioned ZIP and its `.zip.sha256` from that release. In the download directory run `shasum -a 256 -c ContextLens-0.3.0-preview.1-arm64.zip.sha256`. The checksum should report `OK`. Stop if it differs. A checksum obtained from the same release protects against mismatched downloads, not compromise of the release account.
3. For a direct download, extract the ZIP and drag `ContextLens.app` into Applications. If you already have a copy, quit it and deliberately back it up before switching. Do not overwrite your working app just to try the preview. The channels share a bundle ID, session location and CLI name; they are not isolated side-by-side installations.
4. Try opening ContextLens. If macOS blocks it because the developer cannot be verified or Apple cannot check it, dismiss the alert. Only if you trust the origin and intact download, open **System Settings → Privacy & Security**, scroll to the blocked-app notice, choose **Open Anyway**, and confirm **Open**. Follow [Apple's instructions](https://support.apple.com/en-us/102445). This is your decision for this app; do not disable Gatekeeper or remove quarantine. If macOS reports malware, corruption or a revoked app, stop and investigate. Managed Mac policies may prevent authorization.
5. Grant Screen Recording to this copy in System Settings → Privacy & Security → Screen & System Audio Recording (Screen Recording on older macOS), then relaunch if requested. Accessibility is optional for clicked-control captions. Preview updates can require fresh consent because ad-hoc signatures change. Do not reset existing permissions to test installation.
6. Open a disposable window containing no private information, choose **New capture**, select only that window, start/stop capture, review a state, add a mark and note, then **Save Hand Off** to a temporary folder. Check `context.md`, `manifest.json` and the images. Nothing uploads or runs an agent automatically.
7. The CLI is embedded at `/Applications/ContextLens.app/Contents/MacOS/contextlens-cli`. Homebrew links it as `contextlens-cli`; try `contextlens-cli --help` after authorization. macOS may require a separate decision for the CLI; successful app authorization does not prove CLI authorization. If blocked, use the same Apple-supported settings process if available, or use a source build. No security-bypass command is supplied.

Homebrew's intended preview token is **`Brendan-Lim/tap/contextlens-preview`**. Availability and verified commands will be recorded here after publication checks. Homebrew keeps quarantine enabled. Default installation must refuse conflicting apps or CLI links; do not use force/adopt options to replace a working copy inadvertently. Remove a Homebrew-managed old channel deliberately before installing the other one. Never install the stable `contextlens` token expecting a preview.

Uninstalling the preview with Homebrew removes its app and CLI link. It does not delete `~/Library/Application Support/ContextLens/`, session folders selected elsewhere, preferences or exported packages. There is no `zap` or data-deletion hook. Back up valuable sessions before trying preview software; this uninstall policy is not a guarantee against application bugs.

## Maintainer workflow

From clean, current `main` at version 0.3.0, choose an unused numbered preview:

```sh
gh workflow run preview-release.yml --repo Brendan-Lim/ContextLens --ref main -f version=0.3.0-preview.1
gh run list --repo Brendan-Lim/ContextLens --workflow preview-release.yml
```

The manually dispatched job runs all deterministic CI checks: Swift/Python regressions, schemas/packages, replays, real-bundle portability rejection, development packaging and owned browser fixtures. It builds again using `scripts/build-app.sh --preview VERSION --output DIRECTORY`, which forces ad-hoc signing even if an Apple identity/environment variable exists. No Apple secrets, keychain import, notarytool, stapler, Gatekeeper exception or quarantine manipulation is involved in the preview workflow.

The signed bundle includes `Contents/Resources/preview.json` with source repository, exact commit and tree, clean-source assertion, base/preview versions and compiler/OS versions. The final ZIP, `.zip.sha256` and `.zip.json` receipt use the preview version. Packaging extracts and verifies the final archive and compares embedded provenance. ZIP bytes are not promised identical across rebuilds; the recorded Git commit/tree makes the source reproducible, and the SHA-256 identifies the actual immutable download.

Publication repeats source/version/tag/release and archive checks. Atomic Git ref creation rejects an existing or racing tag, including an incomplete prior attempt. Assets upload to a draft prerelease before it becomes visible; no force, clobber or stable/latest promotion is used. If publication partially fails, inspect the tag/draft and choose a new preview number. Do not automatically delete or overwrite the previous attempt.

Generate the cask only from the actual published prerelease:

```sh
gh repo clone Brendan-Lim/homebrew-tap /tmp/contextlens-preview-tap
python3 scripts/preview-release.py update-tap 0.3.0-preview.1 /tmp/contextlens-preview-tap
```

This checks official browser/API URLs and asset IDs, uploaded assets, downloaded checksum, preview trust label, signatures, portable arm64 bundle, receipt and matching source tag before rendering `Casks/contextlens-preview.rb`. It cannot generate a cask for a draft or stable release or a fabricated checksum. It never changes `Casks/contextlens.rb` or its template. Run tap validation, `brew style`, online audit, download verification and the disposable hosted installation check on a candidate branch before publishing the tap's main branch. Then update the status here with evidence. No cross-repository secret is needed; use existing maintainer authorization.

## Installation verification

A fresh GitHub macOS runner can check the real cask download/checksum, default app placement, CLI symlink, default refusal to overwrite a foreign app and uninstall preservation using a synthetic session marker. These checks do not prove a human can authorize launch or grant TCC permission. Do not launch preview copies on a development machine with an existing ContextLens identity/permission record to simulate a fresh user.

In a disposable **interactive macOS environment**, record pass/fail for first launch and actual Gatekeeper warning, manual Open Anyway, app/CLI execution after authorization, Screen Recording, disposable-window capture/Mark Up/Hand Off, preserved sessions after uninstall and macOS 14 runtime. Until observed, these are **pending**. A custom `--appdir` on the current machine is insufficient isolation: Homebrew links/Caskroom, bundle identity and TCC consent are shared. No clean local macOS VM is currently available.

References: [Homebrew Cask Cookbook](https://docs.brew.sh/Cask-Cookbook), [Homebrew Tap Trust](https://docs.brew.sh/Tap-Trust) (fully qualified installation selects only that cask), [GitHub public release asset API](https://docs.github.com/en/rest/releases/assets#get-a-release-asset), [Apple: safely open apps on your Mac](https://support.apple.com/en-us/102445). See [signed release instructions](releasing.md) and [stable Homebrew process](homebrew.md) for the future trusted channel.
