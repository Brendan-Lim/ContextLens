# Research and reproducibility

ContextLens is intended to improve how developers prepare and communicate visual UI feedback. Historical small-fixture studies did not demonstrate a consistent agent token-efficiency advantage. Human preparation savings and general workflow speedups remain unproven. File bytes are not model tokens.

Reusable benchmark implementations, evaluators, synthetic telemetry and owned browser fixtures are public in `Benchmarks/`. Isolated source-mapping experiments are in `Experiments/`; they are not production features. Run offline tests first. Any live agent invocation requires your own explicit authorization and account setup. Historical local authorization does not transfer to a source checkout.

Raw historical model conversations, authentication/authorization receipts, account and billing observations, generated screenshots and private trial workspaces are intentionally excluded. Scripts referring to these local outputs require a newly prepared dataset. The deterministic browser evidence retained under `Benchmarks/reports/browser-evidence/` depicts only repository-owned fixture pages; it supports ten production-selector replays without capturing a personal application.

Run `scripts/verify.sh` for the automated baseline. See [benchmark instructions](../Benchmarks/README.md) for browser controls and study methodology. Model trials are never part of CI.
