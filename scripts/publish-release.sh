#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
version="${1:?Version required}"
asset_dir="${2:?Asset directory required}"
# Recheck main and version immediately before publication. Existing tags/releases
# cause failure, including an incomplete draft from a previous publication attempt.
python3 scripts/release.py preflight "$version"
asset="ContextLens-$version-arm64.zip"
(cd "$asset_dir" && shasum -a 256 -c "$asset.sha256")
python3 scripts/release.py verify-archive "$asset_dir/$asset"
python3 - "$asset_dir/$asset.json" "$(git rev-parse HEAD)" <<'PY'
import json,sys
if json.load(open(sys.argv[1])).get('sourceCommit') != sys.argv[2]:
    raise SystemExit('Archive provenance differs from the current release source')
PY
notes=$(mktemp)
trap 'rm -f "$notes"' EXIT
cat > "$notes" <<EOF
ContextLens $version — Give your AI agent eyes.

Native local-first UI capture, annotation, and coding-agent handoff.

Apple Silicon (arm64), macOS 14 or newer. Built with Developer ID signing,
Hardened Runtime and secure timestamps; Apple notarization, stapling and
Gatekeeper assessment must pass before this workflow publishes.
macOS 14 is the deployment target; hosted runtime checks use macOS 15.

Download $asset and verify its SHA-256 using the accompanying checksum.
The app includes contextlens-cli in Contents/MacOS; --help lists supported commands.
Homebrew installation becomes available after the tap update is validated.
EOF
# A draft ensures assets arrive before visibility. Never use --clobber or --force.
# gh creates the new tag at this exact source commit; no existing tag is moved.
gh release create "v$version" --repo Brendan-Lim/ContextLens --target "$(git rev-parse HEAD)" --draft --title "ContextLens $version" --notes-file "$notes" \
    "$asset_dir/$asset" "$asset_dir/$asset.sha256" "$asset_dir/$asset.json"
gh release edit "v$version" --repo Brendan-Lim/ContextLens --draft=false --latest
