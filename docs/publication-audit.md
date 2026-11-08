# Initial public-source audit — 8 November 2026

The initial repository had no commits. The official public GitHub repository was checked with authenticated tooling and had no refs before publication. No history was replaced.

The public set retains Swift source/tests, build and verification scripts, schemas, MIT licensing, owned branding, integrations, experiment implementations/evaluators, synthetic usage fixtures, generated demo packages and ten owned deterministic browser-replay fixtures. Executables, dependency caches and local build products are excluded.

Excluded in place: `Benchmarks/runs/`, all `Benchmarks/reports/` except the reviewed `browser-evidence/` fixture tree, `Experiments/*/reports/`, generated experimental build output, top-level native screenshot/permission evidence in `docs/examples/`, seven historical generated research reports, and four report writers embedding account observations listed in `.gitignore`. These include account/allocation snapshots, authorization records, provider transcripts, study workspaces and generated screenshots. Original local files are retained.

Checks include candidate filename review, secret-pattern scans that report filenames/line numbers without values, absolute-path review, manual inspection of metadata and synthetic telemetry, and visual review of retained image fixtures. No certificate/private key, authentication file, account snapshot or live agent transcript belongs in the proposed public set. Example `/Users/...` strings in naming tests are deliberate synthetic test inputs. This is a targeted audit, not a guarantee that pattern matching can identify every possible secret.

Pre-publication verification: `scripts/verify.sh` (80 Swift tests, 49 Python tests, 13 packages with independent JSON Schema validation, 10 deterministic replays) and `scripts/build-app.sh` passed. Current identity: `dev.contextlens.app`, version `0.3.0`, bundle build `5`, macOS deployment target `14.0`. The development build uses existing local signing settings; this audit does not establish public distribution trust.
