#!/bin/bash
set -euo pipefail
# GitHub runner only. Never enable shell tracing in a credential step.
: "${RUNNER_TEMP:?}" "${GITHUB_ENV:?}" "${CERTIFICATE_P12_BASE64:?}" "${CERTIFICATE_PASSWORD:?}" \
  "${ASC_KEY_BASE64:?}" "${ASC_KEY_ID:?}" "${ASC_ISSUER_ID:?}" \
  "${CONTEXTLENS_SIGN_IDENTITY:?}" "${CONTEXTLENS_TEAM_ID:?}"
[[ "$CONTEXTLENS_SIGN_IDENTITY" == 'Developer ID Application: '* ]]
umask 077
credential_dir=$(mktemp -d "$RUNNER_TEMP/contextlens-credentials.XXXXXX")
trap 'rm -rf "$credential_dir"' EXIT
printf '%s' "$CERTIFICATE_P12_BASE64" | base64 --decode > "$credential_dir/certificate.p12"
printf '%s' "$ASC_KEY_BASE64" | base64 --decode > "$credential_dir/AuthKey.p8"
keychain="$RUNNER_TEMP/contextlens-signing.keychain-db"
keychain_password=$(openssl rand -hex 32)
printf '::add-mask::%s\n' "$keychain_password"
security list-keychains -d user > "$RUNNER_TEMP/contextlens-original-keychains.txt"
security create-keychain -p "$keychain_password" "$keychain"
security set-keychain-settings -lut 21600 "$keychain"
security unlock-keychain -p "$keychain_password" "$keychain"
security import "$credential_dir/certificate.p12" -P "$CERTIFICATE_PASSWORD" -k "$keychain" -T /usr/bin/codesign > /dev/null
security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$keychain_password" "$keychain" > /dev/null
# This is a fresh ephemeral runner, so a fixed system keychain plus our isolated
# signing keychain is sufficient. Cleanup restores the original search list.
security list-keychains -d user -s "$keychain" /Library/Keychains/System.keychain
xcrun notarytool store-credentials ContextLensRelease --key "$credential_dir/AuthKey.p8" --key-id "$ASC_KEY_ID" --issuer "$ASC_ISSUER_ID" --keychain "$keychain" > /dev/null
