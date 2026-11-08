#!/bin/zsh
set -eu
cd "${0:A:h:h}"
mode=development
preview_version=""
output="$PWD/dist"
while (( $# )); do
    case "$1" in
        --distribution) mode=distribution; shift ;;
        --preview) mode=preview; preview_version="${2:?Missing preview version}"; shift 2 ;;
        --output) output="${2:?Missing output directory}"; shift 2 ;;
        *) print -u2 'Usage: scripts/build-app.sh [--distribution | --preview X.Y.Z-preview.N] [--output DIRECTORY]'; exit 2 ;;
    esac
done
python3 scripts/release.py metadata
sign_identity="${CONTEXTLENS_SIGN_IDENTITY:-}"
if [[ "$mode" == preview ]]; then
    [[ "$(uname -m)" == arm64 ]] || { print -u2 'Preview is arm64 only.'; exit 1; }
    # Preview never discovers or uses any Apple identity, including on a developer Mac.
    sign_identity="-"
fi
if [[ "$mode" == distribution ]]; then
    [[ "$(uname -m)" == arm64 ]] || { print -u2 'Distribution is currently arm64 only.'; exit 1; }
    [[ "$sign_identity" == 'Developer ID Application: '* ]] || { print -u2 'Distribution requires CONTEXTLENS_SIGN_IDENTITY="Developer ID Application: …"; no ad-hoc fallback.'; exit 1; }
fi
# File prefix maps cover Swift file literals; strip removes the linker's object paths.
scripts/swift.sh build -c release --arch arm64 \
    -Xswiftc -file-prefix-map -Xswiftc "$PWD=." \
    -Xcc "-fdebug-prefix-map=$PWD=."
bin_dir=$(scripts/swift.sh build -c release --arch arm64 --show-bin-path)
mkdir -p "$output"
output="${output:A}"
build_stage=$(mktemp -d "$output/.contextlens-build.XXXXXX")
trap 'rm -rf "$build_stage"' EXIT
APP="$build_stage/ContextLens.app"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$bin_dir/ContextLens" "$APP/Contents/MacOS/ContextLens"
cp "$bin_dir/contextlens-cli" "$APP/Contents/MacOS/contextlens-cli"
cp Brand/AppIcon.icns "$APP/Contents/Resources/AppIcon.icns"
cp LICENSE "$APP/Contents/Resources/LICENSE"
python3 scripts/release.py plist "$APP/Contents/Info.plist"
if [[ "$mode" == preview ]]; then
    python3 scripts/preview-release.py provenance "$preview_version" "$APP"
fi
strip -S "$APP/Contents/MacOS/ContextLens" "$APP/Contents/MacOS/contextlens-cli"
if [[ "$mode" == development && -z "$sign_identity" ]]; then
    available_identity=$(/usr/bin/security find-identity -v -p codesigning 2>/dev/null | grep -m 1 '"Apple Development:' || true)
    if [[ -n "$available_identity" ]]; then sign_identity=$(awk '{print $2}' <<< "$available_identity"); fi
fi
if [[ -z "$sign_identity" ]]; then sign_identity="-"; fi
if [[ "$mode" == distribution ]]; then
    # Native code needs no JIT, unsigned executable memory, or library exceptions.
    codesign --force --sign "$sign_identity" --options runtime --timestamp "$APP/Contents/MacOS/contextlens-cli"
    codesign --force --sign "$sign_identity" --options runtime --timestamp "$APP"
else
    print 'Building for development; this is not a notarized public release.'
    codesign --force --sign "$sign_identity" --timestamp=none "$APP/Contents/MacOS/contextlens-cli"
    codesign --force --sign "$sign_identity" --timestamp=none "$APP"
fi
verification_mode="$mode"
if [[ "$mode" == preview ]]; then verification_mode=development; fi
python3 scripts/release.py verify "$APP" --mode "$verification_mode"
# Never overwrite a running executable in place. Preserve the old bundle.
app_destination="$output/ContextLens.app"
previous_bundle=""
if [[ -d "$app_destination" ]]; then
    previous_root=$(mktemp -d "$output/.contextlens-previous.XXXXXX")
    previous_bundle="$previous_root/ContextLens.app"
    mv "$app_destination" "$previous_bundle"
fi
if ! mv "$APP" "$app_destination"; then
    if [[ -n "$previous_bundle" ]]; then mv "$previous_bundle" "$app_destination"; fi
    exit 1
fi
# Keep the established development CLI path as well as the portable embedded CLI.
cp "$app_destination/Contents/MacOS/contextlens-cli" "$build_stage/contextlens-cli"
mv -f "$build_stage/contextlens-cli" "$output/contextlens-cli"
printf 'Built %s\n' "$app_destination"
