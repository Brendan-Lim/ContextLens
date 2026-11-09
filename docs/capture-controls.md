# Capture controls

Press **⌘N** to open Capture. Under **Which window?**, explicitly choose a window; its preview loads before **Start Capture** is enabled. ContextLens never selects a source automatically. New sessions use one capture workflow; legacy mode values remain readable in stored metadata.

- **High** sensitivity is the default and detects smaller changes.
- **Low** requires larger differences and preserves fewer minor states.

Both use the same sampling rate and image quality. Very small or low-contrast changes can be missed; use **Snapshot** or **⌘⇧S** for a specific moment. Balanced is retained internally only for deterministic legacy replays.

Expand **Capture options** for duplicate-state filtering, maximum state count and start delay. During recording, the compact pill offers **Snapshot** and **Stop**. Stopping opens Review with the captured states. Target loss stops capture instead of switching to another window or display.

Open saved sessions or import screenshots through the File menu and the main window's session controls. Review states, then use **Mark Up** and **Hand Off**. See [getting started](../README.md#get-started), [export rules](export-format.md) and [permissions](permissions.md).
