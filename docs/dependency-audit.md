# Dependency and attribution audit

- ContextLens source: independent implementation, MIT (`LICENSE`). No competitor code or bundled assets.
- Swift/SwiftUI/AppKit/ScreenCaptureKit/CoreGraphics/ImageIO/Carbon/CoreText: platform SDKs supplied by Apple; build dependencies, not vendored source. macOS 14+ is required. SF Symbols and system fonts are used through Apple APIs in the native app, not redistributed as standalone assets.
- Runtime Swift Package Manager dependencies: none. No paid service, telemetry SDK, external font, remote image or analytics script.
- Python benchmark/validation core: standard library. Optional plotting uses Matplotlib 3.9.4 (Matplotlib licence based on PSF); schema cross-check uses jsonschema 4.23.0 (MIT). Their transitive development dependencies remain in local build caches, not app bundles. Skill validation additionally used PyYAML 6.0.2 (MIT).
- Browser development tests: Microsoft Playwright 1.62.1 (Apache-2.0); Chrome/Chromium supplied separately under their own terms. Fixtures use system CSS fonts and contain no third-party assets. Initial downloads were sandbox-blocked; a permitted retry installed Playwright 1.62.1 locally and produced its lockfile. Initial verification used the preinstalled same-version module; final checks use the pinned local module with installed Chrome. Browser version is recorded in fixture reports.
- Agent CLIs: external, optional, user-installed tools. Observed Codex 0.163.0 and Claude Code 2.1.303. They are not redistributed or invoked by the app.
- Competitor documentation was read for public behavior only. Annotake GPL implementation was not incorporated. MarkuprPlus and Shotback MIT code was not copied. Mean has no verified source licence in the reviewed page.

Before distributing a signed binary, review current Apple SDK/SF Symbols distribution terms and sign/notarize under your own developer identity. Local builds use Apple Development when available or fall back to ad-hoc; no distribution credentials are used.
