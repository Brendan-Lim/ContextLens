# Simplified Capture screen — 0.2.2

The app now has one capture workflow. There is no mode selector. Older mode values remain readable in stored metadata for compatibility; the current human-readable report omits that label.

The main screen shows available windows, **Low / High** sensitivity and **Start Capture**. Click a window to load its preview and enable Start Capture. No window is selected automatically. The redundant Preview button was removed.

- **Low:** requires larger visual differences, preserving fewer minor states.
- **High:** detects smaller interface changes; this is the default for new captures.

Both use the same sampling rate and screenshot quality. A short description beneath the segmented control updates with the selection. Balanced is absent from the UI; its original thresholds are kept internally only for deterministic replay of archived benchmark samples.

**Capture options** is collapsed initially and contains duplicate-state filtering, maximum state count and start delay. During recording, Stop Capture remains in the header and the manual snapshot action appears with its keyboard shortcut.

**More** in the sidebar groups Open Session, Import Screenshot, Storage & Privacy and How it works. Import remains available through the File menu and Timeline. This removes permanent import/session/help controls from Capture without removing their workflows.

Verification: 29 Swift tests passed, including distinct small-change behavior for Low and High. Ten recorded production replays and thirteen package validations passed. The rendered Capture screen was inspected, and the rebuilt app retained Screen Recording approval and returned actual pixels from its generated test window. Recorded scope and observations (local-only evidence `examples/capture-simplification-verification.json`).

The legacy smoke runner's strict resize-both-dimensions and 200 ms closed-probe heuristics did not pass in this run; display height was constrained and the closed probe remained advertised briefly. These are recorded separately and are not counted as successful UI checks.
