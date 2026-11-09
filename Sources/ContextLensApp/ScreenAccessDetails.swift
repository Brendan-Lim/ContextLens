import SwiftUI
import AppKit
import ContextLensCapture

/// Shared by onboarding and the capture panel. All diagnostics stay in this UI.
struct ScreenAccessDetails: View {
    @EnvironmentObject var model: AppModel
    @State private var showRecovery = false
    @State private var showIdentity = false
    private let identity = Permissions.runningCopyDescription

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Running copy: \(Bundle.main.bundleURL.path)")
                .font(Lens.mono(10.5)).textSelection(.enabled).fixedSize(horizontal: false, vertical: true)
            if let message = model.screenAccess.errorDetails {
                Text(message).font(Lens.mono(10.5)).textSelection(.enabled)
                    .fixedSize(horizontal: false, vertical: true)
            }
            DisclosureGroup("Copy and signing details", isExpanded: $showIdentity) {
                Text(identity).font(Lens.mono(10.5)).textSelection(.enabled)
                    .fixedSize(horizontal: false, vertical: true).padding(.top, 4)
            }
            DisclosureGroup("Reconnect an enabled entry", isExpanded: $showRecovery) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("1. Save your work and quit all ContextLens copies.")
                    Text("2. Open System Settings → Privacy & Security → Screen & System Audio Recording. Remove only ContextLens with the − button.")
                    Text("3. Use + to add the running copy shown above. In the file chooser, ⌘⇧G lets you enter its full path. Enable its switch.")
                    Text("4. Reopen that same copy, following any macOS Quit & Reopen request, then choose Check Access. Access is verified only when ScreenCaptureKit enumeration succeeds.")
                    Text("Ad-hoc updates and switching between development and release copies can change the approved identity even when the name is unchanged. These steps require your approval in macOS.")
                }
                .fixedSize(horizontal: false, vertical: true).padding(.top, 4)
            }
            Button("Show This Copy in Finder") {
                NSWorkspace.shared.activateFileViewerSelecting([Bundle.main.bundleURL])
            }
            .buttonStyle(.link)
        }
        .font(Lens.font(11.5)).foregroundStyle(Lens.muted)
    }
}
