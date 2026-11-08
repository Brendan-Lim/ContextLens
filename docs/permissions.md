# Screen Recording: enabled in Settings, unavailable in the app

An enabled System Settings switch does not prove that the currently running binary matches the approved identity. The initial local build script signed ContextLens ad-hoc. Its designated requirement was pinned to a specific code hash, so changing the executable could invalidate an earlier approval while the Settings entry remained visible.

Apple confirms that ad-hoc builds are treated as new identities, and recommends a stable development signing identity: [Apple Developer Forums / DTS response](https://developer.apple.com/forums/thread/819406).

## Fixed in 0.2.1

- The local build script uses an available Apple Development certificate, or the identity explicitly selected with `CONTEXTLENS_SIGN_IDENTITY`. It falls back to ad-hoc only when no identity is available or `-` is explicitly selected (for example, CI). The fallback message explains the permission consequence.
- On this machine, the rebuilt bundle was signed and verified with an Apple Development identity. Its designated requirement is certificate/identifier based, not pinned to the executable hash. The private key is not exported and no upload or distribution is performed.
- The permission preflight is only a hint. A user-initiated **Check Access** or refresh attempts actual ScreenCaptureKit window enumeration even if preflight is false. Successful enumeration verifies access; an API failure does not become success merely because preflight is true.
- Returning to ContextLens refreshes access/window state automatically. Passive initial startup does not trigger a first-use permission prompt when no approval is known.
- Recovery text distinguishes unavailable access from a proven disabled switch, and shows the running app path to avoid approving a different copy. Stale selected-window IDs are cleared or replaced only within the picker; an ongoing capture still never switches targets.

## One-time repair after switching signing identity

If the old enabled entry still fails:

1. Quit ContextLens fully.
2. In System Settings → Privacy & Security → Screen & System Audio Recording, remove **only ContextLens** using the minus button.
3. Add the rebuilt `dist/ContextLens.app` using the plus button and enable it.
4. Open that copy and press **Check Access**, then choose a window.

This replaces the old identity's approval. ContextLens does not reset privacy settings or grant consent on the user's behalf. It does not alter approvals for other applications.

## Verification

28 Swift tests passed, including explicit retry with false preflight, passive startup without prompting, rechecking previously verified access, and actual API errors despite positive preflight. Release signing and bundle integrity checks passed. Full capture verification for the new identity still requires the user's macOS approval; test success is not represented as a substitute for that consent.

## Confirmed stale-record failure and targeted repair

During the subsequent user report, `tccd` logged “Failed to match existing code requirement” for ContextLens Screen Capture. Its stored requirement still referred to an old ad-hoc hash, whereas the current signed bundle had a different hash and certificate-based requirement. This explained the repeated request despite the enabled Settings entry; it was confirmed from system logs rather than inferred from the checkbox.

With explicit user approval, `scripts/repair-screen-access.sh` quit ContextLens normally, preserved a backup while refreshing bundle file identities, ran **only** `tccutil reset ScreenCapture dev.contextlens.app`, and relaunched it. After the fresh macOS approval, the user confirmed application windows appeared. A subsequent generated-window test obtained actual ScreenCaptureKit pixels and verified movement and resize handling. See [repair verification](examples/permission-repair-verification.json).

Future builds now construct and sign a separate complete bundle, verify it, then publish it using renames while retaining the previous bundle. They no longer copy over a running executable in place. A controlled staged rebuild preserved the exact signing requirement while replacing the executable inode. The repair script is never run automatically by the app or build.
