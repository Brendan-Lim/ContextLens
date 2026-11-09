# Finder installer hidden-file verification

Tested on 2026-11-09. This is development packaging evidence, not official release acceptance. No remaining human security case is marked passed.

## Cause and change

The old builder explicitly created `.background/background.tiff` and an empty `.metadata_never_index` at the volume root. Finder exposed both root entries when Show Hidden Files was enabled. Hidden flags would not solve that setting.

`scripts/build-app.sh` now creates `Contents/Resources/InstallerBackground.tiff` inside the app before any signing. The DMG layout alias points into that bundle on the mounted volume. The packager copies the already signed app without modifying or re-signing it. ZIP and DMG therefore share the same resource and signatures. No artwork, positions, labels, version/build, app behavior or production dependency changed.

The indexing marker is removed. No app or packaging code consumes it. The final image is read-only UDZO, and Apple documents that [disk images are excluded from Spotlight indexing](https://developer.apple.com/library/archive/documentation/Carbon/Conceptual/SpotlightQuery/Concepts/QueryingMetadata.html). The old marker applied to the mounted volume, not an installed app copy. Actual mounting, Finder use, installation and eject were tested without it.

`verify_root` runs on both the configured staging volume and the final mounted image. Its exact allowed inventory is `ContextLens.app`, `Applications` and `.DS_Store`. It rejects auxiliary artwork, indexing markers, indexing directories and any other extra entry. Finder needs `.DS_Store` for the layout and does not display it with hidden files enabled in the tested GUI.

## Genuine Finder evidence

The [disposable prototype run](https://github.com/Brendan-Lim/ContextLens/actions/runs/42623934612) used an ephemeral GitHub-hosted arm64 Mac, macOS 15.8.2, Xcode 26.3, and its real 1024 × 768 desktop at scale 1. The diagnostic branch `qa/dmg-hidden-prototype` applied `qa/prototype.patch` to main `b4453baa79ffe7280ae8af04da13a99ab4b29656` at runtime; production packaging changes remained uncommitted until all four screenshots had been opened and inspected. That patch contains the same packaging implementation and regression tests as this change.

| Show Hidden Files | Appearance | Actual Finder screenshot inspection | Rendered artwork check |
|---|---|---|---|
| Off | Light | Pass: only real app and Applications icons; complete design | Pass; all five sampled artwork regions exactly match |
| Off | Dark | Pass: correct dark titlebar, unchanged design and labels | Pass; all five regions exactly match |
| On | Light | Pass: no auxiliary icons or overlapping text | Pass; all five regions exactly match |
| On | Dark | Pass: no auxiliary icons or overlapping text | Pass; all five regions exactly match |

Each setting had successful preference readback. Finder was restarted when changing hidden-file visibility; each case mounted the real read-only DMG at a fresh private mountpoint. Screenshots captured only the actual Finder window using its verified process/window ID. No Finder window or background was simulated. Finder labels, the owned app icon, icon positions, arrow clearance and full visible design were inspected. Original hidden-file and appearance preferences were restored successfully on the disposable runner. The owner's preferences, installation and privacy permissions were not changed.

The development DMG SHA-256 for this run was `66c077f9c90009fe2f62271f4b046a6618611cd8015a1f4b0c37c58e176ccf25`; its ZIP was `542d0a9156f4dd0b0c37650a5e0e33159ec53a761a6657fabc1d74dc76286dcf`. These are disposable development artifacts, not replacement official candidates. Raw screenshots and diagnostic output were encrypted before upload and decrypted for local inspection. They are not committed as public media.

The prototype also passed UDIF/filesystem checks, strict signatures, exact root inventory, Finder alias/options/positions, real `/Applications` symlink, normal copy round trip, ZIP/DMG bundle inventory equality, real Finder drag installation, clean mount-context detach and normal launch of the installed copy with one window. Installed version/build was 0.3.1/6. The inventory comparison includes every file's bytes, executable bit, signatures and signed Finder/resource metadata. Archive container bytes are intentionally different.

On the local arm64 macOS 26.6.2/Xcode 26.6 build, the relocated TIFF was **byte-identical** to the existing mounted candidate's TIFF: SHA-256 `0efcdaf541cbc70bf00b550ae776dca03bba88e4b582cd06952fc32322422a7b`, 952,400 bytes. ImageIO confirmed two representations, 720 × 440 and 1440 × 880, each with decoded pixels exactly matching its source PNG. The combination command is unchanged. A new live Retina-display Finder matrix was not run; retaining both representations is proven separately from the 1× GUI result.

## Installed-app discovery, investigated separately

Read-only diagnostics on the owner's Mac confirmed the installed app exists with bundle ID `dev.contextlens.app`, version 0.3.1/build 6, package type `APPL`, display name, executable and icon metadata. `codesign --verify --deep --strict` passed. No `.metadata*` or `.noindex` marker was found inside the app.

Outside the execution sandbox, `lsregister -dump` contains a correct `/Applications/ContextLens.app` record, with the expected identifier, display name, executable, arm64 slice, icon and version. Launch Services registration is therefore present. The initial sandbox-only lookup could not see that record and is not used as the conclusion.

`mdls` returned null for bundle identifier, display name and content type. `mdfind` omitted the installed path while returning three other matching paths. `mdutil -s /` and `mdutil -s /System/Volumes/Data` reported `Index is read-only.` Most decisively, `mdimport -t -d2 /Applications/ContextLens.app` successfully used Apple's Application importer and returned the correct identifier, display name and `com.apple.application-bundle` content type. Test mode does not write the index.

This establishes that bundle metadata is extractable and Launch Services knows the app; it points to Spotlight index state rather than an installer metadata defect. The precise reason for the read-only index/stale result was not established. No Spotlight reset, reindex, registration write, quarantine change or owner configuration change was attempted.

Reproduce the diagnostics read-only:

```sh
codesign --verify --deep --strict /Applications/ContextLens.app
plutil -p /Applications/ContextLens.app/Contents/Info.plist
mdls -name kMDItemCFBundleIdentifier -name kMDItemDisplayName -name kMDItemContentType /Applications/ContextLens.app
mdfind 'kMDItemCFBundleIdentifier == "dev.contextlens.app"'
mdutil -s /
mdutil -s /System/Volumes/Data
mdimport -t -d2 /Applications/ContextLens.app
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -dump
```

Inspect only the relevant Launch Services record; keep raw system diagnostics private.

## Automated checks and release boundary

Local `scripts/ci.sh` passed: 117 Swift tests, 49 benchmark Python tests, 82 script tests, 13 package fixtures, 10 deterministic replays, real signed packaging and portability regression, Homebrew syntax/validation, and browser fixtures reproducing 10 defects with 10 passing controls. The two new DMG regression tests failed before the fix and passed afterward. They cover the in-bundle alias and rejection of unexpected top-level entries.

The initial baseline `scripts/verify.sh` stopped because a fresh worktree had no built `dist/contextlens-cli`. After building the baseline and supplying that CLI, the unchanged baseline gate passed. A sandboxed DMG creation attempt was denied; the same operation succeeded with authorized native tool access. These setup limitations are not reported as product failures.

Tracked-file, staged-file, full reachable-history and public-link audits passed with zero findings, as did pinned Gitleaks 8.30.1. No approval hashes or security/freshness rules were changed. CI and Publication Security must also pass on the PR before integration.

The existing unpublished official candidate from prepare run `42614894584`, source `b4453baa79ffe7280ae8af04da13a99ab4b29656`, DMG SHA-256 `e8e7d63c5d604a14f24cffe9596f32fbdcc6eb5d9f4cddfe0643316e039c7cc2`, remains untouched. Integrating these protected packaging inputs requires a **new official preparation and exact-byte acceptance**. No release, stable Homebrew update, auto-merge or human security acceptance is authorized by these development results.
