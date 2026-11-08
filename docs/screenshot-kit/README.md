# README screenshot kit

The README shows only genuine screenshots of the current app and the real Finder installer window. This kit lists the five images it needs, how to take them, and how to check them before they are published. Generated, mocked-up or edited UI is never acceptable. Cropping, resizing and lossless optimization are the only changes allowed.

**Status (9 November 2026): none of the five screenshots exists yet.** No disposable interactive Mac was available to the agent, and the owner's personal desktop is out of bounds for automated capture.

## Where to take them

Use a **disposable macOS environment**, not your everyday account. Then the candidate's ad-hoc signature, Screen Recording approval and `/Applications` copy cannot interfere with your installed ContextLens. Choose one of these:

- **Recommended:** a macOS virtual machine on this Mac (for example UTM or another Apple Virtualization front end). ScreenCaptureKit works inside the guest. The same VM can run the [release acceptance](../release-acceptance/README.md) checklist, so one session covers both jobs.
- A spare Mac you can erase afterwards.

A second user account on your own Mac is **not** enough: `/Applications` is shared, so dragging the candidate there would replace your installed copy.

## What to install

Use the exact official candidate, not a local build:

```sh
gh run download 42504640955 --repo Brendan-Lim/ContextLens --name official-candidate-0.3.1 --dir candidate
cd candidate && shasum -a 256 -c SHA256SUMS
```

Expected hashes: ZIP `1744796e…e501e`, DMG `2c0e1adf…bf76`. The full values are in [official-release preparation](../official-release-preparation.md). The artifact expires on **8 December 2026**. For a genuine Gatekeeper first launch, the DMG must arrive in the VM through a browser download, so it receives quarantine. Downloading the artifact zip from the Actions run page while signed in to GitHub inside the VM works. Confirm the version before capturing: **ContextLens → About** should show 0.3.1 (6).

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
