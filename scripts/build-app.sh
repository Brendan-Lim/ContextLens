#!/bin/zsh
set -eu
cd "${0:A:h:h}"
scripts/swift.sh build -c release
mkdir -p "$PWD/dist"
build_stage=$(mktemp -d "$PWD/dist/.contextlens-build.XXXXXX")
trap 'rm -rf "$build_stage"' EXIT
APP="$build_stage/ContextLens.app"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp .build/release/ContextLens "$APP/Contents/MacOS/ContextLens"
cp .build/release/contextlens-cli "$build_stage/contextlens-cli"
cp Brand/AppIcon.icns "$APP/Contents/Resources/AppIcon.icns"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>ContextLens</string>
<key>CFBundleDisplayName</key><string>ContextLens</string>
<key>CFBundleIdentifier</key><string>dev.contextlens.app</string>
<key>CFBundleVersion</key><string>5</string>
<key>CFBundleShortVersionString</key><string>0.3.0</string>
<key>CFBundleIconFile</key><string>AppIcon</string>
<key>CFBundleExecutable</key><string>ContextLens</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>LSMinimumSystemVersion</key><string>14.0</string>
<key>NSHighResolutionCapable</key><true/>
<key>NSScreenCaptureUsageDescription</key><string>Capture only the window you select to prepare local visual context for your coding agent.</string>
</dict></plist>
PLIST
# A stable development identity keeps the designated requirement stable across rebuilds.
# Explicit '-' remains available for CI and machines without a development certificate.
sign_identity="${CONTEXTLENS_SIGN_IDENTITY:-}"
if [[ -z "$sign_identity" ]]; then
    available_identity=$(/usr/bin/security find-identity -v -p codesigning 2>/dev/null | grep -m 1 '"Apple Development:' || true)
    if [[ -n "$available_identity" ]]; then sign_identity=$(awk '{print $2}' <<< "$available_identity"); fi
fi
if [[ -z "$sign_identity" ]]; then sign_identity="-"; fi
if [[ "$sign_identity" == "-" ]]; then
    print 'Signing ad-hoc: Screen Recording approval can become stale after a rebuild.'
else
    print 'Signing with a stable development identity.'
fi
codesign --force --sign "$sign_identity" --timestamp=none "$APP"
codesign --verify --deep --strict "$APP"
# Never overwrite a running executable in place: publish only the verified bundle.
# Retain the retired bundle for recovery and for any still-running old instance.
app_destination="$PWD/dist/ContextLens.app"
previous_bundle=""
if [[ -d "$app_destination" ]]; then
    previous_root=$(mktemp -d "$PWD/dist/.contextlens-previous.XXXXXX")
    previous_bundle="$previous_root/ContextLens.app"
    mv "$app_destination" "$previous_bundle"
fi
if ! mv "$APP" "$app_destination"; then
    if [[ -n "$previous_bundle" ]]; then mv "$previous_bundle" "$app_destination"; fi
    exit 1
fi
mv -f "$build_stage/contextlens-cli" "$PWD/dist/contextlens-cli"
printf 'Built %s\n' "$app_destination"
