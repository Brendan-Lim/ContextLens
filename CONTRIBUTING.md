# Contributing

Build with `scripts/build-app.sh`; run `scripts/swift.sh test` and the Python unit suite before submitting changes. Browser fixture checks and independent JSON Schema validation are documented in `Benchmarks/README.md`. Keep production dependencies at zero unless a clear capability justifies adding one.

Separate the Foundation-only models/selector/report from native capture and image rendering. Preserve original-dimension normalized coordinates and stable issue IDs. Every exporter must burn redactions into every derived image and reject escaping paths. Never substitute a display or a different window after target loss. No text-input event capture, network transmission, telemetry or paid CLI execution should be introduced implicitly.

A useful PR explains the behavior changed, the tests performed and any native verification still needed. Include fixtures for changes to selection thresholds, settling, export schemas or usage accounting. Never mix synthetic telemetry with actual benchmark results. Do not copy GPL-covered implementation into this MIT project.

For benchmark PRs, retain unsuccessful attempts and timeouts, separate provider/model/settings groups, and document exact source state, CLI versions, traces, timing definitions and acceptance criteria. File sizes cannot establish token usage. Keep evaluator source out of agent fixture copies.
