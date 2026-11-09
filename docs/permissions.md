# Screen Recording and development signing

Grant Screen Recording for the copy you actually launch in **System Settings → Privacy & Security → Screen & System Audio Recording** (Screen Recording on older macOS). Relaunch when macOS requests it, then use **Check Access** and explicitly select a window. Accessibility is optional and enables clicked-control labels; typed text and editable field values are not collected.

An enabled Settings entry does not prove the running binary matches its approved identity. Ad-hoc signing changes can invalidate consent while an old entry remains visible. Apple recommends a stable development signing identity: [Apple Developer Forums / DTS](https://developer.apple.com/forums/thread/819406).

## Build identity

Local builds use an available Apple Development certificate or `CONTEXTLENS_SIGN_IDENTITY`, falling back to ad-hoc when none exists or `-` is selected. Apple Development signatures do not establish public distribution trust. Official unnotarized/preview builds deliberately use ad-hoc signatures and updates may require new consent. [Build instructions](building.md).

The app treats permission preflight as a hint. User-initiated **Check Access** attempts real ScreenCaptureKit enumeration even when preflight is false. Successful enumeration verifies access; positive preflight does not turn API errors into success. Passive initial launch avoids prompting when no approval is known, and reactivation refreshes access/window state. The running-copy path helps distinguish installations. Ongoing capture never changes targets when picker state refreshes.

## Recover a stale entry

1. Quit ContextLens fully and confirm which copy you intend to use.
2. In the Screen Recording settings, remove **only ContextLens** with the minus button.
3. Add that intended app with the plus button, enable it and reopen it.
4. Use **Check Access**, then choose a window.

This replaces the old identity's approval through the user's settings. Builds/installations never reset TCC or grant consent automatically. The maintainer-only `scripts/repair-screen-access.sh` performs a targeted reset and relaunch; inspect it and obtain explicit user authorization before running it. It is not an automated test or ordinary installation step.

Build publishing stages/signs/verifies a complete bundle and replaces it with renames, retaining the previous bundle instead of copying over a running executable. Unit tests cover passive startup, false-preflight retry and actual API failures. They cannot establish a person's consent. Fresh denial, grant/relaunch and revocation/recovery remain human acceptance cases; see [the isolated procedure](beta-acceptance.md) and [current release baseline](official-release-preparation.md).
