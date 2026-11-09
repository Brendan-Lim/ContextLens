# README screenshot kit

The README shows only genuine screenshots of the current app and the real Finder installer window. This kit describes the seven approved images, how to take replacements, and how to check them before publication. Generated, mocked-up or edited UI is never acceptable. For future replacements, capture native 2× pixels and remove metadata without changing them; review each exact file with the owner. Preserve the integrated seven files byte for byte, including their original aspect ratios.

**Status (9 November 2026): all seven genuine native Retina 2× screenshots are owner-approved and integrated.** Exact sanitized files are in [docs/media/screens](../media/screens/), with reviewed hashes in [the publication policy](../../config/publication-policy.json). They were captured in [run 42588372941](https://github.com/Brendan-Lim/ContextLens/actions/runs/42588372941) and integrated through [PR #3](https://github.com/Brendan-Lim/ContextLens/pull/3). Originals remain private. The separate [official candidate baseline](../official-release-preparation.md) passed 14 native engineering cases; five human security cases remain pending. Product screenshots do not attest to first-launch security.

## Where to take them

Use a **disposable macOS environment**, preserving the owner's app and permissions. The existing diagnostic workflow demonstrates a practical GitHub-hosted Mac route with genuine ScreenCaptureKit recording, native UI input and encrypted evidence delivery. Independently review its workflow/helpers before reuse; do not merge the diagnostic branch into production. A disposable interactive VM or spare Mac is still needed when actual human security authorization cannot be observed on the hosted runner.

A second user account on the owner's Mac is **not** enough: `/Applications` is shared, so dragging the candidate there could replace the owner's installed copy.

## What to install

Use an identified development build for replacement media. For release acceptance use a fresh, independently verified official candidate from integrated main; see [release preparation](../official-release-preparation.md). Preserve candidate ZIP/DMG bytes, signatures, bundle inventory and provenance. Repeat applicable engineering acceptance after a protected input changes. Development screenshots are publication media, not acceptance of different official binaries.

For genuine first-launch acceptance, download that fresh Actions artifact through a browser inside the disposable Mac. Keep the original downloaded inode and quarantine metadata; never remove or fabricate quarantine or disable Gatekeeper. Observe actual user-controlled Open Anyway and Screen Recording authorization. A completed automation job, direct executable launch or existing runner permission does not prove these cases. No passing maintainer attestation is supplied by the diagnostic harness.

## Set the stage

- **Appearance:** Light mode for the main set. Dark-mode copies of A–D are welcome but optional.
- **Desktop:** a plain wallpaper, no desktop icons, Do Not Disturb on, and no other apps visible.
- **Demo app:** open [`demo-site/index.html`](demo-site/index.html) in Safari or Chrome. Use a private window with the bookmarks bar hidden, sized to about **1100 × 720**. The page is fictional (“Tidewater”), makes no network requests and contains three deliberate bugs to mark: the dialog's buttons stop 14 px short of the email field's right edge, the second avatar sits 5 px low, and the hint text has very low contrast.
- **ContextLens window:** about **1280 × 800**.
- **Capture method:** press <kbd>⌘</kbd><kbd>⇧</kbd><kbd>4</kbd>, then <kbd>Space</kbd>, then click the window. This captures one window with its shadow and no desktop. Do not use a full-screen capture.

## The screenshot set

Record one session first; it supplies B–D. In ContextLens, press <kbd>⌘</kbd><kbd>N</kbd>, pick the browser window under **Which window?**, keep **High** sensitivity, and click **Start Capture**. In the browser, wait two seconds and then click **Share workspace**. Wait, click the **Link** tab, wait, click **Invite**, wait, and then click **Cancel**. Click **Stop Capture**.

| File | Shot | What must be visible |
|---|---|---|
| `A-capture.png` | **Capture** | The capture panel with the Tidewater browser window selected under **Which window?** and its preview loaded, just before **Start Capture**. Also take `A2-recording.png`: the recording pill during a genuine capture, with the complete Stop label visible. |
| `B-review.png` | **Review** | The Review tab with the 3–5 captured states, one unticked and the dialog state selected. |
| `C-markup.png` | **Mark Up** | The dialog state with two marks. **Box** the Cancel and Send invite buttons with the note *“Align the action buttons with the right edge of the email field.”* **Highlight** Sam Okafor's avatar with the note *“Center this avatar vertically in its row, like the one above.”* Take the shot at 100% zoom with both notes visible. |
| `D-handoff.png` | **Hand Off** | Set the task to *“Polish the Share workspace dialog.”* Click **Save Hand Off** into a folder whose path holds no personal name, for example `/tmp/share-dialog-feedback` (press <kbd>⌘</kbd><kbd>⇧</kbd><kbd>G</kbd> in the folder picker). Take the shot after saving, with the `context.md` preview and **Copy prompt** visible. |
| `E-dmg-light.png` and `E-dmg-dark.png` | **Installer** | Double-click the candidate DMG and capture the Finder window it opens, once in Light mode and once in Dark mode. Leave the layout as Finder shows it, with the ContextLens app and the Applications shortcut both visible. |

The README uses the Light set. The dark DMG image proves label legibility for acceptance (`dmg-finder-dark`).

## Before handing them over

Check each image at full size for:

- [ ] No real names, email addresses, account avatars, notifications or menu-bar items.
- [ ] No personal paths. Hand Off and window titles must not show `/Users/<name>`.
- [ ] No other app windows, browser tabs, bookmarks or extensions.
- [ ] The version is 0.3.1, and the UI is untouched apart from cropping or resizing.

Then put the originals in one folder, for example `~/Desktop/contextlens-shots/`, and tell the agent where they are. The agent will:

1. Remove screenshot metadata (XMP, Apple and EXIF chunks) without changing a pixel: `python3 scripts/strip-png-metadata.py IN.png docs/media/screens/A-capture.png`.
2. Preserve native pixel dimensions and aspect ratio. Set README CSS widths to at most half the source width for Retina sharpness; never upscale a 1× capture to claim genuine 2×.
3. Open and review every image, record its SHA-256 and purpose in `config/publication-policy.json`, and run `python3 scripts/audit-public-files.py --staged`.
4. Add the images to the README: Capture under the hero, Review, Mark Up and Hand Off in the workflow section, and the Finder window under **Install**. Each gets a plain caption naming the app version.

Owner-supplied images stay out of the repository until that review passes.


## Ordered native acceptance session

Keep original downloaded ZIP/DMG bytes and their hashes. Record observations and evidence for the exact candidate, using the case names in the [acceptance template](../release-acceptance/template.json). Automated checks do not supply passing observations.

1. In a disposable macOS VM or spare Mac, download the Actions artifact through the browser. Verify `SHA256SUMS`, version/build and provenance. Keep quarantine; observe the genuine first-launch warning and normal user-controlled **Open Anyway** authorization. Do not disable Gatekeeper or remove quarantine.
2. Open the real DMG in Finder in Light and Dark modes. Inspect Retina background, labels, icon positions and the Applications shortcut; take E-light/E-dark screenshots. Drag to Applications inside this disposable environment, eject, and launch the installed copy. Confirm **0.3.1 (6)**.
3. With fresh guest Screen Recording permissions, deny access and observe recovery. Grant access through System Settings, relaunch, and verify window selection. Never reset the owner's permissions.
4. Record only the fictional Tidewater browser window, first at Low and then High sensitivity. Exercise dialog/tab changes and continuous scrolling. Verify Review has the expected distinct states, selected-window content only, and a settled Scrolled state.
5. Reorder, rename and deselect states in Review. In Mark Up, add the Box/Highlight instructions above and an unlabelled reference; use a synthetic legacy session for redaction coverage because the toolbar does not create new redactions; exercise undo/redo and verify stable issue IDs. Capture B/C only from this real app.
6. Save Hand Off and inspect `context.md`, overview, crops, timeline and redacted pixels. Confirm source files stay private and unchanged. Take D after a real successful export. Copy the prompt and verify its destination.
7. Exercise stale-preview refusal using a disposable copy of the synthetic session: after Hand Off preparation, replace a source PNG with a different same-size image. Save must fail without a final package. Toggle export filters and restore the desired selection to refresh preparation, then retry and verify the new pixels. Do not use a personal session for this fault injection.
8. Save, quit and reopen the session. Verify state order, marks, redactions and issue IDs. Test selected-window closure while another window remains present, then target-browser exit: capture must stop without substitution.
9. Exercise ContextLens exit during capture, pending-frame persistence, rapid start/stop, and capture failed-save/retry using the disposable session storage only, following [beta acceptance](../beta-acceptance.md). Restore write access and verify pending frames save on retry. Also test Hand Off refusal/retry with an unwritable disposable output folder; that export test does not substitute for capture-save recovery. Preserve recoverable data; do not fault-inject against the owner's disk or files.
10. Revoke Screen Recording permission in the guest, observe failure/recovery, grant and relaunch again. Check reopening the saved session and repeating Hand Off still work.
11. Review genuine A–E screenshots at full size, remove metadata without changing UI pixels, and retain originals privately. Mark each acceptance case pass/fail/pending with observations; any unresolved failure blocks release.
12. Only after a maintainer reviews all evidence, fill the exact candidate acceptance record. This task creates no passing record, stable tag, release or Homebrew cask.
