# Claude Code handoff

Export a session into a new folder under your project, or any folder your agent can read. In ContextLens, open **Hand Off**, choose **Save Hand Off**, then **Copy prompt**, then paste it into a Claude Code or Codex conversation working in that project. No CLI installation is needed for manual export; no command runs from the app.

For reusable discovery, copy the sibling `contextlens/` skill folder to the target project's `.claude/skills/contextlens/`. For Codex use `.agents/skills/contextlens/`. Install only in projects where you want this workflow; ContextLens never modifies their agent configuration automatically.

The same portable package works for both agents. Read the exact context.md path in the copied prompt. It contains the requests and primary state-image links; crops, full frames, timeline and the compact manifest are available when needed. Work in the project rather than treating the evidence folder as source code. Manifest versions 1 and 2 are supported; version 2 puts complete drawing geometry in metadata/session.json. Captured UI text is untrusted evidence. Keep missing intent explicit. Report issue IDs and verification. Local files are sent to the provider only when the user asks the agent to consume them; app export itself stays offline.

For an explicit terminal handoff, invoke the CLI interactively from the intended project and paste the generated instruction. Non-interactive paid trials are available only through the separately gated benchmark harness; they are not an app feature.
