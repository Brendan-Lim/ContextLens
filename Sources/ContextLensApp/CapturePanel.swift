import SwiftUI
import AppKit
import Combine
import ContextLensCore
import ContextLensCapture

/// A floating panel that does not activate ContextLens, so the person keeps working in the captured app.
final class LensPanel: NSPanel {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }
}

/// Owns the capture panel and the desktop highlight around the chosen window.
@MainActor final class CapturePanelController: NSObject, NSWindowDelegate {
    static let shared = CapturePanelController()
    private var panel: LensPanel?
    private let highlight = WindowHighlightController()
    private var observation: AnyCancellable?
    private weak var model: AppModel?
    private var showMain: () -> Void = {}
    private var anchoredRecording: Bool?
    private var wasRecording = false
    private var lastFrame: NSRect = .zero

    func attach(model: AppModel, showMain: @escaping () -> Void) {
        self.model = model
        self.showMain = showMain
        guard observation == nil else { return }
        observation = model.objectWillChange.sink { [weak self] _ in
            // objectWillChange fires before the new value is stored.
            DispatchQueue.main.async { self?.sync() }
        }
    }

    var isVisible: Bool { panel?.isVisible == true }

    func show() {
        guard let model else { return }
        if panel == nil { build(model) }
        anchoredRecording = nil
        panel?.orderFrontRegardless()
        anchor()
        Task { await model.refresh() }
        sync()
    }

    func hide() {
        panel?.orderOut(nil)
        highlight.hide()
    }

    private func build(_ model: AppModel) {
        let root = CapturePanelView(close: { [weak self] in self?.hide() },
                                    openMain: { [weak self] in self?.showMain() })
            .environmentObject(model)
        let hosting = NSHostingView(rootView: root)
        let panel = LensPanel(contentRect: NSRect(x: 0, y: 0, width: 320, height: 520),
                              styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        panel.contentView = hosting
        panel.title = "ContextLens Capture"
        panel.isFloatingPanel = true
        panel.level = NSWindow.Level(rawValue: NSWindow.Level.floating.rawValue + 1)
        panel.hidesOnDeactivate = false
        panel.isMovableByWindowBackground = true
        panel.backgroundColor = .clear
        panel.isOpaque = false
        panel.hasShadow = true
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.isReleasedWhenClosed = false
        panel.delegate = self
        self.panel = panel
    }

    private func openReview() {
        model?.mainTab = .review
        hide()
        showMain()
    }

    /// Idle: top-right of the screen. Recording: top centre, as a compact pill.
    private func anchor() {
        guard let panel, let model else { return }
        let recording = model.recording || model.stopping
        guard anchoredRecording != recording else { return }
        anchoredRecording = recording
        guard let visible = (NSScreen.main ?? NSScreen.screens.first)?.visibleFrame else { return }
        let size = panel.frame.size
        let origin = recording
            ? NSPoint(x: visible.midX - size.width / 2, y: visible.maxY - size.height - 10)
            : NSPoint(x: visible.maxX - size.width - 24, y: visible.maxY - size.height - 24)
        panel.setFrameOrigin(origin)
        lastFrame = panel.frame
    }

    func windowDidMove(_ notification: Notification) { if let panel { lastFrame = panel.frame } }

    /// Content changes resize the panel; keep its top edge (and right edge or centre) where it was.
    func windowDidResize(_ notification: Notification) {
        guard let panel, let model else { return }
        if lastFrame != .zero {
            let recording = model.recording || model.stopping
            var frame = panel.frame
            frame.origin.y = lastFrame.maxY - frame.height
            frame.origin.x = recording ? lastFrame.midX - frame.width / 2 : lastFrame.maxX - frame.width
            if frame.origin != panel.frame.origin { panel.setFrameOrigin(frame.origin) }
        }
        lastFrame = panel.frame
    }

    private func sync() {
        guard let model else { return }
        let recording = model.recording || model.stopping
        // When a capture ends, go straight to Review; with nothing captured, the picker stays up to try again.
        if wasRecording && !recording {
            wasRecording = false
            if !model.session.frames.isEmpty { openReview(); return }
        }
        wasRecording = recording
        anchor()
        guard isVisible else { highlight.hide(); return }
        let frame: CGRect?
        if recording { frame = model.targetFrame }
        else { frame = model.windows.first(where: { $0.id == model.windowID })?.window.frame }
        if let frame { highlight.show(globalFrame: frame, recording: recording) } else { highlight.hide() }
    }
}

// MARK: Desktop highlight

@MainActor final class HighlightState: ObservableObject {
    @Published var recording = false
    @Published var tagAbove = true
}

/// A click-through outline drawn around the chosen window. It is never part of the capture,
/// which always uses the selected window alone.
@MainActor final class WindowHighlightController {
    private var window: NSWindow?
    private let state = HighlightState()
    private let tagSpace: CGFloat = 34

    func show(globalFrame: CGRect, recording: Bool) {
        guard let primary = NSScreen.screens.first else { return }
        // ScreenCaptureKit frames use a top-left origin on the primary display.
        let cocoa = NSRect(x: globalFrame.minX, y: primary.frame.maxY - globalFrame.maxY, width: globalFrame.width, height: globalFrame.height)
        var frame = cocoa.insetBy(dx: -8, dy: -8)
        let screenTop = (NSScreen.screens.first { $0.frame.intersects(cocoa) } ?? primary).visibleFrame.maxY
        let tagAbove = frame.maxY + tagSpace <= screenTop
        if tagAbove { frame.size.height += tagSpace }
        if window == nil { build() }
        if state.recording != recording { state.recording = recording }
        if state.tagAbove != tagAbove { state.tagAbove = tagAbove }
        guard let window else { return }
        if window.frame != frame { window.setFrame(frame, display: true) }
        if !window.isVisible {
            window.alphaValue = 0
            window.orderFrontRegardless()
            NSAnimationContext.runAnimationGroup { context in
                context.duration = 0.2
                window.animator().alphaValue = 1
            }
        }
    }

    func hide() { window?.orderOut(nil) }

    private func build() {
        let window = NSWindow(contentRect: .zero, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = NSHostingView(rootView: HighlightView(state: state))
        window.isOpaque = false
        window.backgroundColor = .clear
        window.hasShadow = false
        window.ignoresMouseEvents = true
        window.level = .floating
        window.sharingType = .none
        window.isReleasedWhenClosed = false
        window.collectionBehavior = [.canJoinAllSpaces, .stationary, .ignoresCycle, .fullScreenAuxiliary]
        self.window = window
    }
}

private struct HighlightView: View {
    @ObservedObject var state: HighlightState
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if state.tagAbove { tag }
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .strokeBorder(.white.opacity(0.9), lineWidth: 5)
                .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).strokeBorder(color, lineWidth: 3).padding(1))
                .overlay(alignment: .topLeading) { if !state.tagAbove { tag.padding(12) } }
        }
    }
    private var color: Color { state.recording ? Lens.record : Lens.navy }
    private var tag: some View {
        HStack(spacing: 6) {
            if state.recording { RecordDot(size: 7, color: .white) }
            Text(state.recording ? "Recording this window only" : "ContextLens will capture this window")
        }
        .font(Lens.font(12, .bold))
        .foregroundStyle(.white)
        .padding(.horizontal, 10).frame(height: 24)
        .background(Capsule().fill(color))
        .shadow(color: .black.opacity(0.2), radius: 4, y: 2)
    }
}

// MARK: Panel content

struct CapturePanelView: View {
    @EnvironmentObject var model: AppModel
    var close: () -> Void
    var openMain: () -> Void
    @Environment(\.accessibilityReduceMotion) private var reduce

    private enum Phase { case pick, recording }
    private var phase: Phase { model.recording || model.stopping ? .recording : .pick }

    var body: some View {
        Group {
            switch phase {
            case .pick: PickWindowCard(close: close, openMain: openMain)
            case .recording: RecordingPill()
            }
        }
        .transition(.lensPop(reduce))
        .animation(reduce ? .easeOut(duration: 0.15) : Motion.enter, value: phase)
        .fixedSize()
    }
}

private struct PanelCard<Content: View>: View {
    @ViewBuilder var content: Content
    var body: some View {
        content
            .padding(14)
            .frame(width: 300)
            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
            .background(Lens.surface.opacity(0.6), in: RoundedRectangle(cornerRadius: 20, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 20, style: .continuous).strokeBorder(Lens.line, lineWidth: 1))
    }
}

private struct PickWindowCard: View {
    @EnvironmentObject var model: AppModel
    var close: () -> Void
    var openMain: () -> Void
    @State private var showOptions = false
    @Environment(\.accessibilityReduceMotion) private var reduce

    var body: some View {
        ZStack(alignment: .top) {
            PanelCard {
                VStack(alignment: .leading, spacing: 14) {
                    Text("Which window?").font(Lens.font(15, .heavy)).foregroundStyle(Lens.brandInk)
                        .frame(maxWidth: .infinity)
                        .padding(.top, 22)
                    if model.screenPermission { windowList } else { PermissionBlock() }
                    sensitivity
                    options
                    Button { Task { await model.start() } } label: {
                        HStack(spacing: 8) { Circle().fill(Color(hex: 0xFF8A8E)).frame(width: 9, height: 9); Text("Start Capture") }
                    }
                    .buttonStyle(.lens(.primary, height: 42, fullWidth: true))
                    .disabled(model.windowID == nil || !model.screenPermission || model.checkingScreenAccess)
                    .keyboardShortcut(.defaultAction)
                    Button("Open ContextLens", action: openMain).buttonStyle(.plain).font(Lens.font(12, .bold)).foregroundStyle(Lens.accent)
                        .frame(maxWidth: .infinity)
                }
            }
            .overlay(alignment: .topTrailing) {
                HStack(spacing: 2) {
                    Button { Task { await model.refresh(userInitiated: true) } } label: { Image(systemName: "arrow.clockwise") }
                        .help("Check access and refresh windows").accessibilityLabel("Refresh windows")
                        .disabled(model.checkingScreenAccess)
                    Button(action: close) { Image(systemName: "xmark") }
                        .help("Close").accessibilityLabel("Close capture panel")
                }
                .buttonStyle(LensIconButtonStyle(size: 26))
                .padding(8)
            }
            .padding(.top, 50)
            MascotView(style: .peek).frame(width: 76, height: 76).allowsHitTesting(false)
        }
    }

    private var windowList: some View {
        ScrollView {
            VStack(spacing: 2) {
                ForEach(model.windows) { choice in WindowRow(choice: choice) }
                if model.windows.isEmpty {
                    Text("Open the app you want to capture, then refresh.")
                        .font(Lens.font(12.5)).foregroundStyle(Lens.muted).padding(.vertical, 18)
                }
            }
        }
        .frame(maxHeight: 236)
        .fixedSize(horizontal: false, vertical: model.windows.count < 6)
    }

    private var sensitivity: some View {
        VStack(alignment: .leading, spacing: 7) {
            SectionLabel("Sensitivity").padding(.horizontal, 4)
            LensSegments(selection: $model.sensitivity, options: [
                SegmentOption(value: Sensitivity.low, title: "Low"),
                SegmentOption(value: Sensitivity.high, title: "High")
            ])
            Text(model.sensitivity == .low ? "Captures state changes less frequently." : "Captures state changes more frequently.")
                .font(Lens.font(12)).foregroundStyle(Lens.muted).padding(.horizontal, 4)
        }
    }

    private var options: some View {
        VStack(alignment: .leading, spacing: 10) {
            Button {
                withAnimation(reduce ? nil : Motion.standard) { showOptions.toggle() }
            } label: {
                HStack {
                    Text("Capture options").font(Lens.font(12.5, .bold)).foregroundStyle(Lens.muted)
                    Spacer()
                    Image(systemName: "chevron.down").font(.system(size: 11, weight: .bold)).foregroundStyle(Lens.muted)
                        .rotationEffect(.degrees(showOptions ? 180 : 0))
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityValue(showOptions ? "Expanded" : "Collapsed")
            if showOptions {
                VStack(alignment: .leading, spacing: 10) {
                    Toggle(isOn: $model.deduplicate) { Text("Filter duplicate states").font(Lens.font(13)) }.toggleStyle(LensSwitchStyle())
                    Stepper(value: $model.maximumFrames, in: 5...500, step: 5) { Text("Stop after \(model.maximumFrames) states").font(Lens.font(13)) }
                    Stepper(value: $model.delaySeconds, in: 0...10) { Text(model.delaySeconds == 0 ? "No start delay" : "Start after \(model.delaySeconds) s").font(Lens.font(13)) }
                }
                .transition(.lensRise(reduce, distance: -4))
            }
        }
        .padding(.horizontal, 4)
    }
}

private struct WindowRow: View {
    @EnvironmentObject var model: AppModel
    let choice: WindowChoice
    @State private var hover = false
    private var selected: Bool { model.windowID == choice.id }
    var body: some View {
        Button { model.windowID = choice.id } label: {
            HStack(spacing: 10) {
                AppIcon(pid: choice.window.owningApplication?.processID).frame(width: 28, height: 28)
                VStack(alignment: .leading, spacing: 1) {
                    Text(choice.app).font(Lens.font(13, .bold)).foregroundStyle(Lens.ink)
                    Text(choice.title).font(Lens.font(11.5)).foregroundStyle(Lens.muted).lineLimit(1)
                }
                Spacer(minLength: 4)
                ZStack {
                    Circle().strokeBorder(selected ? Lens.accent : Lens.lineStrong, lineWidth: selected ? 9 : 1.5)
                    Circle().fill(.white).frame(width: 7, height: 7).opacity(selected ? 1 : 0)
                }
                .frame(width: 18, height: 18)
            }
            .padding(8)
            .background(RoundedRectangle(cornerRadius: 11, style: .continuous)
                .fill(selected ? Lens.selectedFill : (hover ? Lens.sunken : .clear)))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { hover = $0 }
        .animation(.easeOut(duration: 0.15), value: selected)
        .accessibilityAddTraits(selected ? .isSelected : [])
        .accessibilityLabel("\(choice.app), \(choice.title)")
    }
}

private struct AppIcon: View {
    let pid: pid_t?
    var body: some View {
        if let pid, let icon = NSRunningApplication(processIdentifier: pid)?.icon {
            Image(nsImage: icon).resizable().interpolation(.high)
        } else {
            RoundedRectangle(cornerRadius: 7).fill(Lens.sunken).overlay(Image(systemName: "macwindow").foregroundStyle(Lens.muted))
        }
    }
}

private struct PermissionBlock: View {
    @EnvironmentObject var model: AppModel
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label(model.screenAccess.title, systemImage: "macwindow").font(Lens.font(13.5, .heavy)).foregroundStyle(Lens.ink)
            Text(model.screenAccess.message)
                .font(Lens.font(12)).foregroundStyle(Lens.muted).fixedSize(horizontal: false, vertical: true)
            VStack(spacing: 8) {
                Button(model.checkingScreenAccess ? "Checking…" : "Check Access") { Task { await model.refresh(userInitiated: true) } }
                    .buttonStyle(.lens(.primary, height: 34, fullWidth: true)).disabled(model.checkingScreenAccess)
                Button("Open System Settings", action: Permissions.openScreenSettings)
                    .buttonStyle(.lens(.ghost, height: 34, fullWidth: true))
            }
            ScrollView { ScreenAccessDetails() }
                .frame(maxHeight: 220)
        }
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(Lens.warningFill))
    }
}

private struct RecordingPill: View {
    @EnvironmentObject var model: AppModel
    @Environment(\.accessibilityReduceMotion) private var reduce
    /// Set for a moment after each saved state, so people clicking quickly can see each capture land.
    @State private var happy = false
    @State private var hop = false
    @State private var calmDown: Task<Void, Never>?
    var body: some View {
        HStack(spacing: 12) {
            ZStack {
                Circle().fill(Lens.sky)
                MascotView(style: .peek, happy: happy).frame(width: 42, height: 42).offset(y: hop ? -1 : 6)
            }
            .frame(width: 38, height: 38)
            .clipShape(Circle())
            .scaleEffect(hop ? 1.08 : 1)
            .overlay(alignment: .topTrailing) {
                Image(systemName: "sparkle")
                    .font(.system(size: 11, weight: .black))
                    .foregroundStyle(Color(hex: 0xFFD66B))
                    .offset(x: 5, y: -4)
                    .scaleEffect(happy ? 1 : 0.4)
                    .opacity(happy ? 1 : 0)
                    .animation(reduce ? .easeOut(duration: 0.15) : .spring(duration: 0.3, bounce: 0), value: happy)
            }
            .onChange(of: model.session.frames.count) { old, new in
                if model.recording, new > old { cheer() }
            }
            .accessibilityElement()
            .accessibilityLabel(happy ? "State saved" : "Recording")
            HStack(spacing: 8) {
                RecordDot(size: 8, color: Color(hex: 0xFF6B70))
                TimelineView(.periodic(from: .now, by: 1)) { context in
                    Text(timerText(now: context.date)).font(Lens.font(14, .bold)).monospacedDigit()
                }
            }
            HStack(spacing: -12) {
                ForEach(model.session.frames.suffix(3)) { frame in
                    FrameThumbnail(frame: frame, root: model.root)
                        .frame(width: 30, height: 20)
                        .background(Color.white)
                        .clipShape(RoundedRectangle(cornerRadius: 4))
                        .overlay(RoundedRectangle(cornerRadius: 4).strokeBorder(Lens.navy, lineWidth: 1.5))
                        .transition(.lensPop(reduce))
                }
            }
            .animation(reduce ? nil : Motion.enter, value: model.session.frames.count)
            Text(model.session.frames.count == 1 ? "1 state" : "\(model.session.frames.count) states")
                .font(Lens.font(13)).monospacedDigit().foregroundStyle(Color(hex: 0xC9D3F0))
            Button(action: model.snapshot) {
                HStack(spacing: 6) { Text("Snapshot"); Text("⌘⇧S").font(Lens.mono(11)).opacity(0.7) }
            }
            .buttonStyle(.lens(.onDark, height: 36))
            .disabled(!model.recording)
            Button { Task { await model.stop() } } label: {
                HStack(spacing: 6) { Image(systemName: "stop.fill").font(.system(size: 10)); Text("Stop") }
            }
            .buttonStyle(.lens(.record, height: 36))
            // Keep the complete action and its padding in the intrinsically sized pill.
            .fixedSize(horizontal: true, vertical: false)
            .disabled(model.stopping)
        }
        .padding(.leading, 8).padding(.trailing, 9)
        .frame(height: 54)
        .foregroundStyle(.white)
        .background(Capsule().fill(Lens.navy))
        .padding(1)
    }

    /// A quick hop up and a smile. The face and sparkle are the cue; the hop is skipped under Reduce Motion.
    private func cheer() {
        happy = true
        if !reduce {
            withAnimation(Motion.ease(0.14)) { hop = true }
            withAnimation(.spring(duration: 0.38, bounce: 0.35).delay(0.14)) { hop = false }
        }
        calmDown?.cancel()
        calmDown = Task { @MainActor in
            try? await Task.sleep(nanoseconds: 900_000_000)
            if !Task.isCancelled { happy = false }
        }
    }

    private func timerText(now: Date) -> String {
        if model.stopping { return "Saving…" }
        guard let start = model.captureStartedAt else { return "Starting…" }
        return formatTimestamp(Int(now.timeIntervalSince(start) * 1000))
    }
}
