import SwiftUI
import AppKit
import ContextLensCore
import ContextLensCapture
import ContextLensImaging
import ScreenCaptureKit

@main struct ContextLensApp: App {
    @StateObject private var model = AppModel()
    @NSApplicationDelegateAdaptor(LensDelegate.self) var delegate
    var body: some Scene {
        WindowGroup("ContextLens") { ContentView().environmentObject(model).frame(minWidth: 1080, minHeight: 720).onAppear { delegate.model = model } }
            .defaultSize(width: 1320, height: 860)
            .windowToolbarStyle(.unified(showsTitle: false))
            .commands {
                CommandGroup(replacing: .newItem) {
                    Button("New Capture…") { CapturePanelController.shared.show() }.keyboardShortcut("n")
                    Divider()
                    Button("Open Session…", action: model.openSession).keyboardShortcut("o").disabled(model.recording || model.busy)
                    Button("Save Session") { do { try model.save() } catch { model.error = error.localizedDescription } }.keyboardShortcut("s")
                    Button("Import Screenshot…", action: model.importFrame).keyboardShortcut("i").disabled(model.recording || model.busy)
                }
                CommandGroup(replacing: .undoRedo) {
                    Button("Undo", action: model.undo).keyboardShortcut("z").disabled(!model.canUndo || model.recording)
                    Button("Redo", action: model.redo).keyboardShortcut("z", modifiers: [.command, .shift]).disabled(!model.canRedo || model.recording)
                }
                CommandMenu("Capture") {
                    Button("Show Capture Panel") { CapturePanelController.shared.show() }
                    Divider()
                    Button("Manual Snapshot", action: model.snapshot).keyboardShortcut("s", modifiers: [.command, .shift]).disabled(!model.recording)
                    Button("Stop Capture") { Task { await model.stop() } }.keyboardShortcut(".").disabled(!model.recording)
                }
            }
    }
}
@MainActor final class LensDelegate: NSObject, NSApplicationDelegate {
    weak var model: AppModel?
    private var smokeWindow: NSWindow?
    private var smokeModel: AppModel?
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        guard let model else { return .terminateNow }
        if model.recording || model.stopping {
            Task { await model.stop(); sender.reply(toApplicationShouldTerminate: true) }
            return .terminateLater
        }
        do { try model.save(); try model.purgeDeletedFrames() } catch { model.error = error.localizedDescription; return .terminateCancel }
        return .terminateNow
    }
    func applicationDidFinishLaunching(_ notification: Notification) {
        let args = CommandLine.arguments
        NSApp.setActivationPolicy(.regular)
        // Test launches stay in the background so they never take keystrokes or clicks meant for other apps.
        if !args.contains("--smoke-snapshot") && !args.contains("--exercise-zoom") && !args.contains("--capture-soak") { NSApp.activate(ignoringOtherApps: true) }
        if let i = args.firstIndex(of: "--capture-soak"), args.indices.contains(i+1) {
            let output = URL(fileURLWithPath: args[i+1])
            let durationIndex = args.firstIndex(of: "--soak-seconds")
            let seconds = durationIndex.flatMap { args.indices.contains($0+1) ? Int(args[$0+1]) : nil } ?? 600
            let sensitivity: Sensitivity = args.contains("--low-sensitivity") ? .low : .high
            Task { @MainActor in
                await CaptureSoak.run(output: output, seconds: seconds, sensitivity: sensitivity)
                NSApp.terminate(nil)
            }
        }
        if let i = args.firstIndex(of: "--exercise-zoom"), args.indices.contains(i+1) {
            let report = args[i+1]
            DispatchQueue.main.asyncAfter(deadline: .now()+2) { Task { @MainActor in await Self.exerciseZoom(report: report); NSApp.terminate(nil) } }
        }
        if args.contains("--smoke-snapshot") || args.contains("--exercise-zoom") {
            // Restored macOS scene state can suppress the initial WindowGroup in a test launch.
            // Build the same content in a dedicated fixture window only for explicit test runs.
            DispatchQueue.main.asyncAfter(deadline: .now()+0.4) { [weak self] in
                guard let self, !NSApp.windows.contains(where: { $0.isVisible && $0.contentView != nil }) else { return }
                let fixtureModel = AppModel()
                let fixture = NSWindow(contentRect: NSRect(x: 80, y: 80, width: 1320, height: 860), styleMask: [.titled, .closable, .resizable, .miniaturizable], backing: .buffered, defer: false)
                fixture.title = "ContextLens"; fixture.isReleasedWhenClosed = false
                fixture.contentView = NSHostingView(rootView: ContentView().environmentObject(fixtureModel))
                self.smokeModel = fixtureModel; self.model = fixtureModel; self.smokeWindow = fixture
                fixture.makeKeyAndOrderFront(nil)
            }
        }
        if let i = args.firstIndex(of: "--smoke-snapshot"), args.indices.contains(i+1) {
            let output = args[i+1]
            if args.contains("--exercise-highlighter") {
                DispatchQueue.main.asyncAfter(deadline: .now()+1) { [weak self] in self?.exerciseHighlighter() }
            }
            DispatchQueue.main.asyncAfter(deadline: .now()+3) {
                guard let window = NSApp.windows.first(where: { $0.contentView != nil && $0.isVisible }) ?? NSApp.windows.first(where: { $0.title == "ContextLens" && $0.contentView != nil }),
                      let view = window.contentView, let bitmap = Self.snapshotRep(for: view, args: args) else {
                    fputs("No renderable ContextLens window (\(NSApp.windows.count) windows).\n", stderr); exit(2)
                }
                window.makeKeyAndOrderFront(nil)
                view.cacheDisplay(in: view.bounds, to: bitmap)
                guard let data = bitmap.representation(using: .png, properties: [:]) else { exit(3) }
                do {
                    try data.write(to: URL(fileURLWithPath: output))
                    print("Native window rendered: \(output); Screen Recording preflight: \(Permissions.screenRecording)")
                    Task { @MainActor in
                        if args.contains("--native-capture-test") {
                            await Self.captureOwnWindow(output: output)
                        }
                        NSApp.terminate(nil)
                    }
                }
                catch { fputs("Snapshot failed: \(error)\n", stderr); exit(4) }
            }
        }
    }
    /// `--snapshot-scale 2` renders the snapshot at that pixel density, whatever display the window is on.
    static func snapshotRep(for view: NSView, args: [String]) -> NSBitmapImageRep? {
        guard let i = args.firstIndex(of: "--snapshot-scale"), args.indices.contains(i+1), let scale = Double(args[i+1]), scale > 0 else {
            return view.bitmapImageRepForCachingDisplay(in: view.bounds)
        }
        let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: Int(view.bounds.width * scale), pixelsHigh: Int(view.bounds.height * scale),
                                   bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)
        rep?.size = view.bounds.size
        return rep
    }
    /// Drives real drag events only in the generated smoke fixture, never in an ordinary session.
    private func exerciseHighlighter() {
        guard let model, model.session.id == "demo-session",
              let window = NSApp.windows.first(where: { $0.isVisible }) ?? NSApp.windows.first(where: { $0.title == "ContextLens" }) else {
            fputs("Generated drag fixture is not ready.\n", stderr); return
        }
        model.tool = .highlight
        let samples: [(NSEvent.EventType, NSPoint)] = [
            (.leftMouseDown, NSPoint(x: 450, y: 410)),
            (.leftMouseDragged, NSPoint(x: 470, y: 410)),
            (.leftMouseDragged, NSPoint(x: 490, y: 410)),
            (.leftMouseDragged, NSPoint(x: 490, y: 370)),
            (.leftMouseDragged, NSPoint(x: 530, y: 370)),
            (.leftMouseUp, NSPoint(x: 560, y: 370))
        ]
        window.makeKeyAndOrderFront(nil)
        for (index, sample) in samples.enumerated() {
            DispatchQueue.main.asyncAfter(deadline: .now()+Double(index)*0.08) {
                if let event = NSEvent.mouseEvent(with: sample.0, location: sample.1, modifierFlags: [], timestamp: ProcessInfo.processInfo.systemUptime,
                                                 windowNumber: window.windowNumber, context: nil, eventNumber: index, clickCount: 1, pressure: sample.0 == .leftMouseUp ? 0 : 1) {
                    NSApp.postEvent(event, atStart: false)
                }
            }
        }
    }
    /// Zoom-to-pointer check for Mark Up. Posts real ⌘-scroll events at chosen points over the screenshot, renders
    /// the window before and after, and compares the pixel under the pointer. Use a session whose frames encode
    /// position in colour (red = x, green = y), so the same colour means the same image point stayed under the pointer.
    static func exerciseZoom(report path: String) async {
        var result: [String: Any] = ["kind": "zoom-to-pointer-check"]
        defer { try? JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys]).write(to: URL(fileURLWithPath: path)) }
        guard let probe = CanvasTestHook.probe, let view = probe.view, let window = view.window, let content = window.contentView else {
            result["status"] = "failed"; result["reason"] = "Mark Up canvas not found"; return
        }
        var dumps = 0
        func sample(_ p: CGPoint) -> [Int] {
            content.layoutSubtreeIfNeeded()
            guard let rep = content.bitmapImageRepForCachingDisplay(in: content.bounds) else { return [] }
            content.cacheDisplay(in: content.bounds, to: rep)
            let c = content.convert(p, from: view)
            let scale = CGFloat(rep.pixelsWide) / content.bounds.width
            let y = content.isFlipped ? c.y : content.bounds.height - c.y
            if dumps < 2, let data = rep.representation(using: .png, properties: [:]) {
                // The first two renders are kept beside the report, with the sample point recorded, for inspection.
                try? data.write(to: URL(fileURLWithPath: path).deletingPathExtension().appendingPathExtension("render\(dumps).png"))
                result["render\(dumps)_sample_pixel"] = [Int(c.x * scale), Int(y * scale)]
                dumps += 1
            }
            guard let color = rep.colorAt(x: Int(c.x * scale), y: Int(y * scale))?.usingColorSpace(.sRGB) else { return [] }
            return [Int(color.redComponent * 255), Int(color.greenComponent * 255)]
        }
        func scroll(at p: CGPoint, delta: Int32) {
            let screen = window.convertPoint(toScreen: view.convert(p, to: nil))
            let primaryHeight = NSScreen.screens.first?.frame.height ?? 0
            guard let e = CGEvent(scrollWheelEvent2Source: nil, units: .pixel, wheelCount: 1, wheel1: delta, wheel2: 0, wheel3: 0) else { return }
            e.flags = .maskCommand
            e.location = CGPoint(x: screen.x, y: primaryHeight - screen.y)
            if let event = NSEvent(cgEvent: e) { NSApp.postEvent(event, atStart: false) }
        }
        func settle() async { try? await Task.sleep(nanoseconds: 350_000_000) }
        result["viewport_in_window"] = NSStringFromRect(view.convert(view.bounds, to: nil))
        var cases: [[String: Any]] = []
        // Image fractions to zoom at: off-centre in both directions, so a wrong anchor cannot pass by symmetry.
        for (fx, fy) in [(0.78, 0.25), (0.2, 0.72), (0.62, 0.6), (0.95, 0.92), (0.04, 0.06)] {
            let state = CanvasTestHook.state, fit = CanvasTestHook.fit
            let p = CGPoint(x: state.offset.x + fx * fit.width * state.zoom, y: state.offset.y + fy * fit.height * state.zoom)
            let before = sample(p)
            for _ in 0..<6 { scroll(at: p, delta: 16) }
            await settle()
            let zoomed = CanvasTestHook.state
            let after = sample(p)
            let drift = zip(before, after).map { abs($0 - $1) }.max() ?? 255
            cases.append(["point": [Int(p.x), Int(p.y)], "zoom": Double(zoomed.zoom), "color_before": before, "color_after": after,
                          "max_channel_drift": drift, "passed": zoomed.zoom > 1.5 && before.count == 2 && drift <= 3])
            for _ in 0..<12 { scroll(at: p, delta: -40) }
            await settle()
        }
        result["cases"] = cases
        result["status"] = cases.allSatisfy { $0["passed"] as? Bool == true } ? "passed" : "failed"
    }
    static func captureOwnWindow(output: String) async {
        let reportURL = URL(fileURLWithPath: output).deletingLastPathComponent().appendingPathComponent("native-capture-verification.json")
        var report: [String: Any] = ["screen_recording_granted": Permissions.screenRecording, "kind": "native-integration-check"]
        guard Permissions.screenRecording else {
            report["status"] = "blocked"; report["reason"] = "Screen Recording permission is not granted; no permission dialog was requested."
            try? JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: reportURL)
            print("Native capture blocked by Screen Recording permission."); return
        }
        do {
            guard let window = NSApp.windows.first(where: { $0.contentView != nil && $0.isVisible }) else { throw LensError.invalid("No fixture window") }
            let targetID = CGWindowID(window.windowNumber)
            let content = try await SCShareableContent.excludingDesktopWindows(true, onScreenWindowsOnly: true)
            guard let selected = content.windows.first(where: { $0.windowID == targetID && $0.owningApplication?.processID == ProcessInfo.processInfo.processIdentifier }) else { throw LensError.invalid("Cannot identify own fixture window") }
            let (image, scale) = try await WindowCapture.image(window: selected)
            try Images.png(image, to: URL(fileURLWithPath: output))
            report["status"] = "passed"; report["width"] = image.width; report["height"] = image.height; report["scale"] = scale
            report["boundary"] = "SCContentFilter(desktopIndependentWindow:) for the app's generated fixture window only"
            let originalFrame = window.frame
            window.setFrameOrigin(NSPoint(x: originalFrame.minX+12, y: originalFrame.minY+12))
            try await Task.sleep(nanoseconds: 200_000_000)
            let movedContent = try await SCShareableContent.excludingDesktopWindows(true, onScreenWindowsOnly: true)
            let moved = try WindowCapture.selected(id: targetID, pid: ProcessInfo.processInfo.processIdentifier, in: movedContent.windows.map { WindowChoice(window: $0) })
            let (movedImage, _) = try await WindowCapture.image(window: moved.window)
            report["movement_preserved_dimensions"] = movedImage.width == image.width && movedImage.height == image.height
            // Shrink: a restored window may already occupy the screen's maximum height.
            window.setContentSize(NSSize(width: max(500, originalFrame.width-160), height: max(400, originalFrame.height-120)))
            try await Task.sleep(nanoseconds: 250_000_000)
            let resizedContent = try await SCShareableContent.excludingDesktopWindows(true, onScreenWindowsOnly: true)
            let resized = try WindowCapture.selected(id: targetID, pid: ProcessInfo.processInfo.processIdentifier, in: resizedContent.windows.map { WindowChoice(window: $0) })
            let (resizedImage, _) = try await WindowCapture.image(window: resized.window)
            report["resize_dimensions_updated"] = resizedImage.width < image.width && resizedImage.height < image.height
            report["resized_width"] = resizedImage.width; report["resized_height"] = resizedImage.height
            window.setFrame(originalFrame, display: true)
            let probe = NSWindow(contentRect: NSRect(x: 100, y: 100, width: 300, height: 200), styleMask: [.titled], backing: .buffered, defer: false)
            probe.isReleasedWhenClosed = false; probe.title = "ContextLens closure test"; probe.makeKeyAndOrderFront(nil)
            let probeID = CGWindowID(probe.windowNumber)
            try await Task.sleep(nanoseconds: 200_000_000)
            probe.close()
            try await Task.sleep(nanoseconds: 200_000_000)
            let closedContent = try await SCShareableContent.excludingDesktopWindows(true, onScreenWindowsOnly: true)
            do {
                _ = try WindowCapture.selected(id: probeID, pid: ProcessInfo.processInfo.processIdentifier, in: closedContent.windows.map { WindowChoice(window: $0) })
                report["closure_detected_without_fallback"] = false
            } catch { report["closure_detected_without_fallback"] = true }
            if report["movement_preserved_dimensions"] as? Bool != true || report["resize_dimensions_updated"] as? Bool != true || report["closure_detected_without_fallback"] as? Bool != true { report["status"] = "failed" }
            print("ScreenCaptureKit selected-window capture passed: \(image.width)×\(image.height); movement, resize and closure checks recorded.")
        } catch { report["status"] = "failed"; report["reason"] = error.localizedDescription }
        try? JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: reportURL)
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}
