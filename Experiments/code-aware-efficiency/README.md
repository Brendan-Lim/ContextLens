# Code-aware agent efficiency — prepared study

Four independent React/TypeScript UI defects, eight matched A/B attempts, **zero new model calls**. Read the report (local output `../../docs/code-aware-agent-efficiency.md`), [frozen plan](reports/study/plan.json), and [preflight receipt](reports/preflight.json).


## Files

- `fixture/src/`: 41 component modules plus one `.tsx` bootstrap, shared UI, four routes, policies/hooks and seven CSS modules; four intentional unfixed defects.
- `fixture/tools/`: opt-in TypeScript AST instrumentation, explicit source receipts and esbuild build. No private React internals. The SDK records source execution entries, not function arguments or form values.
- `tasks.json`, `reports/ground-truth.json`: frozen responsibility labels, source hashes and blame ranges. Never given to coding agents.
- `evaluate.mjs`: frozen independent browser acceptance checks. Never given to coding agents.
- `validate-fixture.mjs`: baseline, four isolated repairs, combined repair and plain/instrumented controls. Contains repair answers; never given to agents.
- `lib/mapper.mjs`: browser/source verification, CSS declaration source maps and controlled execution probes. No access to the answer labels.
- `reports/packages/`: eight production-exported evidence packages. Within each pair only `context.md`'s data appendix and `code-context/CL-001.json` differ.
- `run_study.py`, `analyze.py`: gated invocation, retention, telemetry, matched analysis. Synthetic results are rejected by live analysis.
- `reports/runner-self-test/`: preserved failed infrastructure dry run; npm binary links had been dereferenced.
- `reports/runner-self-test-v2/`: corrected six-case local runner verification; no provider usage.

## Repeat no-cost checks

From the repository root, with the installed dependencies and existing benchmark Playwright installation:

```sh
npm --prefix Experiments/code-aware-efficiency/fixture run check
node --test Experiments/code-aware-efficiency/tests/mapper.test.mjs
python3 -m unittest discover -s Experiments/code-aware-efficiency/tests -p 'test_*.py' -v
python3 Experiments/code-aware-efficiency/run_study.py
python3 Experiments/code-aware-efficiency/preflight.py
python3 Experiments/code-aware-efficiency/analyze.py Experiments/code-aware-efficiency/reports/study
```

If dependencies are absent, use `npm ci --prefix Experiments/code-aware-efficiency/fixture` against the pinned lockfile, then rebuild. This downloads public development packages; it does not call a model. The prepared plan pins the actual installed dependency bytes, symlinks, compiled artifacts, runner/helpers, evidence and CLI versions. Cross-machine differences require an explicitly identified new preparation; do not overwrite this frozen plan or its results.

For a fresh local verification, choose **new** output directories:

```sh
CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  node Experiments/code-aware-efficiency/validate-fixture.mjs /tmp/lensboard-controls-repeat
CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  node Experiments/code-aware-efficiency/map-evaluate.mjs /tmp/lensboard-mapping-repeat
CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  node Experiments/code-aware-efficiency/prepare.mjs /tmp/lensboard-packages-repeat
CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  python3 Experiments/code-aware-efficiency/run_study.py --self-test /tmp/lensboard-runner-repeat
```

The owned browser uses a fresh nonpersistent headless Chrome, synthetic local data and a server bound to loopback. External origins are blocked. No personal browser profile or native window is captured. File/fiducial/pixel checks intentionally abstain on stale or unsupported evidence. Do not use this harness for personal application sessions.

## Execution remains unauthorized

Prepared scope: **8 invocations**, four tasks × current/code-aware, one fresh conversation and private source/dependency copy per attempt. Model `gpt-6.1-sol`, high reasoning, default service tier, workspace-write, no web. Execution cap **600 seconds each** (80 minutes maximum agent execution across eight, plus build/evaluation/overhead). Token/allocation consumption cannot be predicted from these offline measurements.


```sh
# Only after fresh explicit authorization for this study:
CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  python3 Experiments/code-aware-efficiency/run_study.py --run \
  --authorization /absolute/path/to/new-code-aware-efficiency-authorization.json

# Save to a new path; pending analysis already exists:
python3 Experiments/code-aware-efficiency/analyze.py \
  Experiments/code-aware-efficiency/reports/study --output /tmp/lensboard-live-analysis.json
```

The guard checks existing ChatGPT authentication and allowance before every invocation, stops at 80% usage, removes API-key environment variables and forces ChatGPT authentication. It never purchases credits, changes billing, resets limits or falls back to an API key. Failures and reserved/interrupted attempts count toward the cap and are never silently retried. Timeout, clock discrepancies and runner failures stop continuation. Interrupted reservations require inspection rather than deletion.

`schedule(2)` prepares the order for a later, separately authorized eight-attempt replication, reversing each pair. No additional repetition is currently prepared as an executable plan or authorized. The previous minimal-code-aware condition is excluded entirely from this primary comparison.

## Interpret results

Use root completed-turn provider usage for input/cached/uncached/output/total; missing stays unavailable. Command discovery, recognized reads/repeats, tests and recorded output sizes are independent activity measures, never token allocations. Source-read recognition is a lower bound, not syscall tracing. Reading an unmodified file or reading twice does not establish unnecessary exploration.

The independent target and shared regression checks decide first-attempt acceptance. Acceptance time runs from invocation to the frozen checks completing, including local typecheck/build/evaluation; failed attempts have no accepted time. Code changes, traces, commands, stderr, check results and source snapshots survive failures/timeouts. Record wrong-hint reliance only when transcript evidence supports it, using the per-attempt adjudication file. Source reads alone do not reveal reliance.

Report task-paired deltas with correctness alongside them. Compare usage only on complete equivalent pairs; compare accepted time only when both succeed with valid clocks. Four authored tasks support a pilot, not population conclusions. The source hints are verified implementation candidates; general causal localization and native-window mapping remain unproven.
