# Contributing

Build with `scripts/build-app.sh`; run `scripts/swift.sh test` and the Python unit suite before submitting changes. Browser fixture checks and independent JSON Schema validation are documented in `Benchmarks/README.md`. Keep production dependencies at zero unless a clear capability justifies adding one.

Separate the Foundation-only models/selector/report from native capture and image rendering. Preserve original-dimension normalized coordinates and stable issue IDs. Every exporter must burn redactions into every derived image and reject escaping paths. Never substitute a display or a different window after target loss. No text-input event capture, network transmission, telemetry or paid CLI execution should be introduced implicitly.

A useful PR explains the behavior changed, the tests performed and any native verification still needed. Include fixtures for changes to selection thresholds, settling, export schemas or usage accounting. Never mix synthetic telemetry with actual benchmark results. Do not copy GPL-covered implementation into this MIT project.

For benchmark PRs, retain unsuccessful attempts and timeouts, separate provider/model/settings groups, and document exact source state, CLI versions, traces, timing definitions and acceptance criteria. File sizes cannot establish token usage. Keep evaluator source out of agent fixture copies.

Release engineering uses [source build instructions](docs/building.md), [release credentials and gates](docs/releasing.md), and the [Homebrew process](docs/homebrew.md). Run `python3 -m unittest discover -s scripts/tests -v` for publication/archive safety checks, plus `python3 scripts/audit-public-files.py --staged` before publishing. Keep app version/build in `config/version.json`; a normal push must never publish a binary. Do not add broad Hardened Runtime exceptions without an explained, tested need. See [SECURITY.md](SECURITY.md) before sharing captures or logs.

Run the tracked-file audit, explicit full-history audit and independent Gitleaks check described in [publication security](docs/publication-security.md). That guide includes the optional pre-commit hook, exact fixture approvals and incident-response boundary. Never update approval hashes blindly or commit raw scanner output. Use [isolated beta acceptance](docs/beta-acceptance.md) for interactive tests; preserve the owner's current app and permissions.

Maintainer references: [behavioral coverage](docs/testing-coverage.md), [native testing](docs/native-testing.md), [capture lifecycle](docs/native-capture-reliability.md), [diagnostics](docs/diagnostics.md), [dependency attribution](docs/dependency-audit.md), and [research methodology](docs/research.md). [Capture controls](docs/capture-controls.md) documents the current user workflow; keep it consistent with the app and README.
