#!/bin/zsh
set -eu
cd "${0:A:h:h}"
xcodebuild -version
swift --version
[[ "$(uname -m)" == arm64 ]] || { print -u2 'This CI job validates arm64.'; exit 1; }
CONTEXTLENS_SIGN_IDENTITY=- scripts/build-app.sh
scripts/verify.sh
python3 -m unittest discover -s scripts/tests -v
python3 scripts/verify-release-build.py
python3 distribution/homebrew/scripts/validate.py
python3 scripts/release.py package dist/ContextLens.app "$(mktemp -d)" --development
npm --prefix Benchmarks ci --ignore-scripts
(cd Benchmarks && npx playwright install chromium)
node Benchmarks/runners/verify-fixtures.mjs
