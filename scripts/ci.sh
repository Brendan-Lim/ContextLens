#!/bin/zsh
set -eu
cd "${0:A:h:h}"
xcodebuild -version
swift --version
python3 scripts/audit-public-files.py
python3 scripts/check-public-links.py
[[ "$(uname -m)" == arm64 ]] || { print -u2 'This CI job validates arm64.'; exit 1; }
CONTEXTLENS_SIGN_IDENTITY=- scripts/build-app.sh
scripts/verify.sh
python3 -m unittest discover -s scripts/tests -v
python3 scripts/verify-release-build.py
python3 distribution/homebrew/scripts/validate.py
python3 scripts/release.py package dist/ContextLens.app "$(mktemp -d)" --development
python3 -m venv .build/dmg-ci-python
.build/dmg-ci-python/bin/python -m pip install --require-hashes -r distribution/dmg/requirements.txt
.build/dmg-ci-python/bin/python distribution/dmg/build-dmg.py dist/ContextLens.app "$(mktemp -d)/ContextLens-ci.dmg"
npm --prefix Benchmarks ci --ignore-scripts
(cd Benchmarks && npx playwright install chromium)
node Benchmarks/runners/verify-fixtures.mjs
