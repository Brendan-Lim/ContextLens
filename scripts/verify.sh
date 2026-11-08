#!/bin/zsh
set -eu
cd "${0:A:h:h}"
scripts/swift.sh test
python3 scripts/check-coverage-map.py
python3 -m unittest discover -s Benchmarks/tests -v
export PYTHONPATH="$PWD/.build/benchmark-python${PYTHONPATH:+:$PYTHONPATH}"
python3 scripts/verify-packages.py
python3 scripts/verify_replays.py
