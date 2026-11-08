# Security and privacy

ContextLens captures one explicitly selected window and writes local files. It does not upload evidence or run agents. See [privacy and storage](docs/privacy.md) for permissions, redaction limits and retained originals. Review screenshots, titles, labels and instructions before sharing; current rectangle/highlight tools do not create new redactions.

Do not post secrets, personal captures or raw agent transcripts to public issues. For a suspected vulnerability, use the repository's private security reporting channel when enabled; if unavailable, open a minimal issue requesting a private contact without sensitive details. Never include credentials or signing keys.

Contributors must run the [publication audit](docs/publication-audit.md) and review staged content. `scripts/audit-public-files.py --staged` reports targeted patterns without printing matched values; it does not replace manual review. Keep account receipts, private traces and signing material out of Git history.

Distributed binaries must pass Developer ID signing, Apple notarization, stapling and Gatekeeper verification. Development signatures are not public trust. The release scripts never overwrite a published version or bypass operating-system security. No public binary release is available yet; see [release status](docs/distribution-release-report.md).
