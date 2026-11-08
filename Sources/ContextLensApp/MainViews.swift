import SwiftUI
import AppKit
import ImageIO
import ContextLensCore
import ContextLensCapture
import ContextLensImaging

enum MainTab: String, CaseIterable, Identifiable {
    case review = "Review", markUp = "Mark Up", handOff = "Hand Off"
    var id: String { rawValue }
    var icon: String {
        switch self {
        case .review: return "square.grid.2x2"
        case .markUp: return "highlighter"
        case .handOff: return "paperplane"
        }
    }
}

/// Holds the main window so the capture panel can bring it forward.
@MainActor enum MainWindow {
    static weak var window: NSWindow?
    static func show() {
        NSApp.activate(ignoringOtherApps: true)
        window?.makeKeyAndOrderFront(nil)
    }
}

/// Blends the title bar into the canvas so the tab bar sits on one continuous surface.
struct WindowConfigurator: NSViewRepresentable {
    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        DispatchQueue.main.async { configure(view.window) }
        return view
    }
    func updateNSView(_ view: NSView, context: Context) { DispatchQueue.main.async { configure(view.window) } }
    private func configure(_ window: NSWindow?) {
        guard let window else { return }
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        window.titlebarSeparatorStyle = .none
        window.backgroundColor = Lens.canvasNS
        MainWindow.window = window
    }
}

struct ContentView: View {
    @EnvironmentObject var model: AppModel
    @AppStorage("onboardingComplete") private var onboarded = false
    @State private var showOnboarding = false
    @State private var showPrivacy = false
    @Environment(\.accessibilityReduceMotion) private var reduce

    var body: some View {
        VStack(spacing: 0) {
            Group {
                switch model.mainTab {
                case .review: ReviewView()
                case .markUp: MarkUpView()
                case .handOff: HandOffView()
                }
            }
            .id(model.mainTab)
            .transition(.opacity)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .disabled(model.busy || model.stopping)
            StatusBar()
        }
        .animation(reduce ? nil : Motion.quick, value: model.mainTab)
        .background(Lens.canvas)
        .foregroundStyle(Lens.ink)
        .toolbar {
            ToolbarItem(placement: .principal) {
                MainTabBar(selection: $model.mainTab, reviewCount: model.session.frames.count, markCount: model.issueCount, handedOff: model.exportURL != nil)
            }
            ToolbarItemGroup(placement: .primaryAction) {
                Button { CapturePanelController.shared.show() } label: {
                    HStack(spacing: 7) {
                        if model.recording { RecordDot() } else { Circle().fill(Lens.record).frame(width: 8, height: 8) }
                        Text(model.recording ? "Recording…" : "New capture")
                    }
                }
                .buttonStyle(.lens(.ghost, height: 30))
                .help("Open the capture panel (⌘N)")
                MoreMenu(showPrivacy: $showPrivacy, showOnboarding: $showOnboarding)
            }
        }
        .background(WindowConfigurator())
        .sheet(isPresented: $showOnboarding) {
            OnboardingView { onboarded = true; showOnboarding = false }.environmentObject(model)
        }
        .sheet(isPresented: $showPrivacy) { PrivacyView().environmentObject(model) }
        .alert("ContextLens", isPresented: Binding(get: { model.error != nil }, set: { if !$0 { model.error = nil } })) {
            Button("OK") { model.error = nil }
        } message: { Text(model.error ?? "") }
        .task {
            CapturePanelController.shared.attach(model: model, showMain: MainWindow.show)
            model.renderEditor()
            if !onboarded && !CommandLine.arguments.contains("--smoke-snapshot") { showOnboarding = true }
            await model.refresh()
            if CommandLine.arguments.contains("--capture-preview") { CapturePanelController.shared.show() }
        }
        .onReceive(NotificationCenter.default.publisher(for: NSApplication.didBecomeActiveNotification)) { _ in
            Task { await model.refresh() }
        }
    }
}

/// The three-step workflow island: the app's main navigation, so it gets the strongest surface in the toolbar.
struct MainTabBar: View {
    @Binding var selection: MainTab
    let reviewCount: Int
    let markCount: Int
    let handedOff: Bool
    @Namespace private var namespace
    @State private var hovered: MainTab?
    @Environment(\.accessibilityReduceMotion) private var reduce

    var body: some View {
        HStack(spacing: 2) {
            ForEach(Array(MainTab.allCases.enumerated()), id: \.element) { index, tab in
                if index > 0 {
                    Image(systemName: "chevron.compact.right")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundStyle(Lens.muted.opacity(0.5))
                        .accessibilityHidden(true)
                }
                tabButton(tab)
            }
        }
        .padding(4)
        .background(Capsule().fill(Lens.surface))
        .overlay(Capsule().strokeBorder(Lens.lineStrong, lineWidth: 1))
        // A faint top highlight gives the island a lifted, glassy edge.
        .overlay(Capsule().strokeBorder(LinearGradient(colors: [.white.opacity(0.12), .clear], startPoint: .top, endPoint: .center), lineWidth: 1).padding(1))
        .shadow(color: Lens.shadow, radius: 8, y: 3)
        .lineLimit(1)
        .fixedSize()
    }

    private func tabButton(_ tab: MainTab) -> some View {
        let on = tab == selection
        return Button {
            withAnimation(reduce ? nil : Motion.standard) { selection = tab }
        } label: {
            HStack(spacing: 7) {
                Image(systemName: tab.icon).font(.system(size: 12, weight: .bold))
                Text(tab.rawValue)
                badge(for: tab, on: on)
            }
            .font(Lens.font(13.5, .heavy))
            .foregroundStyle(on ? Lens.onAccent : (hovered == tab ? Lens.ink : Lens.muted))
            .padding(.horizontal, 15)
            .frame(height: 32)
            .background {
                if on {
                    Capsule()
                        .fill(LinearGradient(colors: [Lens.accentHover, Lens.accent], startPoint: .top, endPoint: .bottom))
                        .overlay(Capsule().strokeBorder(.white.opacity(0.22), lineWidth: 0.5))
                        .shadow(color: Lens.accent.opacity(0.35), radius: 8, y: 2)
                        .matchedGeometryEffect(id: "tab", in: namespace)
                } else if hovered == tab {
                    Capsule().fill(Lens.track)
                }
            }
            .contentShape(Capsule())
            .animation(.easeOut(duration: 0.15), value: hovered)
        }
        .buttonStyle(.plain)
        .onHover { hovered = $0 ? tab : (hovered == tab ? nil : hovered) }
        .accessibilityAddTraits(on ? .isSelected : [])
    }

    @ViewBuilder private func badge(for tab: MainTab, on: Bool) -> some View {
        let count = tab == .review ? reviewCount : tab == .markUp ? markCount : 0
        if count > 0 {
            Text("\(count)").font(Lens.font(11, .heavy)).monospacedDigit()
                .padding(.horizontal, 5).frame(minWidth: 18, minHeight: 18)
                .background(Capsule().fill(on ? Lens.onAccent : Lens.track))
                .foregroundStyle(on ? Lens.accent : Lens.ink)
        } else if tab == .handOff && handedOff {
            Image(systemName: "checkmark.circle.fill").font(.system(size: 13, weight: .bold))
                .foregroundStyle(on ? Lens.onAccent : Lens.success)
                .accessibilityLabel("Saved")
        }
    }
}

private struct MoreMenu: View {
    @EnvironmentObject var model: AppModel
    @Binding var showPrivacy: Bool
    @Binding var showOnboarding: Bool
    var body: some View {
        Menu {
            Button("Open Session…", action: model.openSession).disabled(model.recording || model.stopping || model.busy)
            Button("Import Screenshot…", action: model.importFrame).disabled(model.recording || model.stopping || model.busy)
            Divider()
            Button("Storage & Privacy…") { showPrivacy = true }
            Button("How it works") { showOnboarding = true }
        } label: {
            MascotView().frame(width: 28, height: 28)
        }
        .menuStyle(.button)
        .buttonStyle(.plain)
        .menuIndicator(.hidden)
        .fixedSize()
        .help("Sessions, storage, privacy and help")
        .accessibilityLabel("More")
    }
}

private struct StatusBar: View {
    @EnvironmentObject var model: AppModel
    var body: some View {
        HStack(spacing: 8) {
            Circle().fill(model.recording ? Lens.record : Lens.success).frame(width: 6, height: 6)
            Text(model.status).lineLimit(1)
            Spacer()
            if model.busy { ProgressView().controlSize(.mini) }
            Text("\(model.session.frames.count) \(model.session.frames.count == 1 ? "state" : "states") · \(model.issueCount) \(model.issueCount == 1 ? "mark" : "marks")")
                .font(Lens.mono(11)).monospacedDigit()
        }
        .font(Lens.font(11.5))
        .foregroundStyle(Lens.muted)
        .padding(.horizontal, 16)
        .frame(height: 28)
        .overlay(alignment: .top) { Rectangle().fill(Lens.line).frame(height: 1) }
    }
}

struct FrameThumbnail: View {
    let frame: Frame
    let root: URL?
    @EnvironmentObject var model: AppModel
    @State private var image: NSImage?
    private var imageKey: String { "\(root?.path ?? "")/\(frame.imagePath)#\(model.sourceRevision)" }
    var body: some View {
        Group {
            if let image { Image(nsImage: image).resizable().aspectRatio(contentMode: .fit) }
            else { Rectangle().fill(Lens.sunken).overlay(Image(systemName: "photo").foregroundStyle(Lens.muted)) }
        }
        .task(id: imageKey) {
            image = nil
            guard let root else { return }
            do {
                let url = try SessionStore.resolve(frame.imagePath, in: root)
                let cg = try await ImagePipeline.shared.thumbnail(at: url, revision: model.sourceRevision)
                guard !Task.isCancelled else { return }
                image = NSImage(cgImage: cg, size: .zero)
            } catch { /* A missing/corrupt thumbnail keeps its placeholder; full-image open reports errors. */ }
        }
        .onDisappear { image = nil }
    }
}

private struct EmptyState<Actions: View>: View {
    let title: String
    let message: String
    @ViewBuilder var actions: Actions
    var body: some View {
        VStack(spacing: 12) {
            MascotView(style: .peek).frame(width: 92, height: 92)
            Text(title).font(Lens.font(22, .heavy)).foregroundStyle(Lens.brandInk)
            Text(message).font(Lens.font(14)).foregroundStyle(Lens.muted).multilineTextAlignment(.center).frame(maxWidth: 380)
            HStack(spacing: 10) { actions }.padding(.top, 6)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: Review

struct ReviewView: View {
    @EnvironmentObject var model: AppModel
    @State private var deletedName: String?
    @State private var toastTask: Task<Void, Never>?
    /// The state shown full size; clicking a screenshot previews it instead of opening Mark Up.
    @State private var enlargedID: String? = CommandLine.arguments.firstIndex(of: "--preview").flatMap { i in
        CommandLine.arguments.indices.contains(i + 1) ? CommandLine.arguments[i + 1] : nil }
    @Environment(\.accessibilityReduceMotion) private var reduce

    private var markCounts: [String: Int] {
        model.session.annotations.filter { $0.kind != .redaction }.reduce(into: [:]) { $0[$1.frameID, default: 0] += 1 }
    }

    var body: some View {
        if model.session.frames.isEmpty {
            EmptyState(title: "No states yet", message: "Capture one window to record its states, or import a screenshot you already have.") {
                Button("New capture") { CapturePanelController.shared.show() }.buttonStyle(.lens(.primary, height: 38))
                Button("Import screenshot", action: model.importFrame).buttonStyle(.lens(.ghost, height: 38)).disabled(model.recording)
            }
        } else {
            content.disabled(model.recording)
                .overlay { Lightbox(frameID: $enlargedID) }
                .animation(reduce ? .easeOut(duration: 0.15) : Motion.standard, value: enlargedID == nil)
                .task {
                    // macOS focuses the first text field on appear; keep focus off the state names until clicked.
                    try? await Task.sleep(nanoseconds: 50_000_000)
                    if MainWindow.window?.firstResponder is NSTextView { MainWindow.window?.makeFirstResponder(nil) }
                }
        }
    }

    private var content: some View {
        let counts = markCounts
        let frames = model.session.frames
        return VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .bottom, spacing: 16) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(frames.first?.windowTitle ?? "Untitled session").font(Lens.font(26, .heavy)).foregroundStyle(Lens.brandInk).lineLimit(1)
                    Text(subtitle).font(Lens.font(13.5)).foregroundStyle(Lens.muted)
                }
                Spacer(minLength: 0)
            }
            Label("Untick the states you don’t need, then click one to mark it up.", systemImage: "checkmark.circle")
                .font(Lens.font(14, .bold)).foregroundStyle(Lens.muted)
            ScrollView {
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 250, maximum: 380), spacing: 18)], spacing: 18) {
                    ForEach(Array(frames.enumerated()), id: \.element.id) { index, frame in
                        ReviewCard(frame: frame, index: index, total: frames.count, marks: counts[frame.id, default: 0],
                                   onOpen: { enlargedID = frame.id }) {
                            delete(frame)
                        }
                        .transition(.lensPop(reduce))
                    }
                }
                .padding(.bottom, 28)
                .animation(reduce ? nil : Motion.standard, value: frames.map(\.id))
            }
        }
        .padding(.horizontal, 32)
        .padding(.top, 18)
        .overlay(alignment: .bottom) {
            if let deletedName {
                HStack(spacing: 14) {
                    Text("Deleted “\(deletedName)”").lineLimit(1)
                    Button("Undo") { model.undo(); dismissToast() }.buttonStyle(.lens(.onDark, height: 30))
                }
                .font(Lens.font(13.5, .bold))
                .foregroundStyle(.white)
                .padding(.leading, 16).padding(.trailing, 8)
                .frame(height: 46)
                .background(RoundedRectangle(cornerRadius: 14, style: .continuous).fill(Lens.navy))
                .shadow(color: .black.opacity(0.25), radius: 14, y: 8)
                .padding(.bottom, 18)
                .transition(.lensRise(reduce, distance: 12))
            }
        }
        .animation(reduce ? .easeOut(duration: 0.15) : Motion.enter, value: deletedName)
    }

    private var subtitle: String {
        var parts: [String] = []
        if let app = model.session.frames.first?.applicationName { parts.append(app) }
        parts.append(model.session.createdAt.formatted(date: .abbreviated, time: .shortened))
        parts.append(model.session.frames.count == 1 ? "1 state" : "\(model.session.frames.count) states")
        return parts.joined(separator: " · ")
    }

    private func delete(_ frame: Frame) {
        model.deleteFrame(frame.id)
        deletedName = frame.name
        toastTask?.cancel()
        toastTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: 5_000_000_000)
            if !Task.isCancelled { deletedName = nil }
        }
    }
    private func dismissToast() { toastTask?.cancel(); deletedName = nil }
}

/// Full-size preview of one state. Close with the × button, Esc or a click outside; ← → step through states.
private struct Lightbox: View {
    @EnvironmentObject var model: AppModel
    @Binding var frameID: String?
    @State private var image: NSImage?

    var body: some View {
        let frames = model.session.frames
        Group {
            if let id = frameID, let index = frames.firstIndex(where: { $0.id == id }) {
                let frame = frames[index]
                ZStack {
                    Rectangle().fill(Color(hex: 0x0A0E1F)).onTapGesture(perform: close)
                    VStack(spacing: 14) {
                        HStack(spacing: 12) {
                            Text(frame.name).font(Lens.font(17, .heavy)).foregroundStyle(.white).lineLimit(1)
                            Text("\(index + 1) of \(frames.count)").font(Lens.font(13)).monospacedDigit().foregroundStyle(.white.opacity(0.6))
                            Spacer()
                            Button(action: close) { Image(systemName: "xmark") }
                                .buttonStyle(LensIconButtonStyle(size: 36, raised: true))
                                .keyboardShortcut(.cancelAction)
                                .help("Close (Esc)").accessibilityLabel("Close preview")
                        }
                        HStack(spacing: 14) {
                            step(-1, index: index, frames: frames, icon: "chevron.left", key: .leftArrow)
                            Group {
                                if let image {
                                    Image(nsImage: image).resizable().interpolation(.high).scaledToFit()
                                        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                                        .shadow(color: .black.opacity(0.4), radius: 24, y: 10)
                                } else {
                                    ProgressView().controlSize(.small).tint(.white)
                                }
                            }
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                            step(1, index: index, frames: frames, icon: "chevron.right", key: .rightArrow)
                        }
                    }
                    .padding(28)
                }
                .transition(.opacity)
            }
        }
        .task(id: "\(model.root?.path ?? "")/\(frameID ?? "")#\(model.sourceRevision)") {
            image = nil
            guard let id = frameID, let root = model.root,
                  let frame = model.session.frames.first(where: { $0.id == id }) else { return }
            do {
                let cg = try await ImagePipeline.shared.render(EditorRenderRequest(source: root, revision: model.sourceRevision, frame: frame, annotations: []))
                guard !Task.isCancelled else { return }
                image = NSImage(cgImage: cg, size: .zero)
            } catch { if !Task.isCancelled { model.error = error.localizedDescription } }
        }
    }

    private func step(_ delta: Int, index: Int, frames: [Frame], icon: String, key: KeyEquivalent) -> some View {
        let target = index + delta
        return Button { if frames.indices.contains(target) { frameID = frames[target].id } } label: { Image(systemName: icon) }
            .buttonStyle(LensIconButtonStyle(size: 40, raised: true))
            .keyboardShortcut(key, modifiers: [])
            .disabled(!frames.indices.contains(target))
            .opacity(frames.indices.contains(target) ? 1 : 0.35)
            .accessibilityLabel(delta < 0 ? "Previous state" : "Next state")
    }
    private func close() { frameID = nil }

}

private struct ReviewCard: View {
    @EnvironmentObject var model: AppModel
    let frame: Frame
    let index: Int
    let total: Int
    let marks: Int
    var onOpen: () -> Void
    var onDelete: () -> Void
    @State private var name = ""
    @State private var hover = false
    @FocusState private var editing: Bool

    /// Plain words for the capture reason stored in the session ("visual_change" → "Changed").
    private var reasonLabel: String {
        switch frame.captureReason {
        case "initial": return "Start"
        case "manual": return "Snapshot"
        case "scroll": return "Scrolled"
        case "stop_flush": return "End"
        case "imported": return "Imported"
        default: return "Changed"
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Button(action: onOpen) {
                FrameThumbnail(frame: frame, root: model.root)
                    .frame(maxWidth: .infinity).frame(height: 168)
                    .background(Lens.sunken)
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .help("Enlarge")
            .accessibilityLabel("Enlarge \(frame.name)")
            .overlay(alignment: .topLeading) { pick.padding(8) }
            .overlay(alignment: .topTrailing) { if hover || editing { actions.padding(8) } }
            .padding(8)
            VStack(alignment: .leading, spacing: 4) {
                TextField("State name", text: $name)
                    .textFieldStyle(.plain)
                    .font(Lens.font(14.5, .heavy))
                    .focused($editing)
                    .onSubmit(commit)
                HStack(spacing: 6) {
                    Text(formatTimestamp(frame.timestampMS)).monospacedDigit()
                    Text("·")
                    Text(reasonLabel).lineLimit(1)
                    Spacer(minLength: 4)
                    if marks > 0 { MarkChip(count: marks) }
                }
                .frame(height: 20)
                .font(Lens.font(12.5))
                .foregroundStyle(Lens.muted)
            }
            .padding(.horizontal, 14).padding(.bottom, 14).padding(.top, 2)
        }
        .background(RoundedRectangle(cornerRadius: 18, style: .continuous).fill(Lens.surface))
        .overlay(RoundedRectangle(cornerRadius: 18, style: .continuous)
            .strokeBorder(frame.selected ? Lens.accent : Lens.line, lineWidth: frame.selected ? 2.5 : 1))
        .shadow(color: Lens.shadow, radius: hover ? 10 : 2, y: hover ? 5 : 1)
        .onHover { hover = $0 }
        .animation(.easeOut(duration: 0.15), value: hover)
        .help(frame.event ?? "")
        .onAppear { name = frame.name }
        .onChange(of: frame.name) { _, value in name = value }
        .onChange(of: editing) { _, focused in if !focused { commit() } }
    }

    private func commit() { if name != frame.name { model.renameFrame(frame.id, name: name) } }

    private var pick: some View {
        Button { model.toggleFrame(frame.id) } label: {
            ZStack {
                Circle().fill(frame.selected ? Lens.accent : Color.white.opacity(0.95))
                Circle().strokeBorder(frame.selected ? .clear : Lens.lineStrong, lineWidth: 1.5)
                Image(systemName: "checkmark").font(.system(size: 11, weight: .heavy)).foregroundStyle(Lens.onAccent).opacity(frame.selected ? 1 : 0)
            }
            .frame(width: 26, height: 26)
            .shadow(color: .black.opacity(0.12), radius: 2, y: 1)
            .contentShape(Circle())
        }
        .buttonStyle(.plain)
        .animation(.easeOut(duration: 0.15), value: frame.selected)
        .accessibilityLabel("Include \(frame.name) in hand-off")
        .accessibilityValue(frame.selected ? "Included" : "Not included")
    }

    private var actions: some View {
        HStack(spacing: 4) {
            Button { model.moveFrame(frame.id, by: -1) } label: { Image(systemName: "chevron.left") }
                .disabled(index == 0).accessibilityLabel("Move earlier")
            Button { model.moveFrame(frame.id, by: 1) } label: { Image(systemName: "chevron.right") }
                .disabled(index == total - 1).accessibilityLabel("Move later")
            Button(action: onDelete) { Image(systemName: "trash").foregroundStyle(Lens.danger) }
                .accessibilityLabel("Delete \(frame.name)")
        }
        .buttonStyle(LensIconButtonStyle(size: 28, raised: true))
    }
}

// MARK: Mark up

struct MarkUpView: View {
    @EnvironmentObject var model: AppModel
    var body: some View {
        if model.frame == nil {
            EmptyState(title: "Pick a state to mark up", message: "Tick the states you want in Review, then box or highlight what should change.") {
                Button("Go to Review") { model.mainTab = .review }.buttonStyle(.lens(.primary, height: 38))
            }
        } else {
            HStack(spacing: 0) {
                VStack(spacing: 0) {
                    MarkToolbar().padding(.vertical, 12)
                    ScreenshotCanvas()
                        .frame(minWidth: 420, maxWidth: .infinity, maxHeight: .infinity)
                        .padding(.horizontal, 28).padding(.bottom, 16)
                    Filmstrip()
                }
                MarksPanel().frame(width: 330)
            }
            .disabled(model.recording)
            .task {
                // macOS focuses the first note field on appear; stray typing would edit a mark.
                try? await Task.sleep(nanoseconds: 50_000_000)
                if MainWindow.window?.firstResponder is NSTextView { MainWindow.window?.makeFirstResponder(nil) }
            }
        }
    }
}

private struct MarkToolbar: View {
    @EnvironmentObject var model: AppModel
    var body: some View {
        HStack(spacing: 6) {
            LensSegments(selection: Binding(get: { model.tool }, set: { model.tool = $0 }), options: [
                SegmentOption(value: AnnotationKind.rectangle, title: "Box", icon: "rectangle.dashed"),
                SegmentOption(value: AnnotationKind.highlight, title: "Highlight", icon: "highlighter")
            ], filled: true, height: 30)
            .frame(width: 236)
            divider
            Button(action: model.undo) { Image(systemName: "arrow.uturn.backward") }
                .disabled(!model.canUndo).help("Undo (⌘Z)").accessibilityLabel("Undo")
            Button(action: model.redo) { Image(systemName: "arrow.uturn.forward") }
                .disabled(!model.canRedo).help("Redo (⇧⌘Z)").accessibilityLabel("Redo")
            divider
            // Both hints share one slot sized to the longer one, so switching tools never resizes the toolbar.
            ZStack {
                hint("Drag to box what should change").opacity(model.tool == .highlight ? 0 : 1)
                hint("Draw over text or controls").opacity(model.tool == .highlight ? 1 : 0)
            }
        }
        .buttonStyle(LensIconButtonStyle(size: 34))
        .padding(.horizontal, 6)
        .frame(height: 46)
        .fixedSize()
        .background(RoundedRectangle(cornerRadius: 15, style: .continuous).fill(Lens.surface))
        .overlay(RoundedRectangle(cornerRadius: 15, style: .continuous).strokeBorder(Lens.line, lineWidth: 1))
        .shadow(color: Lens.shadow, radius: 9, y: 4)
    }
    private func hint(_ text: String) -> some View {
        Text(text).font(Lens.font(12.5, .bold)).foregroundStyle(Lens.muted).padding(.horizontal, 6).lineLimit(1)
    }
    private var divider: some View { Rectangle().fill(Lens.line).frame(width: 1, height: 24) }
}

/// An invisible AppKit view laid exactly over the screenshot area. It turns event positions (window or screen
/// coordinates) into points inside that area, so zoom anchors don't depend on where the canvas sits in the window.
final class ViewportProbe {
    fileprivate(set) weak var view: NSView?
    /// The point under `screenPoint` in viewport coordinates (top-left origin), or nil when outside the screenshot area.
    func point(fromScreen screenPoint: NSPoint) -> CGPoint? {
        guard let view, let window = view.window else { return nil }
        let local = view.convert(window.convertPoint(fromScreen: screenPoint), from: nil)
        return view.bounds.contains(local) ? local : nil
    }
    func screenPoint(of event: NSEvent) -> NSPoint {
        // Events without a window (posted from a CGEvent) carry screen coordinates.
        event.window.map { $0.convertPoint(toScreen: event.locationInWindow) } ?? event.locationInWindow
    }
}
private final class FlippedProbeView: NSView {
    override var isFlipped: Bool { true }
    override func hitTest(_ point: NSPoint) -> NSView? { nil }
}
private struct ViewportProbeView: NSViewRepresentable {
    let probe: ViewportProbe
    func makeNSView(context: Context) -> NSView { let v = FlippedProbeView(); probe.view = v; return v }
    func updateNSView(_ nsView: NSView, context: Context) { probe.view = nsView }
}
/// Read by the `--exercise-zoom` test launch only.
@MainActor enum CanvasTestHook {
    static var probe: ViewportProbe?
    static var state = ZoomState()
    static var fit: CGSize = .zero
}

struct ScreenshotCanvas: View {
    @EnvironmentObject var model: AppModel
    @State private var points: [Point] = []
    @State private var cursorPushed = false
    // Test launches can open at a zoom level (`--zoom 2`).
    @State private var view = ZoomState(zoom: CommandLine.arguments.firstIndex(of: "--zoom").flatMap { i in
        CommandLine.arguments.indices.contains(i + 1) ? Double(CommandLine.arguments[i + 1]).map { CGFloat($0) } : nil } ?? 1)
    @State private var probe = ViewportProbe()
    @State private var viewport: CGSize = .zero
    @State private var fitSize: CGSize = .zero
    @State private var eventMonitor: Any?

    var body: some View {
        GeometryReader { geo in
            if let frame = model.frame, let image = model.editorImage {
                let fitScale = min(geo.size.width / CGFloat(frame.width), geo.size.height / CGFloat(frame.height))
                let fit = CGSize(width: CGFloat(frame.width) * fitScale, height: CGFloat(frame.height) * fitScale)
                let scale = fitScale * view.zoom
                let size = CGSize(width: fit.width * view.zoom, height: fit.height * view.zoom)
                // The zoomed screenshot is larger than the viewport. As an overlay it never sizes its parent, so it
                // stays pinned to the top-left and `offset` is exactly where ZoomState says it is.
                Color.clear
                    .frame(width: geo.size.width, height: geo.size.height)
                    .overlay(alignment: .topLeading) {
                        surface(frame: frame, image: image, size: size, scale: scale)
                            .offset(x: view.offset.x, y: view.offset.y)
                    }
                .background(ViewportProbeView(probe: probe))
                .clipped()
                .contentShape(Rectangle())
                .overlay(alignment: .bottomTrailing) {
                    if view.zoom > 1.01 {
                        Button { view.zoom(to: 1, at: center, content: fit, viewport: geo.size) } label: {
                            Text("\(Int((view.zoom * 100).rounded()))%").font(Lens.font(12, .bold)).monospacedDigit()
                                .padding(.horizontal, 10).frame(height: 26)
                                .background(.regularMaterial, in: Capsule())
                        }
                        .buttonStyle(.plain).padding(10)
                        .help("Fit to window (⌘0)")
                    }
                }
                .background {
                    // Keyboard zoom, centred on the pointer when it is over the screenshot.
                    Group {
                        Button("") { keyZoom(view.larger) }.keyboardShortcut("=", modifiers: .command)
                        Button("") { keyZoom(view.larger) }.keyboardShortcut("+", modifiers: .command)
                        Button("") { keyZoom(view.smaller) }.keyboardShortcut("-", modifiers: .command)
                        Button("") { keyZoom(1) }.keyboardShortcut("0", modifiers: .command)
                    }
                    .opacity(0).accessibilityHidden(true)
                }
                .onAppear { viewport = geo.size; fitSize = fit; view.clamp(content: fit, viewport: geo.size) }
                .onChange(of: geo.size) { _, size in viewport = size; fitSize = fit; view.clamp(content: fit, viewport: size) }
                .onChange(of: fit) { _, value in fitSize = value; view.clamp(content: value, viewport: geo.size) }
            }
        }
        .onChange(of: model.selectedFrameID) { _, _ in
            points = []; view = ZoomState(); view.clamp(content: fitSize, viewport: viewport)
        }
        .onChange(of: view) { _, value in CanvasTestHook.state = value; CanvasTestHook.fit = fitSize }
        .onAppear {
            installEventMonitor()
            CanvasTestHook.probe = probe
        }
        .onDisappear {
            if cursorPushed { NSCursor.pop(); cursorPushed = false }
            if let eventMonitor { NSEvent.removeMonitor(eventMonitor) }; eventMonitor = nil
        }
    }

    private var center: CGPoint { CGPoint(x: viewport.width / 2, y: viewport.height / 2) }
    private func keyZoom(_ target: CGFloat) {
        view.zoom(to: target, at: probe.point(fromScreen: NSEvent.mouseLocation) ?? center, content: fitSize, viewport: viewport)
    }
    /// Pinch and ⌘-scroll zoom at the pointer; two-finger scroll pans while zoomed in.
    private func installEventMonitor() {
        guard eventMonitor == nil else { return }
        eventMonitor = NSEvent.addLocalMonitorForEvents(matching: [.scrollWheel, .magnify]) { event in
            guard model.mainTab == .markUp, let window = probe.view?.window,
                  event.window == nil || event.window === window,
                  let anchor = probe.point(fromScreen: probe.screenPoint(of: event)) else { return event }
            if event.type == .magnify {
                view.zoom(to: view.zoom * (1 + event.magnification), at: anchor, content: fitSize, viewport: viewport)
                return nil
            }
            let step: CGFloat = event.hasPreciseScrollingDeltas ? 1 : 10
            if event.modifierFlags.contains(.command) {
                view.zoom(to: view.zoom * (1 + event.scrollingDeltaY * step * 0.01), at: anchor, content: fitSize, viewport: viewport)
                return nil
            }
            guard view.zoom > 1.01 else { return event }
            view.pan(by: CGSize(width: event.scrollingDeltaX * step, height: event.scrollingDeltaY * step), content: fitSize, viewport: viewport)
            return nil
        }
    }

    private func surface(frame: Frame, image: NSImage, size: CGSize, scale: CGFloat) -> some View {
        ZStack(alignment: .topLeading) {
            Image(nsImage: image).resizable().interpolation(.high).frame(width: size.width, height: size.height)
            Canvas { context, canvasSize in
                if model.tool == .highlight, let first = points.first {
                    var path = Path()
                    path.move(to: CGPoint(x: first.x * canvasSize.width, y: first.y * canvasSize.height))
                    for p in points.dropFirst() { path.addLine(to: CGPoint(x: p.x * canvasSize.width, y: p.y * canvasSize.height)) }
                    context.stroke(path, with: .color(Color(nsColor: .systemOrange).opacity(0.45)),
                                   style: StrokeStyle(lineWidth: AnnotationGeometry.highlightWidth(imageWidth: Double(frame.width)) * scale, lineCap: .round, lineJoin: .round))
                } else if let r = rectangleRegion(points) {
                    let rect = CGRect(x: r.x * canvasSize.width, y: r.y * canvasSize.height, width: r.width * canvasSize.width, height: r.height * canvasSize.height)
                    context.fill(Path(rect), with: .color(Lens.mark.opacity(0.06)))
                    context.stroke(Path(rect), with: .color(Lens.mark), style: StrokeStyle(lineWidth: 2, dash: [6, 4]))
                }
            }
            .allowsHitTesting(false)
            // Numbered badges match the marks list; they stay the same size at any zoom.
            ForEach(model.annotations.filter { $0.kind != .redaction }) { mark in
                MarkBadge(mark: mark, selected: model.selectedIssueID == mark.id, size: 20)
                    .position(x: min(size.width - 10, max(10, mark.region.x * size.width)),
                              y: min(size.height - 10, max(10, mark.region.y * size.height)))
                    .onTapGesture { model.selectedIssueID = mark.id }
            }
        }
        .frame(width: size.width, height: size.height)
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .shadow(color: Lens.shadow, radius: 18, y: 8)
        .contentShape(Rectangle())
        .gesture(DragGesture(minimumDistance: 2).onChanged { value in
            let start = normalized(value.startLocation, size: size), end = normalized(value.location, size: size)
            if points.isEmpty { points = [start] }
            if model.tool == .highlight { points.append(end) } else { points = [start, end] }
        }.onEnded { value in
            let end = normalized(value.location, size: size)
            if model.tool == .highlight {
                points.append(end)
                if let r = AnnotationGeometry.highlightBounds(points: points, imageWidth: Double(frame.width), imageHeight: Double(frame.height)) {
                    model.add(region: r, points: points)
                }
            } else if abs(value.translation.width) >= 3, abs(value.translation.height) >= 3 {
                points = [normalized(value.startLocation, size: size), end]
                if let r = rectangleRegion(points) { model.add(region: r, points: points) }
            }
            points = []
        })
        .onHover { inside in
            if inside && !cursorPushed { drawingCursor.push(); cursorPushed = true }
            else if !inside && cursorPushed { NSCursor.pop(); cursorPushed = false }
        }
    }
    var drawingCursor: NSCursor {
        if model.tool == .highlight, let image = NSImage(systemSymbolName: "highlighter", accessibilityDescription: "Highlighter")?.withSymbolConfiguration(.init(pointSize: 19, weight: .semibold)) {
            return NSCursor(image: image, hotSpot: NSPoint(x: 2, y: image.size.height - 2))
        }
        return .crosshair
    }
    func normalized(_ p: CGPoint, size: CGSize) -> Point { Point(x: min(1, max(0, p.x / size.width)), y: min(1, max(0, p.y / size.height))) }
    func rectangleRegion(_ p: [Point]) -> Region? {
        guard let x = p.map(\.x).min(), let y = p.map(\.y).min(), let right = p.map(\.x).max(), let bottom = p.map(\.y).max(), right > x, bottom > y else { return nil }
        return Region(x: x, y: y, width: right - x, height: bottom - y)
    }
}

/// How a mark is shown in the app: a number (matching CL-00N in the package) and its kind.
extension Annotation {
    var number: Int { Int(id.split(separator: "-").last ?? "") ?? 0 }
    var kindName: String {
        switch kind {
        case .rectangle: return "Box"
        case .highlight: return "Highlight"
        default: return kind.label
        }
    }
    var tint: Color { kind == .highlight ? Lens.highlightMark : Lens.mark }
}

struct MarkBadge: View {
    let mark: Annotation
    var selected = false
    var size: CGFloat = 22
    var body: some View {
        Text("\(mark.number)")
            .font(Lens.font(size * 0.52, .heavy)).monospacedDigit()
            .foregroundStyle(.white)
            .frame(minWidth: size, minHeight: size)
            .padding(.horizontal, mark.number > 9 ? 3 : 0)
            .background(Capsule().fill(selected ? Lens.navy : mark.tint))
            .overlay(Capsule().strokeBorder(.white, lineWidth: 1.5))
            .shadow(color: .black.opacity(0.25), radius: 2, y: 1)
            .accessibilityLabel("Mark \(mark.number)")
    }
}

private struct Filmstrip: View {
    @EnvironmentObject var model: AppModel
    var body: some View {
        let counts = model.session.annotations.filter { $0.kind != .redaction }.reduce(into: [String: Int]()) { $0[$1.frameID, default: 0] += 1 }
        ScrollView(.horizontal, showsIndicators: false) {
            LazyHStack(spacing: 10) {
                // Review's ticks choose what to mark up; the open state stays visible even if unticked.
                ForEach(model.session.frames.filter { $0.selected || $0.id == model.selectedFrameID }) { frame in
                    let current = model.selectedFrameID == frame.id
                    Button { model.select(frame.id) } label: {
                        VStack(alignment: .leading, spacing: 4) {
                            FrameThumbnail(frame: frame, root: model.root)
                                .frame(width: 104, height: 58)
                                .background(Lens.sunken)
                                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                                .overlay(RoundedRectangle(cornerRadius: 8, style: .continuous)
                                    .strokeBorder(current ? Lens.accent : Lens.line, lineWidth: current ? 2.5 : 1))
                                .overlay(alignment: .topTrailing) {
                                    if let n = counts[frame.id], n > 0 {
                                        Text("\(n)").font(Lens.font(10.5, .heavy)).foregroundStyle(.white)
                                            .frame(width: 18, height: 18).background(Circle().fill(Lens.mark)).padding(4)
                                    }
                                }
                            Text(frame.name).font(Lens.font(11, .bold)).foregroundStyle(current ? Lens.accent : Lens.muted).lineLimit(1)
                        }
                        .frame(width: 104)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .animation(.easeOut(duration: 0.15), value: current)
                    .accessibilityAddTraits(current ? .isSelected : [])
                }
            }
            .padding(.horizontal, 24).padding(.vertical, 12)
        }
        .frame(height: 100)
        .overlay(alignment: .top) { Rectangle().fill(Lens.line).frame(height: 1) }
    }
}

private struct MarksPanel: View {
    @EnvironmentObject var model: AppModel
    @Environment(\.accessibilityReduceMotion) private var reduce
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text(model.frame?.name ?? "").font(Lens.font(17, .heavy)).foregroundStyle(Lens.brandInk).lineLimit(1)
                let n = model.annotations.filter { $0.kind != .redaction }.count
                Text(n == 1 ? "1 mark" : "\(n) marks").font(Lens.font(12.5)).foregroundStyle(Lens.muted)
            }
            .padding(18)
            ScrollView {
                VStack(spacing: 10) {
                    ForEach(model.annotations) { annotation in
                        MarkCard(annotation: annotation).id(annotation.id).transition(.lensPop(reduce))
                    }
                    if model.annotations.isEmpty {
                        VStack(spacing: 10) {
                            MascotView(style: .peek).frame(width: 64, height: 64)
                            Text("Drag on the screenshot to mark what should change.")
                                .font(Lens.font(13.5)).foregroundStyle(Lens.muted).multilineTextAlignment(.center)
                        }
                        .padding(.vertical, 36).padding(.horizontal, 10)
                    }
                }
                .padding(.horizontal, 18).padding(.bottom, 12)
                .animation(reduce ? nil : Motion.quick, value: model.annotations.map(\.id))
            }
            VStack(alignment: .leading, spacing: 10) {
                Button("Continue to Hand Off") { model.mainTab = .handOff }.buttonStyle(.lens(.primary, height: 38, fullWidth: true))
            }
            .padding(18)
            .overlay(alignment: .top) { Rectangle().fill(Lens.line).frame(height: 1) }
        }
        .background(Lens.surface)
        .overlay(alignment: .leading) { Rectangle().fill(Lens.line).frame(width: 1) }
    }
}

private struct MarkCard: View {
    @EnvironmentObject var model: AppModel
    let annotation: Annotation
    @State private var text = ""
    @FocusState private var focused: Bool

    private var selected: Bool { model.selectedIssueID == annotation.id }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Button { model.selectedIssueID = annotation.id } label: {
                    HStack(spacing: 8) {
                        MarkBadge(mark: annotation, selected: selected)
                        Text(annotation.kindName).font(Lens.font(13, .heavy)).foregroundStyle(Lens.ink).lineLimit(1)
                    }
                    .contentShape(Rectangle())
                    .help("\(annotation.id) in the hand off")
                }
                .buttonStyle(.plain)
                Spacer()
                Button(role: .destructive) { model.removeIssue(annotation.id) } label: { Image(systemName: "trash") }
                    .buttonStyle(LensIconButtonStyle(size: 28)).accessibilityLabel("Delete mark \(annotation.number)")
            }
            if annotation.kind == .redaction {
                Text("Hidden in every export").font(Lens.font(12)).foregroundStyle(Lens.muted)
            } else {
                TextField("What should change?", text: $text, axis: .vertical)
                    .lineLimit(2...6)
                    .textFieldStyle(.plain)
                    .font(.system(size: 13.5))
                    .padding(.horizontal, 10).padding(.vertical, 8)
                    .background(RoundedRectangle(cornerRadius: 10, style: .continuous).fill(Lens.surface))
                    .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous).strokeBorder(focused ? Lens.accent : Lens.lineStrong, lineWidth: focused ? 1.5 : 1))
                    .focused($focused)
                    .onChange(of: text) { _, value in model.editIssue(annotation.id, text: value) }
            }
        }
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 14, style: .continuous).fill(selected ? Lens.surface : Lens.canvas))
        .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous)
            .strokeBorder(selected ? Lens.accent : Lens.line, lineWidth: selected ? 2 : 1))
        .animation(.easeOut(duration: 0.15), value: selected)
        .onAppear {
            sync()
            if selected && text.isEmpty && annotation.kind != .redaction { focused = true }
        }
        .onChange(of: annotation) { _, _ in sync() }
        .onChange(of: focused) { _, isFocused in if isFocused { model.selectedIssueID = annotation.id } }
    }

    private func sync() {
        if text != annotation.instruction { text = annotation.instruction }
    }
}

// MARK: Hand off

struct HandOffView: View {
    @EnvironmentObject var model: AppModel
    @State private var copied: String?
    @State private var copyReset: Task<Void, Never>?
    @State private var hadExport = false
    @Environment(\.accessibilityReduceMotion) private var reduce

    var body: some View {
        HStack(spacing: 0) {
            ScrollView { settings.padding(26) }
                .frame(width: 410)
                .background(Lens.surface)
                .overlay(alignment: .trailing) { Rectangle().fill(Lens.line).frame(width: 1) }
            preview
        }
        .task(id: model.exportPreviewKey) { await model.refreshExportPreview() }
        .onChange(of: model.exportURL) { _, url in if url != nil { hadExport = true } }
        .onAppear { if model.exportURL != nil { hadExport = true } }
    }

    private var plan: ExportPlan? { model.currentExportPlan }

    private var settings: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text("Hand Off").font(Lens.font(24, .heavy)).foregroundStyle(Lens.brandInk)
            Toggle(isOn: $model.exportOptions.annotatedOnly) {
                optionLabel("Only marked states", nil)
            }
            .toggleStyle(LensSwitchStyle())
            Toggle(isOn: $model.exportOptions.excludeDuplicates) {
                optionLabel("Skip repeated states", "Marked states are always kept.")
            }
            .toggleStyle(LensSwitchStyle())
            VStack(alignment: .leading, spacing: 6) {
                Text("Task").font(Lens.font(14, .heavy)) + Text("  (optional)").font(Lens.font(13)).foregroundColor(Lens.muted)
                TextField("What should the agent do?",
                          text: Binding(get: { model.session.task ?? "" }, set: model.editTask), axis: .vertical)
                    .lineLimit(2...4)
                    .textFieldStyle(.plain)
                    .font(.system(size: 13.5))
                    .padding(.horizontal, 12).padding(.vertical, 10)
                    .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(Lens.surface))
                    .overlay(RoundedRectangle(cornerRadius: 12, style: .continuous).strokeBorder(Lens.lineStrong, lineWidth: 1))
            }
            summary
            if hadExport && model.exportURL == nil {
                Text("Settings changed. Save the hand off again.")
                    .font(Lens.font(12.5, .bold)).foregroundStyle(Lens.warning)
                    .padding(10).frame(maxWidth: .infinity, alignment: .leading)
                    .background(RoundedRectangle(cornerRadius: 10, style: .continuous).fill(Lens.warningFill))
            }
            if let url = model.exportURL {
                ready(url).transition(.lensRise(reduce, distance: 6))
            } else {
                Button { Task { await model.exportSession() } } label: {
                    HStack(spacing: 8) {
                        if model.busy { ProgressView().controlSize(.small).tint(Lens.onAccent); Text("Saving…") }
                        else { Text("Save Hand Off") }
                    }
                }
                .buttonStyle(.lens(.primary, height: 44, fullWidth: true))
                .disabled(plan?.session.frames.isEmpty != false || model.recording || model.busy)
            }
        }
        .animation(reduce ? .easeOut(duration: 0.15) : Motion.enter, value: model.exportURL)
    }

    private func optionLabel(_ title: String, _ detail: String?) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title).font(Lens.font(14, .heavy)).foregroundStyle(Lens.ink)
            if let detail {
                Text(detail).font(Lens.font(12.5)).foregroundStyle(Lens.muted).fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    @ViewBuilder private var summary: some View {
        if model.exportPreviewLoading && plan == nil {
            HStack(spacing: 8) { ProgressView().controlSize(.small); Text("Preparing preview…").font(Lens.font(12.5)).foregroundStyle(Lens.muted) }
        }
        if let message = model.exportPreviewError {
            Text(message).font(Lens.font(12.5)).foregroundStyle(Lens.warning)
        }
        if let plan {
            let s = plan.summary
            HStack(spacing: 28) {
                metric("\(s.includedFrames)", "States")
                metric("\(s.includedAnnotations)", "Marks")
            }
            .contentTransition(.numericText())
            .animation(reduce ? nil : Motion.standard, value: s.includedFrames)
            VStack(alignment: .leading, spacing: 4) {
                Text(leftOut(s)).font(Lens.font(12.5)).foregroundStyle(Lens.muted)
                if s.unlabelledAnnotations > 0 {
                    Text(s.unlabelledAnnotations == 1 ? "1 mark has no note, so it's sent as a reference only."
                         : "\(s.unlabelledAnnotations) marks have no note, so they're sent as references only.")
                        .font(Lens.font(12.5)).foregroundStyle(Lens.warning)
                }
                if plan.session.frames.isEmpty {
                    Text("No states match. Mark a state or turn off “Only marked states”.")
                        .font(Lens.font(12.5, .bold)).foregroundStyle(Lens.warning)
                }
            }
        }
    }

    private func leftOut(_ s: ExportSummary) -> String {
        var parts: [String] = []
        if s.excludedUnannotated > 0 { parts.append("\(s.excludedUnannotated) unmarked left out") }
        if s.excludedDuplicates > 0 { parts.append("\(s.excludedDuplicates) repeated skipped") }
        let unticked = model.session.frames.count - s.selectedFrames
        if unticked > 0 { parts.append("\(unticked) not ticked") }
        parts.append(ByteCountFormatter.string(fromByteCount: s.estimatedSourceBytes, countStyle: .file))
        return parts.joined(separator: " · ")
    }

    private func metric(_ value: String, _ label: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(value).font(Lens.font(40, .heavy)).monospacedDigit().foregroundStyle(Lens.brandInk)
            SectionLabel(label)
        }
    }

    private func ready(_ url: URL) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 10) {
                MascotView().frame(width: 34, height: 34)
                VStack(alignment: .leading, spacing: 2) {
                    Text("Hand off saved").font(Lens.font(14.5, .heavy)).foregroundStyle(Lens.brandInk)
                    Text((url.path as NSString).abbreviatingWithTildeInPath).font(Lens.mono(11)).foregroundStyle(Lens.muted)
                        .lineLimit(2).truncationMode(.middle).textSelection(.enabled)
                }
            }
            Button { copy("prompt") { model.copyPrompt() } } label: {
                HStack(spacing: 8) {
                    SwapIcon(from: "doc.on.doc", to: "checkmark", swapped: copied == "prompt")
                    Text(copied == "prompt" ? "Copied" : "Copy prompt")
                }
            }
            .buttonStyle(.lens(.primary, height: 42, fullWidth: true))
            HStack(spacing: 8) {
                Button("Show in Finder") { NSWorkspace.shared.activateFileViewerSelecting([url]) }
                    .buttonStyle(.lens(.ghost, height: 36, fullWidth: true))
                Button {
                    copy("path") { NSPasteboard.general.clearContents(); NSPasteboard.general.setString(url.path, forType: .string) }
                } label: {
                    HStack(spacing: 7) {
                        SwapIcon(from: "folder", to: "checkmark", swapped: copied == "path")
                        Text(copied == "path" ? "Copied" : "Copy path")
                    }
                }
                .buttonStyle(.lens(.ghost, height: 36, fullWidth: true))
            }
            Text("Paste into any coding agent.").font(Lens.font(12)).foregroundStyle(Lens.muted)
        }
        .padding(14)
        .lensCard()
        .shadow(color: Lens.shadow, radius: 10, y: 4)
    }

    private func copy(_ key: String, _ action: () -> Void) {
        action()
        copied = key
        copyReset?.cancel()
        copyReset = Task { @MainActor in
            try? await Task.sleep(nanoseconds: 1_800_000_000)
            if !Task.isCancelled { copied = nil }
        }
    }

    private var preview: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionLabel("In this package")
            ScrollView(.horizontal, showsIndicators: false) {
                LazyHStack(spacing: 12) {
                    if let plan {
                        let counts = plan.session.annotations.filter { $0.kind != .redaction }.reduce(into: [String: Int]()) { $0[$1.frameID, default: 0] += 1 }
                        ForEach(plan.session.frames) { frame in
                            VStack(alignment: .leading, spacing: 5) {
                                FrameThumbnail(frame: frame, root: model.root)
                                    .frame(width: 132, height: 76)
                                    .background(Lens.sunken)
                                    .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
                                    .overlay(RoundedRectangle(cornerRadius: 9, style: .continuous).strokeBorder(Lens.line, lineWidth: 1))
                                Text(frame.name).font(Lens.font(12, .heavy)).lineLimit(1)
                                let n = counts[frame.id, default: 0]
                                Text("\(formatTimestamp(frame.timestampMS)) · \(n == 0 ? "no marks" : n == 1 ? "1 mark" : "\(n) marks")")
                                    .font(Lens.font(11)).monospacedDigit().foregroundStyle(Lens.muted)
                            }
                            .frame(width: 132)
                            .transition(.lensPop(reduce))
                        }
                    }
                }
                .animation(reduce ? nil : Motion.standard, value: plan?.session.frames.map(\.id) ?? [])
            }
            .frame(height: 118)
            SectionLabel("context.md preview").padding(.top, 4)
            ScrollView {
                Text(plan.map { ContextReport.markdown($0.session, summary: $0.summary) } ?? "Your filtered report preview will appear here.")
                    .font(Lens.mono(12))
                    .lineSpacing(3)
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(18)
            }
            .lensCard(radius: 14)
        }
        .padding(24)
    }
}
