# README screenshot kit

The README shows only genuine screenshots of the current app and the real Finder installer window. This kit lists the five images it needs, how to take them, and how to check them before they are published. Generated, mocked-up or edited UI is never acceptable. Cropping, resizing and lossless optimization are the only changes allowed.

**Status (9 November 2026): none of the five screenshots exists yet.** No disposable interactive Mac was available to the agent, and the owner's personal desktop is out of bounds for automated capture.

## Where to take them

Use a **disposable macOS environment**, not your everyday account. Then the candidate's ad-hoc signature, Screen Recording approval and `/Applications` copy cannot interfere with your installed ContextLens. Choose one of these:

- **Recommended:** a macOS virtual machine on this Mac (for example UTM or another Apple Virtualization front end). ScreenCaptureKit works inside the guest. The same VM can run the [release acceptance](../release-acceptance/README.md) checklist, so one session covers both jobs.
- A spare Mac you can erase afterwards.

A second user account on your own Mac is **not** enough: `/Applications` is shared, so dragging the candidate there would replace your installed copy.

## What to install

Use the independently verified hosted candidate from [prepare-only run 42557369631](https://github.com/Brendan-Lim/ContextLens/actions/runs/42557369631), source `5e786bc5dc144f0debe7f05f1957489e5600c256`. The older run `42504640955` is obsolete and must not be promoted or used for final acceptance.

```sh
gh run download 42557369631 --repo Brendan-Lim/ContextLens --name official-candidate-0.3.1 --dir candidate-42557369631
cd candidate-42557369631
shasum -a 256 -c SHA256SUMS
```

| Candidate identity | Exact value |
|---|---|
| Version / build | **0.3.1 / 6** |
| ZIP SHA-256 | `f4ac0a2cc3dc5fd6f120a21e3f7152f86351b7f8bf93e3908f57bc5a9ad3425e` |
| DMG SHA-256 | `52872a5e0221fac2960fb8d5c349743201bbb5800a914eb77b1b48416473b37d` |
| Bundle inventory SHA-256 | `9e689eba51491066164b315dd2ac94d525154d4d7c8dadd1ea5124ed5775e1db` |
| Artifact expiration | **9 December 2026, 11:40 SGT** (`2026-12-09T03:40:00Z`) |

For genuine first-launch acceptance, download the Actions artifact through a browser while signed in to GitHub **inside the disposable macOS VM or spare Mac**. The CLI command verifies bytes but does not establish quarantine. Retain the downloaded container and confirm its quarantine metadata is present; never remove or fabricate quarantine or disable Gatekeeper. Confirm **ContextLens → About** shows **0.3.1 (6)**. Record the actual macOS version and policy observations. The deployment metadata is macOS 14.0; runtime behavior on macOS 14 remains unverified.

Both containers were independently reverified on macOS 26.6.2 using the trusted scripts: hashes, strict ad-hoc signatures, embedded CLI, source/input identity, ZIP safety, actual DMG mount/filesystem/layout metadata, clean detach, temporary installation copy and complete bundle equality passed. Actual Finder appearance and native capture/permission behavior remain pending. See [the final candidate report](../final-0.3.1-candidate.md).

## Set the stage

- **Appearance:** Light mode for the main set. Dark-mode copies of A–D are welcome but optional.
- **Desktop:** a plain wallpaper, no desktop icons, Do Not Disturb on, and no other apps visible.
- **Demo app:** open [`demo-site/index.html`](demo-site/index.html) in Safari or Chrome. Use a private window with the bookmarks bar hidden, sized to about **1100 × 720**. The page is fictional (“Tidewater”), makes no network requests and contains three deliberate bugs to mark: the dialog's buttons stop 14 px short of the email field's right edge, the second avatar sits 5 px low, and the hint text has very low contrast.
- **ContextLens window:** about **1280 × 800**.
- **Capture method:** press <kbd>⌘</kbd><kbd>⇧</kbd><kbd>4</kbd>, then <kbd>Space</kbd>, then click the window. This captures one window with its shadow and no desktop. Do not use a full-screen capture.

## The five shots

Record one session first; it supplies B–D. In ContextLens, press <kbd>⌘</kbd><kbd>N</kbd>, pick the browser window under **Which window?**, keep **High** sensitivity, and click **Start Capture**. In the browser, wait two seconds and then click **Share workspace**. Wait, click the **Link** tab, wait, click **Invite**, wait, and then click **Cancel**. Click **Stop Capture**.

| File | Shot | What must be visible |
|---|---|---|
| `A-capture.png` | **Capture** | The capture panel with the Tidewater browser window selected under **Which window?** and its preview loaded, just before **Start Capture**. If you can, also take `A2-recording.png`: the recording pill during capture. |
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
2. Resize to at most 2400 px wide if needed, using `sips --resampleWidth 2400`.
3. Open and review every image, record its SHA-256 and purpose in `config/publication-policy.json`, and run `python3 scripts/audit-public-files.py --staged`.
4. Add the images to the README: Capture under the hero, Review, Mark Up and Hand Off in the workflow section, and the Finder window under **Install**. Each gets a plain caption naming the app version.

Owner-supplied images stay out of the repository until that review passes.


## Ordered native acceptance session

Keep original downloaded ZIP/DMG bytes and their hashes. Record observations and evidence for the exact candidate, using the case names in the [acceptance template](../release-acceptance/template.json). Automated checks do not supply passing observations.

1. In a disposable macOS VM or spare Mac, download the Actions artifact through the browser. Verify `SHA256SUMS`, version/build and provenance. Keep quarantine; observe the genuine first-launch warning and normal user-controlled **Open Anyway** authorization. Do not disable Gatekeeper or remove quarantine.
2. Open the real DMG in Finder in Light and Dark modes. Inspect Retina background, labels, icon positions and the Applications shortcut; take E-light/E-dark screenshots. Drag to Applications inside this disposable environment, eject, and launch the installed copy. Confirm **0.3.1 (6)**.
3. With fresh guest Screen Recording permissions, deny access and observe recovery. Grant access through System Settings, relaunch, and verify window selection. Never reset the owner's permissions.
4. Record only the fictional Tidewater browser window, first at Low and then High sensitivity. Exercise dialog/tab changes and continuous scrolling. Verify Review has the expected distinct states, selected-window content only, and a settled Scrolled state.
5. Reorder, rename and deselect states in Review. In Mark Up, add the Box/Highlight instructions above, a redaction and an unlabelled reference; exercise undo/redo and verify stable issue IDs. Capture B/C only from this real app.
6. Save Hand Off and inspect `context.md`, overview, crops, timeline and redacted pixels. Confirm source files stay private and unchanged. Take D after a real successful export. Copy the prompt and verify its destination.
7. Exercise stale-preview refusal using a disposable copy of the synthetic session: after Hand Off preparation, replace a source PNG with a different same-size image. Save must fail without a final package. Toggle export filters and restore the desired selection to refresh preparation, then retry and verify the new pixels. Do not use a personal session for this fault injection.
8. Save, quit and reopen the session. Verify state order, marks, redactions and issue IDs. Test selected-window closure while another window remains present, then target-browser exit: capture must stop without substitution.
9. Exercise ContextLens exit during capture, pending-frame persistence, rapid start/stop, and capture failed-save/retry using the disposable session storage only, following [beta acceptance](../beta-acceptance.md). Restore write access and verify pending frames save on retry. Also test Hand Off refusal/retry with an unwritable disposable output folder; that export test does not substitute for capture-save recovery. Preserve recoverable data; do not fault-inject against the owner's disk or files.
10. Revoke Screen Recording permission in the guest, observe failure/recovery, grant and relaunch again. Check reopening the saved session and repeating Hand Off still work.
11. Review genuine A–E screenshots at full size, remove metadata without changing UI pixels, and retain originals privately. Mark each acceptance case pass/fail/pending with observations; any unresolved failure blocks release.
12. Only after a maintainer reviews all evidence, fill the exact candidate acceptance record. This task creates no passing record, stable tag, release or Homebrew cask.
