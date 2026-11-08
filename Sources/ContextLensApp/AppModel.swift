import SwiftUI
import os
import AppKit
import ScreenCaptureKit
import ApplicationServices
import ContextLensCore
import ContextLensImaging
import ContextLensCapture

@MainActor final class AppModel: ObservableObject {
    @Published var session = Session()
    @Published var root: URL?
    @Published var windows: [WindowChoice] = []
    @Published var windowID: CGWindowID?
    @Published var selectedFrameID: String?
    @Published var selectedIssueID: String?
    @Published var recording = false
    @Published var stopping = false
    @Published var busy = false
    @Published var error: String? { didSet { if error != nil { log.error("Operation failed; details shown only in the app") } } }
    @Published var status = "Choose a window to begin."
    @Published var sensitivity: Sensitivity = .high
    @Published var deduplicate = true
    @Published var maximumFrames = 100
    @Published var delaySeconds = 0
    @Published var tool: AnnotationKind = .rectangle
    @Published var mainTab: MainTab = .review {
        // Opening Mark up with nothing selected starts on the first ticked state instead of an empty screen.
        didSet { if mainTab == .markUp, frame == nil { select(FrameSelection.resolve(selectedFrameID, in: session, preferIncluded: true)) } }
    }
    /// Set once sampling begins (after any start delay); drives the recording timer.
    @Published var captureStartedAt: Date?
    /// Latest global frame of the captured window, used for the desktop highlight.
    @Published var targetFrame: CGRect?
    /// True after a capture ends with saved states, until the person moves on.
    @Published var exportURL: URL?
    @Published var exportOptions = ExportOptions() { didSet { exportURL = nil } }
    @Published private(set) var sourceRevision = 0
    @Published var exportPlan: ExportPlan?
    @Published var exportPreviewLoading = false
    @Published var exportPreviewError: String?
    @Published var preview: NSImage?
    @Published var editorImage: NSImage?
    @Published var screenPermission = false
    @Published var checkingScreenAccess = false
    @Published var screenAccessError: String?
    private var screenAccessVerified = false
    @Published var axPermission = Permissions.accessibility
    @Published var storageBase = UserDefaults.standard.string(forKey: "storagePath").map { URL(fileURLWithPath: $0) } ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("ContextLens/Sessions") {
        didSet { UserDefaults.standard.set(storageBase.path, forKey: "storagePath") }
    }
    @Published var retentionDays = UserDefaults.standard.object(forKey: "retentionDays") as? Int ?? 30 { didSet { UserDefaults.standard.set(retentionDays, forKey: "retentionDays") } }
    private var history = SessionHistory()
    private let log = Logger(subsystem: "dev.contextlens.app", category: "App")
    private var editorTask: Task<Void, Never>?
    private var editorRequest: EditorRenderRequest?
    private var captureTask: Task<Void, Never>?
    private var eventMonitor: Any?
    private var scrollMonitor: Any?
    /// Last scroll over the captured window, in seconds of system uptime; nil when not scrolling yet.
    private var scrollActivity = ScrollActivity()
    private var pendingScroll: (time: TimeInterval, point: CGPoint)?
    private var hotKey: SnapshotHotKey?
    private var pendingEvent: String?
    private var pendingLabel: String?
    private var manual = false
    private var targetBounds: CGRect = .zero
    private var targetProcessID: pid_t?
    private var targetWindowID: CGWindowID?
    private var startedAt = Date()
    private var processor: CaptureProcessor?
    var frame: Frame? { session.frames.first { $0.id == selectedFrameID } }
    var annotations: [Annotation] { session.annotations.filter { $0.frameID == selectedFrameID } }
    var canUndo: Bool { history.canUndo }
    var canRedo: Bool { history.canRedo }
    var selectedCount: Int { session.frames.filter(\.selected).count }
    var issueCount: Int {
        let included = Set(session.frames.filter(\.selected).map(\.id))
        return session.annotations.filter { $0.kind != .redaction && included.contains($0.frameID) }.count
    }
    init() {
        let args = CommandLine.arguments
        if let i = args.firstIndex(of: "--session"), args.indices.contains(i+1) {
            let folder = URL(fileURLWithPath: args[i+1])
            do { session = try SessionStore.load(from: folder); root = folder; selectedFrameID = session.frames.last?.id; mainTab = .markUp; status = "Session opened." }
            catch { self.error = error.localizedDescription }
        }
        // Test launches can open a specific state (`--frame frame-002`).
        if let i = args.firstIndex(of: "--frame"), args.indices.contains(i+1), session.frames.contains(where: { $0.id == args[i+1] }) {
            selectedFrameID = args[i+1]
        }
        if args.contains("--export-preview") { mainTab = .handOff }
        if let i = args.firstIndex(of: "--tab"), args.indices.contains(i+1),
           let tab = MainTab.allCases.first(where: { $0.rawValue.lowercased().replacingOccurrences(of: " ", with: "-") == args[i+1].lowercased() }) {
            mainTab = tab
        }
    }
    func refresh(userInitiated: Bool = false) async {
        guard !recording, !stopping, !checkingScreenAccess else { return }
        checkingScreenAccess = true
        defer { checkingScreenAccess = false }
        axPermission = Permissions.accessibility
        do {
            guard let available = try await ScreenAccessProbe.windows(preflightGranted: Permissions.screenRecording,
                                                                      userInitiated: userInitiated, previouslyVerified: screenAccessVerified) else {
                screenPermission = false; windows = []; windowID = nil; preview = nil
                status = "Screen capture access has not been verified. Choose Check Access."
                return
            }
            screenAccessVerified = true; screenPermission = true; screenAccessError = nil; windows = available
            if !available.contains(where: { $0.id == windowID }) { windowID = nil; preview = nil }
            if available.isEmpty { status = "Access verified. Open an application window, then refresh." }
            else if !userInitiated { if session.frames.isEmpty { status = "Choose a window to begin." } }
            else { status = "Screen capture access verified. Select a window to capture." }
        } catch {
            screenAccessVerified = false; screenPermission = false; windows = []; windowID = nil; preview = nil
            screenAccessError = error.localizedDescription
            status = "macOS could not verify screen capture access. If Settings is enabled, reopen this build and check again."
        }
    }
    func showPreview() async {
        guard !recording, let w = windows.first(where: { $0.id == windowID }) else { return }
        do { let (img, _) = try await WindowCapture.image(window: w.window); preview = NSImage(cgImage: img, size: .zero) }
        catch { self.error = error.localizedDescription }
    }
    func start() async {
        guard !recording, !stopping, let chosen = windows.first(where: { $0.id == windowID }), let pid = chosen.window.owningApplication?.processID else { return }
        do {
            // Persist the previous session before replacing it.
            if root != nil { try save() }
            session = Session(); root = storageBase.appendingPathComponent(session.id)
            try save(); history.reset(); selectedFrameID = nil; editorImage = nil; exportURL = nil
            var selector = FrameSelector(); selector.sensitivity = sensitivity; selector.deduplicate = deduplicate; selector.maximumFrames = maximumFrames
            let worker = CaptureProcessor(root: root!, selector: selector); processor = worker
            recording = true; status = delaySeconds > 0 ? "Capture starts in \(delaySeconds) seconds…" : "Recording selected window"
            captureStartedAt = nil; targetFrame = chosen.window.frame
            manual = false; pendingEvent = nil; pendingLabel = nil; scrollActivity = ScrollActivity(); pendingScroll = nil; targetBounds = chosen.window.frame; targetProcessID = pid; targetWindowID = chosen.id
            let targetID = chosen.id, delay = delaySeconds
            captureTask = Task {
                if delay > 0 { try? await Task.sleep(nanoseconds: UInt64(delay) * 1_000_000_000) }
                if recording && !Task.isCancelled { startedAt = Date(); captureStartedAt = startedAt }
                if recording { installEventMonitors() }
                while recording {
                    do {
                        let available = try await WindowCapture.windows()
                        let current = try WindowCapture.selected(id: targetID, pid: pid, in: available)
                        targetBounds = current.window.frame
                        if targetFrame != current.window.frame { targetFrame = current.window.frame }
                        let (img, scale) = try await WindowCapture.image(window: current.window)
                        let now = Int(Date().timeIntervalSince(startedAt) * 1000)
                        try Task.checkCancellation()
                        let requestManual = manual; manual = false
                        // Momentum scrolling sends events too, so 0.5 s of quiet means the scroll has ended.
                        updateScrollActivity()
                        let scrolling = scrollActivity.holding(at: ProcessInfo.processInfo.systemUptime)
                        if let f = try await worker.process(image: img, at: now, scale: scale, title: current.window.title, app: current.app, event: pendingEvent, manual: requestManual, holding: scrolling) {
                            try append(named(f, clickedLabel: pendingLabel)); pendingEvent = nil; pendingLabel = nil
                        }
                        status = "Recording \(current.app) · \(session.frames.count) states · ⌘⇧S snapshot"
                        if session.frames.count >= maximumFrames { stopping = true; recording = false; status = "Maximum frame count reached." }
                        try await Task.sleep(nanoseconds: 250_000_000)
                    } catch { if !(error is CancellationError) { self.error = error.localizedDescription }; recording = false }
                }
                stopping = true
                removeEventMonitors()
                do { if let f = try await worker.flush() { try append(named(f, clickedLabel: nil)) }; try save() }
                catch { self.error = error.localizedDescription }
                recording = false; stopping = false; captureStartedAt = nil
                mainTab = .review
                status = "\(Self.count(session.frames.count, "state")) saved locally. Review and annotate."
                if selectedFrameID == nil { select(session.frames.first?.id) }
            }
        } catch { self.error = error.localizedDescription; recording = false }
    }
    func stop() async { guard recording || stopping else { return }; stopping = true; recording = false; captureTask?.cancel(); await captureTask?.value }
    func snapshot() { if recording { manual = true; status = "Manual snapshot queued" } }
    private func append(_ f: Frame) throws { session.frames.append(f); try save() }
    /// Replaces the processor's counter name with one that says what happened.
    private func named(_ f: Frame, clickedLabel: String?) -> Frame {
        var f = f
        f.name = StateNamer.name(sequence: session.frames.count + 1, reason: f.captureReason, windowTitle: f.windowTitle,
                                 previousTitle: session.frames.last?.windowTitle, clickedLabel: clickedLabel)
        return f
    }
    private func installEventMonitors() {
        eventMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.leftMouseUp, .rightMouseUp]) { [weak self] _ in
            Task { @MainActor in self?.mouseEvent() }
        }
        // Only a timestamp is recorded per scroll event; the capture loop reads it on its next tick.
        scrollMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.scrollWheel]) { [weak self] _ in
            Task { @MainActor in self?.scrollEvent() }
        }
        hotKey = SnapshotHotKey { [weak self] in Task { @MainActor in self?.snapshot() } }
        hotKey?.register()
    }
    private func removeEventMonitors() {
        if let eventMonitor { NSEvent.removeMonitor(eventMonitor) }; eventMonitor = nil
        if let scrollMonitor { NSEvent.removeMonitor(scrollMonitor) }; scrollMonitor = nil
        hotKey?.unregister(); hotKey = nil
    }
    /// macOS scrolls the window under the pointer even when it is in the background, so only the position is checked.
    private func scrollEvent() {
        guard recording, let p = CGEvent(source: nil)?.location, targetBounds.contains(p) else { return }
        pendingScroll = (ProcessInfo.processInfo.systemUptime, p)
    }
    private func updateScrollActivity() {
        guard let pending = pendingScroll, let targetWindowID else { return }
        pendingScroll = nil
        guard ProcessInfo.processInfo.systemUptime - pending.time < 0.5 else { return }
        let p = pending.point
        // Resolve occlusion once per sampling tick, never once per high-frequency wheel event.
        let topWindow = (CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]])?.first { info in
            guard (info[kCGWindowLayer as String] as? Int) == 0,
                  let bounds = info[kCGWindowBounds as String] as? [String: Any],
                  let rect = CGRect(dictionaryRepresentation: bounds as CFDictionary) else { return false }
            return rect.contains(p)
        }
        scrollActivity.observe(at: pending.time, targetWindowID: targetWindowID,
                               windowUnderPointer: (topWindow?[kCGWindowNumber as String] as? NSNumber)?.uint32Value)
    }
    private func mouseEvent() {
        guard recording, let p = CGEvent(source: nil)?.location, targetBounds.contains(p),
              NSWorkspace.shared.frontmostApplication?.processIdentifier == targetProcessID else { return }
        // A click over another window must not be attributed to the selected window.
        guard let info = CGWindowListCopyWindowInfo(.optionOnScreenOnly, kCGNullWindowID) as? [[String: Any]],
              let front = info.first(where: { item in
                  guard let layer = item[kCGWindowLayer as String] as? Int, layer == 0,
                        let bounds = item[kCGWindowBounds as String] as? [String: Any],
                        let rect = CGRect(dictionaryRepresentation: bounds as CFDictionary) else { return false }
                  return rect.contains(p)
              }), let number = front[kCGWindowNumber as String] as? UInt32, number == targetWindowID else { return }
        let ms = Int(Date().timeIntervalSince(startedAt)*1000)
        var caption = "mouse release at \(ms) ms"
        var label: String?
        if Permissions.accessibility {
            var element: AXUIElement?
            if AXUIElementCopyElementAtPosition(AXUIElementCreateSystemWide(), Float(p.x), Float(p.y), &element) == .success, let element {
                let role = Self.axString(element, kAXRoleAttribute)
                label = Self.controlLabel(element)
                if let role { caption += label.map { " (\(role) “\($0)”)" } ?? " (\(role))" }
            }
        }
        pendingEvent = caption; pendingLabel = label
    }
    private static func axString(_ element: AXUIElement, _ attribute: String) -> String? {
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, attribute as CFString, &value) == .success else { return nil }
        return (value as? String).flatMap { $0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? nil : $0 }
    }
    /// The visible label of the clicked control, looking up two parents for a button's text.
    /// Never reads the value of editable fields, so typed text stays out of state names.
    private static func controlLabel(_ start: AXUIElement) -> String? {
        let editable: Set<String> = ["AXTextField", "AXTextArea", "AXComboBox", "AXSearchField", "AXSecureTextField"]
        var element: AXUIElement? = start
        for _ in 0..<3 {
            guard let current = element else { return nil }
            let role = axString(current, kAXRoleAttribute) ?? ""
            if editable.contains(role) || axString(current, kAXSubroleAttribute) == "AXSecureTextField" { return nil }
            if let title = axString(current, kAXTitleAttribute) ?? axString(current, kAXDescriptionAttribute) { return title }
            if role == "AXStaticText", let text = axString(current, kAXValueAttribute) { return text }
            var parent: CFTypeRef?
            guard AXUIElementCopyAttributeValue(current, kAXParentAttribute as CFString, &parent) == .success, let parent,
                  CFGetTypeID(parent) == AXUIElementGetTypeID() else { return nil }
            element = (parent as! AXUIElement)
        }
        return nil
    }
    func select(_ id: String?) {
        selectedFrameID = id.flatMap { candidate in session.frames.contains(where: { $0.id == candidate }) ? candidate : nil }
        selectedIssueID = nil; renderEditor()
    }
    func renderEditor() {
        guard let frame, let root else { editorTask?.cancel(); editorRequest = nil; editorImage = nil; return }
        let request = EditorRenderRequest(source: root, revision: sourceRevision, frame: frame, annotations: annotations)
        guard request != editorRequest else { return }
        let sameFrame = editorRequest?.source == request.source && editorRequest?.frame == request.frame && editorRequest?.revision == request.revision
        editorTask?.cancel(); editorRequest = request
        if !sameFrame { editorImage = nil }
        editorTask = Task { [weak self] in
            do {
                let image = try await ImagePipeline.shared.render(request)
                guard let self, !Task.isCancelled, editorRequest == request else { return }
                editorImage = NSImage(cgImage: image, size: .zero)
            } catch {
                guard let self, !Task.isCancelled, editorRequest == request else { return }
                editorImage = nil; editorRequest = nil; self.error = error.localizedDescription
            }
        }
    }
    func checkpoint() { history.checkpoint(session) }
    func changed() {
        exportURL = nil
        // Display edits even if persistence fails; keep the failure visible to the person.
        renderEditor()
        do { try save() } catch { self.error = error.localizedDescription }
    }
    func add(region: Region, points: [Point]) {
        guard let selectedFrameID, !recording, AnnotationKind.drawingTools.contains(tool) else { return }
        do { checkpoint(); selectedIssueID = try session.addAnnotation(frameID: selectedFrameID, kind: tool, region: region, points: points); changed() }
        catch { self.error = error.localizedDescription }
    }
    func editIssue(_ id: String, text: String) {
        guard let i = session.annotations.firstIndex(where: { $0.id == id }), session.annotations[i].instruction != text else { return }
        checkpoint(); session.annotations[i].instruction = text; changed()
    }
    func editRegion(_ id: String, region: Region) {
        do { try region.validate(); guard let i = session.annotations.firstIndex(where: { $0.id == id }) else { return }; checkpoint()
            let old = session.annotations[i].region
            session.annotations[i].points = session.annotations[i].points.map { p in
                Point(x: min(1, max(0, region.x + (p.x-old.x)/old.width*region.width)),
                      y: min(1, max(0, region.y + (p.y-old.y)/old.height*region.height)))
            }
            session.annotations[i].region = region; changed() }
        catch { self.error = error.localizedDescription }
    }
    func removeIssue(_ id: String) { checkpoint(); session.annotations.removeAll { $0.id == id }; selectedIssueID = nil; changed() }
    func undo() {
        guard let previous = history.undo(session) else { return }; session = previous; reconcileSelection(); changed()
    }
    func redo() {
        guard let next = history.redo(session) else { return }; session = next; reconcileSelection(); changed()
    }
    private func reconcileSelection() {
        selectedFrameID = FrameSelection.resolve(selectedFrameID, in: session)
        if !session.annotations.contains(where: { $0.id == selectedIssueID && $0.frameID == selectedFrameID }) { selectedIssueID = nil }
    }
    func toggleFrame(_ id: String) { guard let i = session.frames.firstIndex(where: { $0.id == id }) else { return }; checkpoint(); session.frames[i].selected.toggle(); changed() }
    func renameFrame(_ id: String, name: String) { guard let i = session.frames.firstIndex(where: { $0.id == id }) else { return }; checkpoint(); session.frames[i].name = name; changed() }
    func moveFrame(_ id: String, by offset: Int) {
        guard let i = session.frames.firstIndex(where: { $0.id == id }), session.frames.indices.contains(i+offset) else { return }
        checkpoint(); session.frames.swapAt(i, i+offset); changed()
    }
    func deleteFrame(_ id: String) {
        checkpoint(); session.frames.removeAll { $0.id == id }; session.annotations.removeAll { $0.frameID == id }
        select(session.frames.first?.id); changed()
        // File remains only in the private session directory until session deletion, allowing undo.
    }
    func importFrame() {
        guard !recording, !stopping, !busy else { return }
        let panel = NSOpenPanel(); panel.allowedContentTypes = [.png, .jpeg, .webP]; panel.canChooseDirectories = false
        guard panel.runModal() == .OK, let url = panel.url else { return }
        do {
            if root == nil { session = Session(); root = storageBase.appendingPathComponent(session.id) }
            let id = "frame-" + UUID().uuidString.lowercased()
            let img = try Images.load(url)
            try FileManager.default.createDirectory(at: root!.appendingPathComponent("frames"), withIntermediateDirectories: true)
            try Images.png(img, to: root!.appendingPathComponent("frames/\(id).png"))
            checkpoint(); session.frames.append(Frame(id: id, timestampMS: session.frames.last?.timestampMS ?? 0, name: url.deletingPathExtension().lastPathComponent, imagePath: "frames/\(id).png", width: img.width, height: img.height, captureReason: "imported"))
            select(id); changed()
        } catch { self.error = error.localizedDescription }
    }
    func save() throws { if let root { try SessionStore.save(session, to: root) } }
    func openSession() {
        guard !recording, !stopping, !busy else { return }
        guard let folder = chooseFolder(message: "Choose a local ContextLens session folder") else { return }
        do { try save(); let loaded = try SessionStore.load(from: folder); session = loaded; root = folder; sourceRevision += 1; history.reset(); exportURL = nil; select(session.frames.first?.id); mainTab = .review; status = "Session opened." }
        catch { self.error = error.localizedDescription }
    }
    func editTask(_ text: String) {
        guard (session.task ?? "") != text else { return }
        checkpoint(); session.task = text.isEmpty ? nil : text; exportURL = nil
        do { try save() } catch { self.error = error.localizedDescription }
    }
    var exportPreviewKey: Data {
        var key = (try? SessionStore.encoder().encode(session)) ?? Data()
        key.append((try? SessionStore.encoder().encode(exportOptions)) ?? Data())
        key.append(Data(((root?.path ?? "") + "#\(sourceRevision)").utf8)); return key
    }
    var currentExportPlan: ExportPlan? {
        guard let exportPlan, exportPlan.sourceSession == session, exportPlan.source == root, exportPlan.options == exportOptions else { return nil }
        return exportPlan
    }
    func refreshExportPreview() async {
        let copy = session, options = exportOptions, source = root, revision = sourceRevision
        exportPreviewLoading = true; exportPreviewError = nil
        guard let source else { exportPreviewLoading = false; exportPlan = nil; exportPreviewError = "Capture or import screenshots to prepare an export."; return }
        do {
            try await Task.sleep(nanoseconds: 200_000_000)
            let worker = Task.detached(priority: .userInitiated) { try ExportPlan.prepare(copy, source: source, options: options) }
            let prepared = try await withTaskCancellationHandler(operation: { try await worker.value }, onCancel: { worker.cancel() })
            guard !Task.isCancelled, copy == session, source == root, options == exportOptions, revision == sourceRevision else { return }
            exportPlan = prepared; exportPreviewLoading = false
        } catch {
            guard !Task.isCancelled, copy == session, source == root, options == exportOptions, revision == sourceRevision else { return }
            exportPlan = nil; exportPreviewLoading = false; exportPreviewError = error.localizedDescription
        }
    }
    func exportSession() async {
        guard !recording, !stopping, !busy, let plan = currentExportPlan, !plan.session.frames.isEmpty else { return }
        let remembered = UserDefaults.standard.string(forKey: "lastExportFolder").map { URL(fileURLWithPath: $0, isDirectory: true) }
        guard let parent = chooseFolder(message: "Choose a folder in your project so your agent can read the hand off without asking.",
                                        prompt: "Save Hand Off", startingAt: remembered) else { return }
        UserDefaults.standard.set(parent.path, forKey: "lastExportFolder")
        busy = true
        let dest = PackageName.unique(PackageName.folder(for: session), in: parent)
        do {
            let manifest = try await Task.detached { try Exporter.export(plan, destination: dest) }.value
            guard plan.sourceSession == session, plan.options == exportOptions, plan.source == root else {
                status = "Hand off saved, but the session changed. Save again to copy the current prompt."; busy = false; return
            }
            exportURL = dest; status = "Hand off saved: \(Self.count(manifest.frames.count, "state")), \(Self.count(manifest.issues.count, "mark"))."
        } catch { self.error = error.localizedDescription }
        busy = false
    }
    static func count(_ n: Int, _ noun: String) -> String { n == 1 ? "1 \(noun)" : "\(n) \(noun)s" }
    /// One prompt for every coding agent; the evidence and guidance live in the package itself.
    func copyPrompt() {
        guard let exportURL else { return }
        NSPasteboard.general.clearContents(); NSPasteboard.general.setString(ContextReport.instruction(path: exportURL.path, task: session.task), forType: .string)
        status = "Prompt copied. Paste it into your coding agent."
    }
    func chooseFolder(message: String, prompt: String? = nil, startingAt directory: URL? = nil) -> URL? {
        let panel = NSOpenPanel(); panel.canChooseDirectories = true; panel.canChooseFiles = false; panel.canCreateDirectories = true; panel.message = message
        if let prompt { panel.prompt = prompt }
        if let directory, FileManager.default.fileExists(atPath: directory.path) { panel.directoryURL = directory }
        return panel.runModal() == .OK ? panel.url : nil
    }
    var canDeleteSession: Bool {
        guard let root else { return false }
        let base = storageBase.resolvingSymlinksInPath().standardizedFileURL.path
        let path = root.resolvingSymlinksInPath().standardizedFileURL.path
        return root.lastPathComponent == session.id && path.hasPrefix(base + "/")
    }
    func deleteSession() {
        guard !recording, !stopping, !busy, let root, canDeleteSession else { error = "Only sessions in the configured storage folder can be deleted here. Manage externally opened folders in Finder."; return }
        do { try FileManager.default.removeItem(at: root); self.root = nil; session = Session(); selectedFrameID = nil; editorImage = nil; history.reset(); status = "Local session deleted. Exported copies are separate." }
        catch { self.error = error.localizedDescription }
    }
    func burnLocalRedactions() {
        guard !recording, !stopping, !busy, let root else { return }
        do {
            for frame in session.frames {
                let reds = session.annotations.filter { $0.frameID == frame.id && $0.kind == .redaction }
                if reds.isEmpty { continue }
                let url = try SessionStore.resolve(frame.imagePath, in: root)
                let img = try Images.load(url)
                let temp = url.deletingLastPathComponent().appendingPathComponent(".redacted-\(UUID().uuidString).png")
                try Images.png(Images.render(img, annotations: reds, overlays: false), to: temp)
                _ = try FileManager.default.replaceItemAt(url, withItemAt: temp)
            }
            history.reset(); exportURL = nil; exportPlan = nil; sourceRevision += 1; renderEditor(); status = "Redactions applied permanently to local image files. Previous exports are separate."
        } catch {
            // Some files may already have been replaced. Invalidate every image even on a partial failure.
            history.reset(); exportURL = nil; exportPlan = nil; sourceRevision += 1; renderEditor()
            self.error = error.localizedDescription
        }
    }
    func purgeDeletedFrames() throws {
        guard canDeleteSession, let root else { return }
        let folder = root.appendingPathComponent("frames")
        let retained = Set(session.frames.map(\.imagePath))
        guard FileManager.default.fileExists(atPath: folder.path) else { return }
        for image in try FileManager.default.contentsOfDirectory(at: folder, includingPropertiesForKeys: nil) {
            let name = image.lastPathComponent
            if name.hasPrefix("frame-"), image.pathExtension == "png", !retained.contains("frames/" + name) {
                try FileManager.default.removeItem(at: image)
            }
        }
    }
    func pruneSessions() {
        guard !recording, !stopping, !busy else { return }
        do {
            let fm = FileManager.default
            let folders = try fm.contentsOfDirectory(at: storageBase, includingPropertiesForKeys: nil)
            let cutoff = Date().addingTimeInterval(-Double(retentionDays)*86400)
            var count = 0
            for folder in folders where folder != root {
                guard Session.safeName(folder.lastPathComponent), let s = try? SessionStore.load(from: folder), folder.lastPathComponent == s.id, s.createdAt < cutoff else { continue }
                try fm.removeItem(at: folder); count += 1
            }
            status = "Deleted \(count) local sessions older than \(retentionDays) days."
        } catch { self.error = error.localizedDescription }
    }
}
