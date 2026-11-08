# Distribution release report — 8 November 2026

## Preview channel follow-up

The free **unnotarized preview** channel is published separately from the stable channel. Base: `0.3.0`, build `5`, bundle ID `dev.contextlens.app`. No paid Apple membership or Apple credentials were used. The optimized app and embedded CLI are ad-hoc signed; there is no Developer ID signature, notarization or claimed Apple trust. The signed `release.yml` and stable `contextlens` cask template are unchanged.

- Source implementation: [`4b463d3`](https://github.com/Brendan-Lim/ContextLens/commit/4b463d3e6dfc3ec4035f89d0e9f8787dee08ff4c).
- Public asset/renderer safety follow-up: [`8b1b89a`](https://github.com/Brendan-Lim/ContextLens/commit/8b1b89a), with [source CI 42471166865](https://github.com/Brendan-Lim/ContextLens/actions/runs/42471166865) passed. Later documentation/template follow-up retains the same immutable release bytes.
- Published prerelease: [`v0.3.0-preview.1`](https://github.com/Brendan-Lim/ContextLens/releases/tag/v0.3.0-preview.1). It is public, not a draft, explicitly a prerelease and never promoted to latest/stable.
- Successful [preview workflow 42469995205](https://github.com/Brendan-Lim/ContextLens/actions/runs/42469995205) and [ordinary CI 42469994983](https://github.com/Brendan-Lim/ContextLens/actions/runs/42469994983).
- Actual public archive: `ContextLens-0.3.0-preview.1-arm64.zip`, 1,447,424 bytes. SHA-256: `1cd84d6b15fc7aed7346ff1fd27382d5d2cd5a51637c7358861ddf55ebe0da45`.
- The independently downloaded archive, checksum and receipt passed `python3 scripts/preview-release.py verify-archive 0.3.0-preview.1 /tmp/contextlens-preview-public-assets/ContextLens-0.3.0-preview.1-arm64.zip`. GitHub's asset digest agrees. Receipt and signed embedded provenance both identify source commit `4b463d3e6dfc3ec4035f89d0e9f8787dee08ff4c`, tree `ef12a53fd58568db84655d5ea8f0fa8dd1fdf8aa` and clean source.
- Hosted build: macOS 15.8.2, arm64, Xcode 26.3 (17C529), Swift 6.2.4. Local isolated verification: arm64 macOS 26.6.2, Xcode 26.6, Swift 6.3.3. No local app was launched or replaced for preview testing.

| Automated preview check | Result |
|---|---|
| Baseline `scripts/verify.sh` | Passed: 80 Swift tests, 49 Python tests, 13 package/schema validations, 10 deterministic replays |
| Full `scripts/ci.sh` in `/tmp/contextlens-preview-source` | Passed, including real-bundle portability rejection, CLI help aliases, development archive round-trip and browser fixtures (10 defects reproduced, 10 known-good controls passed) |
| Full hosted prerelease gate | Same checks passed before publication; 17 release-safety tests passed |
| Preview safety boundaries | Tests introduced red before implementation; invalid/foreign preview versions, Apple identity/team signatures, dirty source, existing tags/drafts, archive sidecar overwrite, changed checksums, stable-trust receipts and missing/foreign assets rejected |
| Real optimized preview build/archive | Passed using `scripts/build-app.sh --preview 0.3.0-preview.1 --output /tmp/contextlens-preview-local-build`; a deliberately supplied Developer ID environment value was ignored and signatures remained ad-hoc |
| Actual overwrite refusal | Repeating local packaging rejected the existing archive/sidecars; its hash stayed unchanged. Repeating source preflight after publication rejected the existing tag |
| Stable channel isolation | Stable archive verification rejected the preview filename. No changes to `.github/workflows/release.yml` or either repository's stable cask template |
| Source publication checks | Ruby/template syntax, Python tests, workflow YAML parsing, Zsh syntax and diff whitespace checks passed; targeted indexed-file scan performed before push |

Homebrew status: **verified preview cask published** in [`Brendan-Lim/homebrew-tap`](https://github.com/Brendan-Lim/homebrew-tap), promoted to main as [`de8dff7`](https://github.com/Brendan-Lim/homebrew-tap/commit/de8dff7) after [final candidate run 42471268060](https://github.com/Brendan-Lim/homebrew-tap/actions/runs/42471268060) passed every applicable check at candidate [`34845f8`](https://github.com/Brendan-Lim/homebrew-tap/commit/34845f8). The only additional tap change is documentation of those results. The exact tested app archive, checksum, cask, validator and install-test script were preserved during promotion. The stable cask remains an unchanged template; no `Casks/contextlens.rb` was published.

Verified installation command:

```sh
brew install --cask Brendan-Lim/tap/contextlens-preview
```

| Final disposable macOS installation checks | Result |
|---|---|
| Machine | GitHub-hosted arm64 macOS 15.8.2, Homebrew 7.0.12 |
| Ruby/template validation, `brew style --cask`, `brew audit --cask --online`, `brew fetch --cask` | Passed against the exact candidate checkout |
| Existing app protection | Default install refused a foreign `/Applications/ContextLens.app`; its marker remained unchanged |
| Actual default install | Passed; `/Applications/ContextLens.app` installed, `/opt/homebrew/bin/contextlens-cli` linked to its embedded executable |
| Signature integrity and quarantine | Strict codesign verification passed; `com.apple.quarantine` remained present |
| CLI | Installed `contextlens-cli --help` passed |
| Gatekeeper read-only assessment | Returned 3, `/Applications/ContextLens.app: rejected`; no Apple trust or acceptance claimed |
| Uninstall | `brew uninstall --cask Brendan-Lim/tap/contextlens-preview` passed; app and CLI link removed, synthetic session JSON and exported context marker preserved |
| User environment | Local working app, Homebrew installation, TCC permissions, sessions and exports were not replaced or reset |

The candidate test uses an exact-commit custom tap remote on a fresh runner so a PR/candidate cannot accidentally test stale main. Final main-branch CI repeats the same checks. This is an automated install/uninstall check, not an interactive fresh-user launch test.

Two candidate checks found Homebrew integration defects before installation: [42470179665](https://github.com/Brendan-Lim/homebrew-tap/actions/runs/42470179665) rejected `brew style --cask Casks/contextlens-preview.rb` outside Homebrew's tap directory; the corrected command uses the fully qualified token after tapping the exact candidate checkout. [42470264257](https://github.com/Brendan-Lim/homebrew-tap/actions/runs/42470264257) then required the current `depends_on macos: :sonoma` spelling. Preview template/cask/validator were corrected together; the stable template was preserved. These failures are retained as evidence, rather than described as successful installs.

[42470363208](https://github.com/Brendan-Lim/homebrew-tap/actions/runs/42470363208) passed style and exposed Homebrew's item-trust prerequisite for online audit. The job now exercises the fully qualified install before audit: [Homebrew documents](https://docs.brew.sh/Tap-Trust) that this explicitly selects/trusts only that cask. No whole-tap trust or trust-disabling setting is used. This affects Homebrew's permission to load a selected package definition, not macOS Gatekeeper authorization; quarantine remains enabled.

[42470518372, attempt 1](https://github.com/Brendan-Lim/homebrew-tap/actions/runs/42470518372/attempts/1) selected the cask normally but GitHub's browser download URL returned HTTP 504 on every retry, before app-conflict or installation assertions could run. A separate unauthenticated `curl` request reproduced that failure. GitHub's [documented public release asset endpoint](https://docs.github.com/en/rest/releases/assets#get-a-release-asset), `https://api.github.com/repos/Brendan-Lim/ContextLens/releases/assets/723563642` with `Accept: application/octet-stream`, downloaded 1,447,424 bytes without any token and matched the exact published SHA-256. The unpublished candidate was regenerated to use that immutable API asset ID, with explicit ZIP container handling. The source updater validates both browser/API URLs and positive integer IDs. Expanded safety tests failed before this implementation and now pass. The release assets and tag were not changed.

[42470888863](https://github.com/Brendan-Lim/homebrew-tap/actions/runs/42470888863) passed real installation/uninstallation on arm64 macOS 15.8.2 with Homebrew 7.0.12: existing-app refusal, default `/Applications/ContextLens.app` placement, `/opt/homebrew/bin/contextlens-cli` symlink, strict signature integrity, retained quarantine, installed CLI `--help`, and preserved synthetic session/export markers after uninstall. Read-only `spctl --assess --type execute -vv /Applications/ContextLens.app` returned **3, rejected**, as expected for an unnotarized preview. No GUI launch or authorization was automated. Online audit then treated the literal numeric API URL as unversioned. The cask now models preview version plus immutable asset ID using Homebrew's standard comma-separated version (`0.3.0-preview.1,723563642`) and `version.csv.second` in the URL. The exact SHA-256 remains required; no `:no_check` was introduced. Tests were red before this correction and green afterward. The final combined verification subsequently passed, as recorded above.

[42471090097](https://github.com/Brendan-Lim/homebrew-tap/actions/runs/42471090097) repeated the successful install/uninstall checks with that version format; the remaining audit error was HTTP 504 for the repository homepage. An unauthenticated request to the same repository with its canonical trailing slash, `https://github.com/Brendan-Lim/ContextLens/`, returned HTTP 200 and the correct repository title/source/README. The preview homepage now uses that form. No audit check was disabled or suppressed.

| Interactive check | Status / limitation |
|---|---|
| First launch and actual Gatekeeper dialog | Pending: no disposable interactive macOS environment available |
| User-controlled Open Anyway | Pending: requires a person after verifying origin; no authorization or exception was automated |
| Fresh-user Screen Recording | Pending; existing permissions were not changed or reset |
| Disposable-window capture, Review/Mark Up, Hand Off | Pending as an installed-preview interactive workflow; existing deterministic export/replay checks passed |
| CLI after manual authorization | Pending independently of app authorization; CLI help during bundle verification passed |
| macOS 14 runtime and Intel | Unverified; Apple Silicon only, macOS 14 deployment metadata verified |

No quarantine removal, global Gatekeeper disabling, force/adopt installation, TCC reset or existing-user capture was used. Only temporary builds/fixtures and disposable hosted runners were used. Sessions and exported packages remain outside uninstall hooks. The practical free route is the published preview ZIP and its verified separate Homebrew cask. The remaining blockers are a disposable interactive macOS session/person for manual Open Anyway, fresh Screen Recording and capture/Hand Off checks; macOS 14 runtime and upgrades also remain untested. Apple credentials are required only for the future trusted stable channel. [First-time-user instructions](preview-releases.md) explain verification, Apple's Open Anyway process, permissions, channel conflicts and preserved user data.

## Historical signed-release infrastructure report

The sections below retain the earlier signed-release infrastructure report as historical evidence; their pending-publication statements describe that earlier stable-channel work.

**State B: release infrastructure prepared; Apple credentials pending.** No public binary release or installable Homebrew cask is claimed. Initial source, release infrastructure and the pending tap are public. Available local checks and hosted CI passed; signing and real installation remain unverified.

## A. Initial GitHub publication

- Created initial commit [`c6ac254657743335f8e28d77e61e9987bcbe90bc`](https://github.com/Brendan-Lim/ContextLens/commit/c6ac254657743335f8e28d77e61e9987bcbe90bc), `feat: initial open-source ContextLens implementation`.
- Successfully pushed to `main` at `https://github.com/Brendan-Lim/ContextLens.git` **before** implementing distribution. `git ls-remote origin refs/heads/main` matched the local SHA. No force push, history replacement or local evidence deletion occurred.
- Verified the repository was public and empty immediately before the push. Afterward, GitHub served the source directory listing, rendered README HTML and recognized MIT licence. The indexed public set was inspected; targeted scanning found no credentials. A scanner is not a formal proof of absence.
- Initial public set: 461 files, including production source/tests, schemas, integrations, owned branding, reusable experiment/evaluator source, synthetic telemetry, demo packages and ten owned browser replay fixtures.
- Excluded: `.build/`, `dist/`, dependency caches, environment/signing files, `Benchmarks/runs/`, all `Benchmarks/reports/` except `browser-evidence/`, `Experiments/*/reports/`, generated experimental build output, top-level native screenshot/permission receipts under `docs/examples/`, seven historical research reports and four historical report writers embedding account observations. This excludes private agent conversations, authorization receipts, account/Education allocation/billing snapshots, trial workspaces and generated evidence while retaining originals locally. See [.gitignore](../.gitignore) and [audit details](publication-audit.md).

## B. macOS release build

| Check | Actual result |
|---|---|
| Version / build / identifier | `0.3.0` / `5` / `dev.contextlens.app`, preserved from the original build script; now centralized in `config/version.json` |
| Optimized build | `scripts/build-app.sh` and isolated `--output /tmp/contextlens-release-check` passed |
| Architecture | Native `file`/`lipo` verification: arm64 for app and CLI |
| Intel investigation | Both executables cross-compiled with `--arch x86_64`; no Intel execution, packaging or distribution claim |
| Minimum OS | SwiftPM macOS 14, Info.plist `14.0`, both Mach-O `minos 14.0`, cask Sonoma requirement agree |
| Runtime environment | arm64 Mac; macOS 26.6.2 (25G83), Xcode 26.6 (17F113), Swift 6.3.3; macOS 14 runtime unverified |
| Bundle | Correct plist, executable/icon/licence, embedded signed CLI, screen-capture usage string, portable library dependencies and no embedded developer checkout paths |
| CLI | Embedded `Contents/MacOS/contextlens-cli`; separate development copy retained; `--help` and `-h` execute successfully with all supported commands listed |
| Local packaging | `ContextLens-0.3.0-arm64-development.zip` created with ditto, extracted and re-verified; final-byte checksum rechecked successfully |
| Intended trusted asset | `ContextLens-0.3.0-arm64.zip`; **not created or published**, because trust gates cannot pass without credentials |

The final local development archive under `/tmp/contextlens-final-package/` has SHA-256 `9f7e33384adff567e2bd60a71ba10e2a8b3ead5c36ae3fc37c2ae363b6487e1d`. This is a **local development artifact, not a public release checksum**. Its receipt explicitly records the initial source HEAD and `sourceDirty: true` for the in-progress infrastructure changes. Separate rebuilds/signing timestamps need not produce identical ZIP bytes.

A background app launch rendered `/tmp/contextlens-distribution-smoke.png` at 2×, which was opened and inspected. The first restricted-sandbox attempt aborted; the same background-only command passed with ordinary WindowServer access. No other application's window was captured and the app was not activated. This verifies development launch, not fresh-user Gatekeeper acceptance.

## C. Signing and notarization

- Distribution signing is implemented: Developer ID Application, expected Apple team, Hardened Runtime, secure timestamps, CLI first and bundle second; no broad entitlement exceptions.
- Actual local signing used the existing **Apple Development** identity. It does not establish public distribution trust. A development signature was explicitly rejected by the distribution verifier.
- Only an Apple Development identity was found by `security find-identity -v -p codesigning`; no suitable Developer ID Application identity was available. No repository signing/notarization secrets were configured.
- Developer ID signing **not performed**; Apple notarization **not submitted/accepted**; trusted stapling and Gatekeeper assessment **not completed**. Development-mode signature integrity did pass.
- `--distribution` fails before building when a suitable identity is absent; public packaging requires trusted signatures, a clean source checkout, a valid staple and Gatekeeper acceptance. The normal release workflow cannot publish on a failed gate.
- Remaining setup: Developer Program access, Developer ID Application certificate plus matching private key/password, expected Apple team, and App Store Connect notarization API key/key ID/issuer. [Exact seven secret names and setup](releasing.md).

## D. GitHub Actions and local checks

Workflows: `.github/workflows/ci.yml` (main pushes, PRs to main, optional manual CI), `.github/workflows/release.yml` (manual version input, main only), and the separate tap's `.github/workflows/validate.yml`. All used actions are pinned to commit SHAs; ordinary jobs have read-only contents permission. Only the release publication job has contents write permission. No paid/model study or interactive TCC capture runs in CI.

| Verification | Evidence / result |
|---|---|
| Initial hosted source gate | [Run 42459309989](https://github.com/Brendan-Lim/ContextLens/actions/runs/42459309989), **passed** |
| Tap hosted template gate | [Initial run 42459961923](https://github.com/Brendan-Lim/homebrew-tap/actions/runs/42459961923) and [candidate-commit audit workflow run 42460311343](https://github.com/Brendan-Lim/homebrew-tap/actions/runs/42460311343), **passed** |
| New infrastructure CI | [Infrastructure run 42460312944](https://github.com/Brendan-Lim/ContextLens/actions/runs/42460312944) and [final code run 42460499697](https://github.com/Brendan-Lim/ContextLens/actions/runs/42460499697), **passed**; final code commit `3d5a33df09086e84e1d05bf236e6335212d4bf57` |
| Release signing workflow | Not dispatched with unavailable credentials; notarization/publication remain unverified |
| `scripts/verify.sh` | **80 Swift tests, 49 Python tests, 13 packages including independent JSON Schema validation, 10 deterministic replays — passed** |
| `python3 -m unittest discover -s scripts/tests -v` | **9 release/archive-safety tests passed** |
| `python3 scripts/verify-release-build.py` | Real-bundle portability regression and CLI help aliases **passed** |
| Browser controls | **10 defects reproduced, 10 known-good controls passed**, with shared regression checks |
| YAML / shell / Python parsing | Three workflow YAML files, Bash/Zsh syntax and Python compilation **passed** |
| Pending cask validation | Ruby syntax and template metadata checks **passed**; no install test implied |
| Publication scan | Indexed-file targeted pattern scan and manual metadata/image review; repeated before final push |

A fresh clone from the published GitHub repository into `/tmp/contextlens-clean-source` built successfully and passed 80 Swift tests, 49 Python tests, 13 package checks and ten replays. That clean clone lacked the optional jsonschema development dependency, so its gate explicitly reported the independent schema cross-check as unavailable; the primary workspace and hosted CI did perform it. The clean-clone CLI help also passed.

The initial packaging attempt failed because unstripped Mach-O debug object records contained absolute developer paths. The build now strips staged executables before signing. `scripts/verify-release-build.py` reintroduces that exact defect in a disposable bundle and requires the verifier to reject it, while the final bundle passes. The original SwiftPM products and existing apps are preserved. A fresh-clone regression run then exposed a `/Users`-only path assumption. The verifier now rejects the actual checkout root as well; the unstripped `/tmp` fixture failed before that correction and passed the rejection check afterward. Both checkout locations and all nine release tests pass with the correction.

The default local browser check initially failed because Playwright's expected headless shell was not installed. This environment issue was resolved for local verification using:

```sh
CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' node Benchmarks/runners/verify-fixtures.mjs
```

Hosted CI installs the matching Playwright browser instead. A Python bytecode compilation attempt was sandbox-blocked writing to a system cache; setting `PYTHONPYCACHEPREFIX="$PWD/.build/python-cache"` passed. Neither issue was represented as a successful check before resolution.

Repeatable packaging checks:

```sh
scripts/build-app.sh
scripts/verify.sh
python3 -m unittest discover -s scripts/tests -v
python3 scripts/verify-release-build.py
python3 distribution/homebrew/scripts/validate.py
python3 scripts/release.py package dist/ContextLens.app /tmp/new-contextlens-archives --development
(cd /tmp/new-contextlens-archives && shasum -a 256 -c ContextLens-0.3.0-arm64-development.zip.sha256)
```

Use a new archive output directory. Public packaging rejects archive replacement, development signatures, altered checksums, invalid receipt trust, archive traversal and symlinks. Tests cover these boundaries. Local detailed logs/snapshots remain OS-temporary evidence and were not published as historical execution dumps.

Source release infrastructure was committed and pushed as [`46deeaa9a0a7e997877f983a095f486c3d30b7ec`](https://github.com/Brendan-Lim/ContextLens/commit/46deeaa9a0a7e997877f983a095f486c3d30b7ec), `build: add macOS release packaging and Homebrew distribution`. The remote main SHA matched after push. The checkout-root portability correction was pushed as [`3d5a33df09086e84e1d05bf236e6335212d4bf57`](https://github.com/Brendan-Lim/ContextLens/commit/3d5a33df09086e84e1d05bf236e6335212d4bf57), with its hosted CI passing. This report is finalized in a subsequent documentation-only commit; no force push was used. A final GitHub tree/index comparison matched all 482 public files, and rendered README HTML included the pending-installation warning.

## E. GitHub Releases

**No actual release, tag or trusted archive is published.** GitHub returned HTTP 404 for release tag `v0.3.0`; release listing was empty. There is no release URL or public archive SHA-256 to provide. The workflow will create a new matching tag at the checked source commit and publish complete assets through a draft after all gates pass. Existing tags/releases cause failure, and no asset-clobber path exists.

## F. Homebrew

- Created and pushed [Brendan-Lim/homebrew-tap](https://github.com/Brendan-Lim/homebrew-tap), initial commit [`296a83b87e22b7e6f7c4ee2beab935ab0928277e`](https://github.com/Brendan-Lim/homebrew-tap/commit/296a83b87e22b7e6f7c4ee2beab935ab0928277e).
- Latest tap follow-up: `cd526e3`, auditing the exact candidate checkout rather than a potentially stale remote copy.
- Available: `Casks/contextlens.rb.in`, explicit pending README, Ruby/template validator and passing hosted workflow. **No `Casks/contextlens.rb` exists**.
- Exact Homebrew command/DSL syntax checked against installed Homebrew 7.0.10 and official documentation. The template links the embedded CLI and restricts architecture/OS appropriately. It does not contain a fabricated checksum or nonexistent concrete release URL.
- The real update script attempted `v0.3.0`, received HTTP 404, stopped and left the tap without a cask. It requires actual downloaded assets and expected-team signature/notarization checks before writing anything.
- Tap repository discovery/authentication and pending-template syntax passed. A real cask audit, download checksum, Homebrew install, installed app launch, Homebrew CLI link, uninstall and upgrade **have not been tested**. The standalone packaged development CLI did run successfully.
- No installed app, CLI link, session, permission record or system security setting was removed/overwritten for Homebrew testing. Normal development rebuilds preserve retired bundles.
- [Upgrade/uninstall and isolated installation procedure](homebrew.md) is documented; upgrade needs two verified published versions. The tap intentionally has no `zap` stanza deleting sessions.
- Tap updates are deterministic local generation from published bytes; no cross-repository secret is needed. A future GitHub App should have Contents access only to this tap; the main repository's `GITHUB_TOKEN` is not assumed to write there.

## G. Remaining blockers and limits

1. Configure real Developer ID and notarization credentials, then successfully execute the release workflow. Check the downloaded final asset, its signature/team/runtime/timestamp, notary acceptance, staple and Gatekeeper.
2. Generate/audit/publish the real cask from that verified release and complete a clean Homebrew install/launch/CLI/uninstall test in a disposable account/VM. Verify an upgrade only after another trusted version exists.
3. Complete fresh-user Screen Recording and optional Accessibility consent plus the interactive [native checklist](native-testing.md); macOS 14 runtime and Intel remain unverified. The pre-existing native self-test closure-detection limitation (`closure_detected_without_fallback: false`) remains documented in the agent guide; this distribution task does not claim it fixed or rerun all capture checks.

No Gatekeeper bypass, quarantine removal, fake signing secret, ad-hoc public release or misleading installation claim was used. No new agent/model study ran.

## H. Installation instructions

**Verified source-build path** (requires Xcode/Swift on an Apple Silicon Mac):

```sh
git clone https://github.com/Brendan-Lim/ContextLens.git
cd ContextLens
scripts/build-app.sh
open dist/ContextLens.app
dist/contextlens-cli --help
```

Build, CLI execution and background app launch have been exercised; `open` is the normal interactive launch command and is left to the person to avoid taking focus. Grant Screen Recording when macOS requests it; Accessibility labels are optional.

**Pending final release setup — do not use yet:** `brew install --cask Brendan-Lim/tap/contextlens`, followed by `open -a ContextLens` and `contextlens-cli --help`. After clean installation is proven, `brew update`, `brew upgrade --cask contextlens` and `brew uninstall --cask contextlens` are the intended maintenance commands. These are documented future commands, not verified installation results.
