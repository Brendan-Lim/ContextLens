# Screen Recording access

ContextLens verifies access by asking ScreenCaptureKit for shareable windows. A successful enumeration verifies access, including when no eligible windows are open. A System Settings switch or Core Graphics preflight flag alone cannot verify it. The CLI's `permissions` command reports the CLI process's preflight hint; it does not test the running app's ScreenCaptureKit access.

## First install

1. Open the copy you intend to use. Keep one installed copy, normally `/Applications/ContextLens.app`, and quit other development or mounted-image copies.
2. In onboarding or the Capture panel, choose **Check Access**. Passive first startup avoids triggering a permission prompt when no prior approval is known.
3. Respond yourself to any macOS prompt. In System Settings → Privacy & Security → Screen & System Audio Recording, enable that copy of ContextLens. Follow any macOS **Quit & Reopen** request.
4. Reopen the same copy and choose **Check Access**. Select a window only after access is verified. Then test an actual capture of synthetic content.

Denial leaves capture unavailable. ContextLens does not approve prompts, edit TCC, change privacy settings or reset other applications' permissions.

## Interpret the app's result

- **Access unverified:** ScreenCaptureKit has not verified this run. Choose Check Access.
- **Access denied:** ScreenCaptureKit returned its explicit permission-denial error. Enable the intended copy in Settings, then relaunch if macOS requests it.
- **Verification failed:** enumeration returned another error. The app shows its actual domain, code, description, failure reason/recovery suggestion when supplied, and bounded underlying errors. Resolve that error and retry.
- **Access verified:** ScreenCaptureKit enumeration succeeded. An empty window list means no eligible application window was returned. A subsequent explicit permission denial clears access and the old selection.

The app shows **Running copy** beside the failure. **Copy and signing details** identifies its bundle/executable paths, bundle ID, version/build, process and code hash when available, plus whether the process has an ad-hoc or certificate signature. **Show This Copy in Finder** reveals that exact bundle. Onboarding exposes the same diagnostics through **Details…**. These details stay local in the UI; the app does not log paths or raw errors or upload diagnostics.

## Enabled in Settings but still unavailable

An enabled switch can refer to a code identity that no longer matches this executable. Multiple copies with the same bundle ID can make the approved copy ambiguous. The app cannot determine the stored TCC requirement from the checkbox or safely repair it automatically.

For a stale enabled entry, reconnect the intended copy manually:

1. Save your work and quit all ContextLens copies.
2. Open System Settings → Privacy & Security → Screen & System Audio Recording. Remove **only ContextLens** with the minus button.
3. Use the plus button to add the exact bundle shown by **Running copy**. In the file chooser, Command-Shift-G accepts its full path. Enable its switch.
4. Reopen that same bundle, follow any macOS Quit & Reopen request, and choose Check Access. Successful enumeration and a real synthetic-window capture are the recovery criteria.

This is a recovery procedure, not a guarantee that every macOS error is a stale authorization. If it still fails, retain the error details and running-copy identity locally. Do not repeatedly toggle unrelated approvals, reset the entire privacy database, strip quarantine or change system security policy.

## Signing and upgrades

Ad-hoc signing has no stable certificate identity. Its default designated requirement is tied to the executable's code hash, so changing the executable or switching to/from a certificate-signed development copy can invalidate the previous authorization while an enabled Settings entry remains. Apple confirms this behavior and recommends a stable development signing identity: [Apple DTS explanation](https://developer.apple.com/forums/thread/819406), [code-signing requirements](https://developer.apple.com/documentation/technotes/tn3127-inside-code-signing-requirements).

Local development builds use an available Apple Development identity, or `CONTEXTLENS_SIGN_IDENTITY` when explicitly supplied. CI, preview and the official unnotarized channel deliberately use ad-hoc signing. Their updates may require manual reconnection; seamless retention of Screen Recording permission across those updates is not promised. The Developer ID/notarized channel retains its separate signing and release gates. Do not change the bundle ID or add an artificial signing requirement to imitate an existing approval.

Builds create and verify a separate complete bundle before promoting it by rename. They do not overwrite a running executable in place. This preserves bundle integrity, but cannot turn a changed ad-hoc code hash into the previously approved identity.

## Verification boundaries

Automated tests cover the passive/explicit/preflight gate, propagation of API failures, distinct states, permission-error classification and diagnostic retention. They do not establish genuine human consent. On a disposable Mac, follow [isolated acceptance](beta-acceptance.md): deny, grant, relaunch, capture synthetic content, revoke and recover against the **same signed bytes**. Separately test an update with a different ad-hoc code hash and the same bundle ID. Record the actual macOS version and preserve private observations outside Git.

A hosted runner with existing access can verify native API and UI behavior, but cannot stand in for a fresh human grant or revocation. Keep those security cases pending until a person performs them. Do not run native fixtures or approval experiments against the owner's working installation.
