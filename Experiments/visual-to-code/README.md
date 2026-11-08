# Visual-to-Code Mapping — optional research adapter

This is a working local Chromium experiment, separate from the macOS app. It uses the existing Playwright 1.62.1 installation, Node built-ins and the production ContextLens CLI. It makes no model calls to map an annotation. The completed experiment is in the engineering report (local output `../../docs/visual-to-code-experiment.md`); historical activity findings are in the trace report (local output `../../docs/token-exploration-analysis.md`).

## Scope

The adapter launches a fresh headless browser and a server bound to `127.0.0.1` for an explicitly selected project. It cannot attach to a personal browser profile or a native window. Requests outside that server's origin are blocked. Do not point it at private or uncontrolled application sessions.

The native capture pipeline, annotation editor, session/manifest versions and default exporter are unchanged. The experiment copies an export and optionally adds `code-context/CL-001.json`. If the binding, source verification, freshness or redaction checks fail, the original visual brief is retained. `code-context.schema.json` versions the independent extension.

## Modules

| Directory | Responsibility |
|---|---|
| `src/browser-adapter/` | Owned browser, asset receipts, snapshot identity/freshness and mapping orchestration |
| `src/geometry/` | PNG pixel calibration and normalized ↔ screenshot ↔ viewport transforms |
| `src/element-ranking/` | Multi-point visibility, geometric ranking and semantic ancestor promotion |
| `src/style-inspection/` | Bounded deterministic property sets |
| `src/source-mapping/` | Selected-project containment, served-byte checks, CSS/markup/dev-hook provenance |
| `src/export/` | Exact pixel binding and optional concise sidecars |
| `fixtures/` | Existing-fixture case labels plus ES-module component fixture |
| `tests/` | Geometry, paths, privacy, stale state, export and authorization regressions |

The component fixture uses parent/child ES-module component functions and externally loaded CSS. Its explicit `contextLensDevelopmentSources` contract registers an element with its module URL and exported function. That hook is ignored unless the caller opts into its selected local registry file. The function declaration line is verified against the served project asset. This does not recover arbitrary React/Vue/Svelte components, JSX lines, event handlers or unavailable production source maps.

## Use the adapter

```js
import {OwnedBrowser} from './src/browser-adapter/owned-browser.mjs';
import {mapAnnotation} from './src/browser-adapter/map.mjs';

const owner = await OwnedBrowser.create({projectRoot: '/absolute/selected/dev/project'});
try {
  const snapshot = await owner.capture({id: 'frame-001', path: '/tmp/owned-viewport.png'});
  const mapping = await mapAnnotation(owner, snapshot, {
    issueID: 'CL-001', frameID: 'frame-001',
    region: {x: 0.1, y: 0.2, width: 0.2, height: 0.08},
    category: 'spacing'
  });
  // Treat mapping.status/sourceStatus/confidence as evidence, not a confirmed cause.
} finally {
  await owner.close();
}
```

Categories are `spacing`, `alignment`, `visibility`, `interaction`, `unknown`. Names and general DOM text are omitted by default; input values, cookies and request bodies are never read. Any redaction in a bound frame disables the code-aware extension for that frame. File paths are canonicalized inside the selected project and asset hashes must match the browser-observed response.

Four temporary colour fiducials verify an axis-aligned transform before capturing the clean viewport. The transform accounts for actual device scaling/page scale; DPR is not applied twice. Main-document scroll stays in viewport coordinates for hit testing. Untransformed same-origin frame offsets are supported. Native title bars, arbitrary window movement, display scaling and Chrome UI zoom remain uncalibrated; CSS layout zoom and Chromium page-scale emulation were tested separately. Re-capture after resize or scroll; do not reuse an old native screenshot or guess its transform.

## Reproduce without inference

Run from the repository root. Existing output folders are preserved; use new directories for another measured run.

```sh
# Existing-trace profile; the JSON retains command/event evidence and turn usage:
python3 Benchmarks/runners/profile_agent_exploration.py \
  --output Experiments/visual-to-code/reports/trace-profile-repeat

node --test Experiments/visual-to-code/tests/unit.test.mjs \
  Experiments/visual-to-code/tests/export.test.mjs
CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  node --test Experiments/visual-to-code/tests/browser.test.mjs
python3 -m unittest discover -s Experiments/visual-to-code/tests -p 'test_*.py' -v

# Frozen labels; 10 development cases and 22 held-out cases:
CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  node Experiments/visual-to-code/evaluate.mjs --split development \
  --output Experiments/visual-to-code/reports/development-repeat
CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  node Experiments/visual-to-code/evaluate.mjs --split held-out \
  --output Experiments/visual-to-code/reports/held-out-repeat

# Four tasks × current / code-aware / minimal-code-aware; actual bytes, not tokens:
CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  node Experiments/visual-to-code/prepare-handoffs.mjs \
  Experiments/visual-to-code/reports/offline-repeat

scripts/verify.sh
```

`reports/ground-truth-freeze.json` was written before the mapper. `reports/algorithm-freeze.json` identifies the core used before the first held-out evaluation. Do not tune the ranker against the held-out answers; use new labelled cases for another experiment. The report preserves the wrong CSS-rule case instead of redefining ground truth.

## Live pilot: prepared, not authorized or executed

`live_pilot.py` prepares four task triplets (12 attempts, seed 3001). Current versus code-aware is the primary controlled comparison; minimal code-aware is exploratory. Source, instructions, initial image hashes, model/high effort and acceptance checks match. Each attempt is a fresh workspace/conversation, with local tools, no web, timeout retention and UTC/monotonic clock reconciliation. It records provider usage and exploration activity separately. Partial and failed keys are never silently repeated.

```sh
# No model turn:
python3 Experiments/visual-to-code/live_pilot.py

# Synthetic local Python execution + independent browser checks, never Codex:
CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  python3 Experiments/visual-to-code/live_pilot.py --self-test \
  --self-test-output Experiments/visual-to-code/reports/synthetic-repeat

# ONLY after new explicit authorization for this experiment is recorded:
CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  python3 Experiments/visual-to-code/live_pilot.py --run \
  --authorization /absolute/path/to/new-visual-to-code-authorization.json
```


The synthetic fixtures have labelled usage solely to test the runner/parser. They are stored separately and must never be loaded as live agent performance. Live token/time/correctness effects, human preparation savings and production framework coverage remain unproven.
