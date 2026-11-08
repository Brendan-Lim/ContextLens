# Build from source

For free binary downloads without Apple credentials, see the separate [unnotarized preview channel](preview-releases.md). The source-build instructions below remain available for local compilation and verification.

Use an Apple Silicon Mac running macOS 14 or newer and Xcode with Swift 5.10 or newer. There are no production dependencies. Local verification used macOS 26.6.2, Xcode 26.6 and Swift 6.3.3. Hosted CI selects Xcode 26.3 on `macos-15` and records the actual versions. macOS 14 is the deployment target; execution on macOS 14 has not been verified.

```sh
git clone https://github.com/Brendan-Lim/ContextLens.git
cd ContextLens
scripts/build-app.sh
open dist/ContextLens.app
dist/contextlens-cli --help
```

The build preserves `dev.contextlens.app`, reads `config/version.json`, includes the owned `Brand/AppIcon.icns` and MIT licence, and embeds the companion in `ContextLens.app/Contents/MacOS/contextlens-cli`. It also retains the established separate `dist/contextlens-cli` path. Previously built app bundles are retained in `dist/.contextlens-previous.*`; user sessions are not changed. Compiler caches stay under `.build/`.

Development signing uses an available Apple Development identity or falls back to ad-hoc. Select an identity with `CONTEXTLENS_SIGN_IDENTITY`; set it to `-` for ad-hoc CI. Development signatures do not provide Developer ID distribution trust. A change in signing identity can require fresh macOS Screen Recording consent; see [permissions](permissions.md).

Use a disposable build destination without replacing your current development app:

```sh
scripts/build-app.sh --output /tmp/contextlens-local-build
python3 scripts/release.py verify /tmp/contextlens-local-build/ContextLens.app
python3 scripts/release.py package /tmp/contextlens-local-build/ContextLens.app /tmp/contextlens-local-archives --development
```

Archive output must be new. Development archives have an explicit `-development.zip` suffix and receipt; they cannot pass distribution verification. Release executables are stripped of debug object paths before signing. Original unstripped SwiftPM products remain available in `.build/`.

Run the automated checks:

```sh
scripts/build-app.sh
scripts/verify.sh
python3 -m unittest discover -s scripts/tests -v
python3 distribution/homebrew/scripts/validate.py
```

Independent schema validation requires `jsonschema==4.23.0`. CI installs it with Python 3.12, uses Node 24 and installs the pinned Playwright/Chromium development fixtures. `scripts/ci.sh` runs the full deterministic job; it does not invoke models, request TCC consent or capture personal windows. It requires the development Python/Node dependencies and network access for browser installation. See [benchmark setup](../Benchmarks/README.md).

Only arm64 packaging is supported. An x86_64 cross-build of both Swift executables succeeded on the development machine, using `scripts/swift.sh build -c release --arch x86_64 --scratch-path /tmp/contextlens-intel-probe`. It was not executed on Intel hardware, packaged or notarized; Intel compatibility is unverified and is not advertised. Future architecture support needs bundle verification, runtime testing and a separate `ContextLens-VERSION-ARCH.zip` asset/cask definition.
