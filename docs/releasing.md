# Releasing ContextLens

This document describes the future signed/notarized stable channel. The separate [unnotarized preview channel](preview-releases.md) requires no Apple credentials and uses `preview-release.yml`; it does not weaken or replace any gate below.

Public binary distribution is pending Apple credentials. Ordinary pushes run CI and never publish binaries. Only a manual release workflow on current `main` can publish, after tests, Developer ID signing, notarization, stapling, archive verification and Gatekeeper assessment. The app bundle identity remains `dev.contextlens.app`.

## Credential setup

An Apple Developer Program Account Holder must arrange a **Developer ID Application** certificate and its matching private key. An Apple Development certificate is insufficient. Export the identity from Keychain Access as a password-protected `.p12`; keep the file and password outside this repository. Create an App Store Connect team API key with access to notarization and keep its `.p8` private. Do not upload either file to source control.

Configure these seven GitHub Actions repository secrets using GitHub's encrypted Secrets UI or `gh secret set NAME` with stdin/file input. Never include secret values directly in shell command lines or commit them:

| Secret | Value |
|---|---|
| `DEVELOPER_ID_P12_BASE64` | Base64 of the exported Developer ID Application `.p12` |
| `DEVELOPER_ID_P12_PASSWORD` | Export/import password |
| `DEVELOPER_ID_IDENTITY` | Exact identity name beginning `Developer ID Application: ` |
| `APPLE_TEAM_ID` | Expected 10-character Apple signing team |
| `ASC_PRIVATE_KEY_BASE64` | Base64 of the App Store Connect `.p8` |
| `ASC_KEY_ID` | App Store Connect API key ID |
| `ASC_ISSUER_ID` | App Store Connect team issuer UUID |

For example, `base64 < /secure/location/developer-id.p12 | gh secret set DEVELOPER_ID_P12_BASE64 --repo Brendan-Lim/ContextLens` reads the certificate without printing it. Use an interactive secret prompt for passwords. Configure real credentials only; there is no dummy/ad-hoc production mode.

The workflow creates an isolated temporary keychain with a random masked password, imports only the intended signing identity, stores notarytool credentials there, removes temporary secret files, and restores the keychain search list/deletes the temporary keychain in an `always()` cleanup step. Scripts intentionally avoid shell tracing. No signing or private entitlement material is an artifact.

## Publish a new version

1. Update `config/version.json` with a new `X.Y.Z` and increment the numeric build. Keep the bundle ID and deployment target stable. Commit/push `main` and wait for CI.
2. Verify that `vX.Y.Z` and its release do not already exist. Published bytes must never be replaced under an existing version. The preflight rejects existing tags/releases and a dirty/outdated/non-main checkout.
3. Dispatch the release workflow. For the current metadata the command will be:

   ```sh
   gh workflow run release.yml --repo Brendan-Lim/ContextLens --ref main -f version=0.3.0
   gh run list --repo Brendan-Lim/ContextLens --workflow release.yml
   ```

   This command is prepared, **not yet exercised with real signing credentials**.
4. The job runs `scripts/ci.sh`, signs the embedded CLI first and app second using Hardened Runtime and secure timestamps, submits with `xcrun notarytool --wait`, requires `Accepted`, staples the app, and validates both signatures, the ticket and Gatekeeper. No JIT, unsigned-memory, library-validation or sandbox entitlements are needed for this native app; the verifier rejects entitlement exceptions for review.
5. Only then does `ditto` create `ContextLens-X.Y.Z-arm64.zip`, containing the app with the CLI inside. SHA-256 and a provenance receipt are written from the **final stapled archive bytes**. The archive is extracted and verified again. The publisher repeats verification, creates a new tag at the exact checked source commit, uploads to a draft release, then publishes the complete release. A concurrent main change causes failure rather than releasing stale source.
6. Download/verify the public asset and update the tap with the [Homebrew procedure](homebrew.md). Only add user installation commands to the README after a real clean-install check.

GitHub `contents: write` is limited to the manually dispatched release job because it creates the tag and release; ordinary CI has `contents: read`. Checkout and environment setup actions are pinned to reviewed commit SHAs. The workflows select Xcode 26.3 on the supported arm64 `macos-15` image and print the toolchain. Updating that image/toolchain requires another CI check.

## Local signing/notarization

With a real Developer ID Application identity in your keychain, set `CONTEXTLENS_SIGN_IDENTITY` and `CONTEXTLENS_TEAM_ID`. Store notarization credentials interactively using `xcrun notarytool store-credentials ContextLensRelease` (or its supported API-key options). Then:

```sh
scripts/build-app.sh --distribution --output /tmp/contextlens-signed
python3 scripts/release.py notarize /tmp/contextlens-signed/ContextLens.app /tmp/contextlens-release-assets --profile ContextLensRelease
python3 scripts/release.py verify-archive /tmp/contextlens-release-assets/ContextLens-0.3.0-arm64.zip
```

These commands require credentials that were unavailable during setup. They have not been claimed successful. Never pass development archives to the release publisher. `scripts/release.py package` without `--development` requires a properly signed/stapled app and Gatekeeper acceptance.

Signatures and tickets are checked using `codesign --verify --deep --strict`, `xcrun stapler validate` and `spctl --assess --type execute`. Both executables must be arm64, target macOS 14.0, have the expected signing team, Developer ID authority, secure timestamp and runtime flag. The bundle must include its icon, licence, correct version and screen-capture usage string. Dependencies must resolve to system or relative library paths; developer checkout paths are rejected.

## Failure recovery and limits

A signing/notarization/assessment failure never reaches publication. Use the notary submission ID to retrieve its log with `xcrun notarytool log ID --keychain-profile ContextLensRelease`; inspect locally before sharing. A timeout or rejected submission is not acceptance. Fix the cause before retrying.

If publication fails after draft/tag creation, inspect `gh release view vX.Y.Z` and the tag first. The workflow refuses to overwrite them automatically. Recover an unpublished draft deliberately after reviewing provenance; never move a published tag or use asset `--clobber`. Prefer a new version after any public artifact changes.

The process has deterministic version/architecture naming and final-byte checksums. Rebuilding/signing/notarizing can change ZIP bytes and secure timestamps; byte-identical ZIPs across separate builds are **not** claimed. Rehashing an unchanged final file must always agree.

macOS 14 runtime behavior, fresh-user permissions and all interactive release checks remain separate from deployment metadata and unattended CI. Complete [native testing](native-testing.md) before calling a release fully verified. No quarantine removal or Gatekeeper bypass is part of installation.

References checked 8 November 2026: [Apple notarization requirements](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution), [custom notarization workflow](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow), [GitHub runner support](https://docs.github.com/en/actions/reference/runners/github-hosted-runners), [macOS 15 arm64 image toolchain](https://github.com/actions/runner-images/blob/main/images/macos/macos-15-arm64-Readme.md).
