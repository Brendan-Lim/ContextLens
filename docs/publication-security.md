# Publication security checks

Run these from a checkout before committing or publishing. The checks inspect Git's **index**, not a working copy that could hide a staged secret:

```sh
python3 scripts/audit-public-files.py --staged
python3 scripts/audit-public-files.py
git fetch origin --tags
python3 scripts/audit-public-files.py --history
python3 scripts/run-gitleaks.py
python3 scripts/check-public-links.py
python3 -m unittest discover -s scripts/tests -v
```

Fetch every public branch/tag into a full clone for a complete historical audit; `--history` scans all locally reachable refs, including release tags, commit messages and annotated tag messages. It rejects shallow clones. Deleted server refs, other people's clones, forks, Actions logs and deleted release assets are outside this command's visibility. A clean scan is evidence within that scope, not proof that a secret never existed elsewhere.

To enable the included local pre-commit hook, first inspect `git config --get core.hooksPath` and any existing `.git/hooks/pre-commit`. If you have no hook to preserve, run `git config --local core.hooksPath .githooks`. Otherwise add `python3 scripts/audit-public-files.py --staged` to your existing hook. No global Git setting is needed. CI independently checks the index and history even when a contributor has no hook installed.

## What fails publication

The guard detects common provider tokens, private keys, credential assignments, embedded Authorization headers, credential-bearing URLs, personal home/cache paths, sensitive filenames, raw traces, generated/build outputs, disguised compiled/archive files, unsafe symlinks and submodules needing review. It reads the full staged blob even if the worktree differs or the file was deleted there. It checks every historical path, including when the same bytes were committed under a different filename.

Findings contain only a file, object ID, rule, location and optional line number. They never include matching values or source snippets. Token-shaped filenames are redacted too. Oversized or unreadable inputs fail for review rather than silently counting as clean. Do not paste a raw scanner report, suspected credential or private screenshot into an issue to explain a failure.

`config/publication-policy.json` records exact SHA-256 approvals and purposes for reviewed synthetic fixtures, example packages, parser telemetry and owned branding. New or changed media/example files require review before their hashes are updated. Inspect pixels, all animation frames, metadata and JSON contents first. Do not regenerate approvals just to make CI green. Approved bytes still undergo credential and metadata checks. Synthetic path exceptions are restricted to an exact test-file digest and never exempt credential checks. If a reviewed fixture changes, retain its previously reviewed digest under `historicalSHA256` so its safe history remains auditable.

PNG validation rejects text/timestamp/unreviewed chunks and malformed CRCs. The currently approved EXIF contains only dimensions/color-space information, confirmed through ImageIO. Pixel text and other image/container metadata still require human review; Linux CI does not claim OCR or visual privacy analysis. Public example JSON is parsed and rejects private identity/account fields and application/window metadata outside the synthetic fixture contract. Existing package/schema tests validate export structure separately.

The independent Gitleaks wrapper downloads official **8.30.1** into temporary storage, verifies a pinned archive SHA-256, uses stock rules, forces complete redaction, ignores inline skip comments and repository ignore/config overrides, and prints only sanitized locations. No repository contents are sent to a service. Its temporary raw report is never an Actions artifact or comment. The MIT CLI requires no paid service or action license. Supported scanner hosts are Apple Silicon macOS and Linux x86_64. Review the upstream release and checksums before updating the pinned tool.

The separate **Publication Security** workflow runs on pushes, pull requests and manual dispatch with read-only repository permissions. Normal macOS CI also runs the tracked-file and public-link checks. Keep production dependencies at zero. The same scripts and workflow are used by the Homebrew tap, which has no media approvals to maintain.

## Documentation and incident handling

The link check resolves inline/reference links, headings, images and HTML link attributes against tracked files. A private ignored report on disk cannot make a public link pass. External URL availability is a separate network check; transient 403/429/504 responses do not establish a broken target. Describe local-only research evidence in prose and link to the public [research summary](research.md), rather than publishing the excluded report.

If a finding is a genuine exposure, stop publication, identify the affected current/history/release locations without showing the value, rotate or revoke affected credentials, and prepare a remediation plan. Do not automatically delete releases, force-push or rewrite history. Rewriting requires explicit approval and coordinated release-provenance recovery. Preserve private local originals outside Git.

See [the beta-readiness audit](public-beta-readiness.md), [security policy](../SECURITY.md) and [initial publication scope](publication-audit.md). References: [Gitleaks source and releases](https://github.com/gitleaks/gitleaks), [GitHub secret scanning](https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning).
