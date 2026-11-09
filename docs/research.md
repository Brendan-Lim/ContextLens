# Research and reproducibility

ContextLens is intended to improve how developers prepare and communicate visual UI feedback. Historical small-fixture studies did not demonstrate a consistent agent token-efficiency advantage. Human preparation savings and general workflow speedups remain unproven. File bytes are not model tokens.

Reusable benchmark implementations, evaluators, synthetic telemetry and owned browser fixtures are public in `Benchmarks/`. Isolated source-mapping experiments are in `Experiments/`; they are not production features. Run offline tests first. Any live agent invocation requires your own explicit authorization and account setup. Historical local authorization does not transfer to a source checkout.

Raw historical model conversations, authentication/authorization receipts, account and billing observations, generated screenshots and private trial workspaces are intentionally excluded. Scripts referring to these local outputs require a newly prepared dataset. The deterministic browser evidence retained under `Benchmarks/reports/browser-evidence/` depicts only repository-owned fixture pages; it supports ten production-selector replays without capturing a personal application.

Run `scripts/verify.sh` for the automated baseline. See [benchmark instructions](../Benchmarks/README.md) for browser controls and study methodology. Model trials are never part of CI.

## Visual-to-Code and historical evidence

The [Visual-to-Code adapter](../Experiments/visual-to-code/README.md) can inspect repository-owned pages in a fresh headless Chromium instance and bind visual regions to verified local browser/source evidence. It is experimental, opt-in and absent from the native app's production capture/export flow. Its path, geometry, freshness, redaction and origin checks have offline fixtures; success there does not prove general native-window mapping, causal bug localization or model-efficiency gains.

Earlier trace profiles, measured payload variants and small agent pilots used local execution records that are intentionally excluded from Git. Detailed engineering reports are local-only evidence, not missing public artifacts to restore. Public source retains reusable evaluators and synthetic controls; reproducing an analysis needs a fresh dataset and any live model work needs fresh authorization. No account, billing, authorization or conversation data should be added to make an old command run.

The ten browser fixture packages and legacy geometric examples are useful deterministic test inputs, not personal recordings or measurements of human reporting time. Their visual/metadata audit and exact approvals are documented in [the publication policy](../config/publication-policy.json) and [publication security](publication-security.md). They do not demonstrate token, execution-time or human-preparation savings.
