import SwiftUI
import AppKit
import ContextLensCore
import ContextLensCapture

// MARK: First launch

struct OnboardingView: View {
    @EnvironmentObject var model: AppModel
    var done: () -> Void
    @State private var mascotUp = false
    @State private var showScreenAccessDetails = false
    @Environment(\.accessibilityReduceMotion) private var reduce

    var body: some View {
        VStack(spacing: 20) {
            MascotView(style: .peek)
                .frame(width: 96, height: 96)
                .offset(y: mascotUp || reduce ? 0 : 26)
                .opacity(mascotUp ? 1 : 0)
                .padding(.top, 8)
            VStack(spacing: 10) {
                WordmarkView().frame(width: 150)
                Text("Give your AI agent eyes.").font(Lens.font(30, .heavy)).foregroundStyle(Lens.brandInk)
                Text("Capture one window, mark what should change, and hand it to Claude Code or Codex. Everything stays on your Mac.")
                    .font(Lens.font(15)).foregroundStyle(Lens.muted).multilineTextAlignment(.center).frame(maxWidth: 480)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .staggerIn(0)
            VStack(spacing: 10) {
                StepRow(icon: "display", title: "Screen Recording", tag: "Required",
                        detail: "\(model.screenAccess.title). \(model.screenAccess.message)", granted: model.screenPermission) {
                    Button("Open Settings", action: Permissions.openScreenSettings).buttonStyle(.lens(.quiet, height: 32))
                    Button(model.checkingScreenAccess ? "Checking…" : "Check Access") { Task { await model.refresh(userInitiated: true) } }
                    .buttonStyle(.lens(.primary, height: 32))
                    .disabled(model.checkingScreenAccess)
                    Button("Details…") { showScreenAccessDetails = true }
                        .buttonStyle(.lens(.quiet, height: 32))
                }
                .staggerIn(1)
                .popover(isPresented: $showScreenAccessDetails) {
                    ScrollView { ScreenAccessDetails().padding(20) }
                        .frame(width: 420, height: 360)
                }
                StepRow(icon: "cursorarrow.rays", title: "Accessibility", tag: "Optional",
                        detail: "Notes which kind of control you clicked, like “button”. Never reads text, values or passwords.", granted: model.axPermission) {
                    Button("Allow", action: Permissions.requestAccessibility).buttonStyle(.lens(.ghost, height: 32))
                }
                .staggerIn(2)
                StepRow(icon: "folder", title: "Where sessions are kept", tag: nil,
                        detail: (model.storageBase.path as NSString).abbreviatingWithTildeInPath, granted: false, monoDetail: true) {
                    Button("Change…") {
                        if let folder = model.chooseFolder(message: "Choose where new sessions are stored") { model.storageBase = folder }
                    }
                    .buttonStyle(.lens(.ghost, height: 32))
                    .disabled(model.recording)
                }
                .staggerIn(3)
            }
            HStack(spacing: 16) {
                Label("Nothing is uploaded or sent to an agent until you copy it.", systemImage: "lock")
                    .font(Lens.font(13)).foregroundStyle(Lens.muted)
                Spacer()
                Button("Start using ContextLens", action: done)
                    .buttonStyle(.lens(.primary, height: 42))
                    .keyboardShortcut(.defaultAction)
            }
            .staggerIn(4)
        }
        .padding(.horizontal, 36).padding(.bottom, 28).padding(.top, 12)
        .frame(width: 700)
        .background(Lens.canvas)
        .onAppear {
            // First launch is a rare moment: the mascot rises into view once.
            withAnimation(Motion.ease(0.42).delay(0.45)) { mascotUp = true }
        }
    }
}

private struct StepRow<Actions: View>: View {
    let icon: String
    let title: String
    let tag: String?
    let detail: String
    let granted: Bool
    var monoDetail = false
    @ViewBuilder var actions: Actions

    var body: some View {
        HStack(spacing: 14) {
            SwapIcon(from: icon, to: "checkmark", swapped: granted)
                .font(.system(size: 17, weight: .semibold))
                .foregroundStyle(granted ? Lens.success : Lens.accent)
                .frame(width: 40, height: 40)
                .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(granted ? Lens.successFill : Lens.selectedFill))
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 8) {
                    Text(title).font(Lens.font(15, .heavy)).foregroundStyle(Lens.ink)
                    if let tag {
                        Text(tag).font(Lens.font(11, .heavy)).padding(.horizontal, 8).frame(height: 20)
                            .background(Capsule().fill(tag == "Required" ? Lens.selectedFill : Lens.sunken))
                            .foregroundStyle(tag == "Required" ? Lens.accent : Lens.muted)
                    }
                }
                Text(detail).font(monoDetail ? Lens.mono(12) : Lens.font(13)).foregroundStyle(Lens.muted)
                    .fixedSize(horizontal: false, vertical: true).textSelection(.enabled)
            }
            Spacer(minLength: 8)
            if granted {
                Text("Allowed").font(Lens.font(13.5, .heavy)).foregroundStyle(Lens.success)
            } else {
                HStack(spacing: 6) { actions }
            }
        }
        .padding(.horizontal, 16).padding(.vertical, 14)
        .background(RoundedRectangle(cornerRadius: 16, style: .continuous).fill(granted ? Lens.successFill.opacity(0.5) : Lens.surface))
        .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).strokeBorder(Lens.line, lineWidth: 1))
        .animation(.easeOut(duration: 0.2), value: granted)
    }
}

// MARK: Storage & Privacy

struct PrivacyView: View {
    @EnvironmentObject var model: AppModel
    @Environment(\.dismiss) private var dismiss
    @Environment(\.accessibilityReduceMotion) private var reduce
    @State private var confirmDelete = false
    @State private var confirmBurn = false
    @State private var pruneMessage: String?
    @State private var deleted = false

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(spacing: 12) {
                MascotView().frame(width: 40, height: 40)
                VStack(alignment: .leading, spacing: 2) {
                    Text("Storage & Privacy").font(Lens.font(21, .heavy)).foregroundStyle(Lens.brandInk)
                    Text("Everything ContextLens keeps lives on this Mac.").font(Lens.font(12.5)).foregroundStyle(Lens.muted)
                }
            }
            section {
                Text("Where sessions are kept").font(Lens.font(14, .heavy))
                HStack(spacing: 10) {
                    Text((model.storageBase.path as NSString).abbreviatingWithTildeInPath)
                        .font(Lens.mono(12)).foregroundStyle(Lens.muted).lineLimit(1).truncationMode(.middle)
                        .padding(.horizontal, 12).frame(maxWidth: .infinity, minHeight: 34, alignment: .leading)
                        .background(RoundedRectangle(cornerRadius: 10, style: .continuous).fill(Lens.sunken))
                        .textSelection(.enabled)
                    Button("Choose…") {
                        if let folder = model.chooseFolder(message: "Choose where new sessions are stored") { model.storageBase = folder }
                    }
                    .buttonStyle(.lens(.ghost, height: 34)).disabled(model.recording)
                }
            }
            section {
                HStack(alignment: .center, spacing: 12) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Keep sessions for").font(Lens.font(14, .heavy))
                        Text("Older sessions are only removed when you press Delete older sessions. Exports are never touched.")
                            .font(Lens.font(12.5)).foregroundStyle(Lens.muted).fixedSize(horizontal: false, vertical: true)
                    }
                    Spacer()
                    Stepper(value: $model.retentionDays, in: 1...365) {
                        Text("\(model.retentionDays) days").font(Lens.font(13.5, .heavy)).monospacedDigit()
                    }
                    .fixedSize()
                }
                HStack(spacing: 12) {
                    Button("Delete older sessions") { model.pruneSessions(); pruneMessage = model.status }
                        .buttonStyle(.lens(.ghost, height: 34)).disabled(model.recording)
                    if let pruneMessage {
                        Text(pruneMessage).font(Lens.font(12.5, .bold)).foregroundStyle(Lens.success).transition(.lensRise(reduce, distance: -4))
                    }
                }
            }
            section {
                Text("What ContextLens records").font(Lens.font(14, .heavy))
                HStack(alignment: .top, spacing: 16) {
                    VStack(alignment: .leading, spacing: 8) {
                        record(true, "Pixels of the one window you pick")
                        record(true, "The kind of control you clicked, if Accessibility is on")
                        record(true, "Your marks and notes")
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    VStack(alignment: .leading, spacing: 8) {
                        record(false, "Typed text, field values or passwords")
                        record(false, "Audio from any source")
                        record(false, "Uploads of any kind")
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                Text("Screenshots can still show sensitive text that was on screen. Look over a package before you share it.")
                    .font(Lens.font(12.5)).foregroundStyle(Lens.muted)
            }
            if model.session.annotations.contains(where: { $0.kind == .redaction }) {
                section {
                    Text("This older session has redactions. They are burned into every exported image; local originals keep the pixels until you apply them permanently or delete the session.")
                        .font(Lens.font(12.5)).foregroundStyle(Lens.muted).fixedSize(horizontal: false, vertical: true)
                    if confirmBurn {
                        confirmBox(title: "Permanently cover redacted pixels in the local originals?",
                                   detail: "This clears undo history and can't be reversed.",
                                   action: "Apply Permanently") { model.burnLocalRedactions(); confirmBurn = false } cancel: { confirmBurn = false }
                    } else {
                        Button("Apply redactions permanently…") { confirmBurn = true }
                            .buttonStyle(.lens(.danger, height: 34)).disabled(model.root == nil || model.recording)
                    }
                }
            }
            VStack(alignment: .leading, spacing: 10) {
                if deleted {
                    Text("Session deleted. Exported packages were not touched.").font(Lens.font(12.5, .bold)).foregroundStyle(Lens.success)
                } else if confirmDelete {
                    confirmBox(title: "Delete this session and its \(model.session.frames.count) original screenshots?",
                               detail: "Packages you already exported stay where they are. This can't be undone.",
                               action: "Delete Session") { model.deleteSession(); confirmDelete = false; deleted = model.root == nil } cancel: { confirmDelete = false }
                } else {
                    HStack(spacing: 12) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Delete this session").font(Lens.font(14, .heavy))
                            Text(model.canDeleteSession ? "Removes it and its original screenshots from this Mac."
                                 : "Only sessions in the storage folder can be deleted here. Manage other folders in Finder.")
                                .font(Lens.font(12.5)).foregroundStyle(Lens.muted)
                        }
                        Spacer()
                        Button("Delete…") { confirmDelete = true }
                            .buttonStyle(.lens(.danger, height: 34)).disabled(!model.canDeleteSession || model.recording)
                    }
                }
            }
            HStack {
                Spacer()
                Button("Done") { dismiss() }.buttonStyle(.lens(.primary, height: 38)).keyboardShortcut(.defaultAction)
            }
        }
        .padding(26)
        .frame(width: 620)
        .background(Lens.surface)
        .animation(reduce ? .easeOut(duration: 0.15) : Motion.standard, value: confirmDelete)
        .animation(reduce ? .easeOut(duration: 0.15) : Motion.standard, value: confirmBurn)
        .animation(reduce ? .easeOut(duration: 0.15) : Motion.standard, value: pruneMessage)
    }

    private func section<Content: View>(@ViewBuilder _ content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) { content() }
            .padding(.bottom, 14)
            .overlay(alignment: .bottom) { Rectangle().fill(Lens.line).frame(height: 1) }
    }

    private func record(_ yes: Bool, _ text: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 8) {
            Image(systemName: yes ? "checkmark" : "xmark").font(.system(size: 11, weight: .heavy))
                .foregroundStyle(yes ? Lens.success : Lens.danger)
            Text(text).font(Lens.font(13)).fixedSize(horizontal: false, vertical: true)
        }
    }

    private func confirmBox(title: String, detail: String, action: String, confirm: @escaping () -> Void, cancel: @escaping () -> Void) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(Lens.font(13.5, .heavy)).foregroundStyle(Lens.danger)
            Text(detail).font(Lens.font(12.5)).foregroundStyle(Lens.muted)
            HStack(spacing: 8) {
                Spacer()
                Button("Cancel", action: cancel).buttonStyle(.lens(.ghost, height: 32)).keyboardShortcut(.cancelAction)
                Button(action, role: .destructive, action: confirm).buttonStyle(.lens(.dangerSolid, height: 32))
            }
        }
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(Lens.dangerFill))
        .transition(.lensRise(reduce, distance: -4))
    }
}
