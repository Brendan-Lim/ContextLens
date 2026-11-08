import AppKit
import os
import ScreenCaptureKit
import ApplicationServices
import ContextLensCore
import ContextLensImaging

public struct WindowChoice: Identifiable {
    public var id: CGWindowID { window.windowID }
    public let window: SCWindow
    public init(window: SCWindow) { self.window = window }
    public var title: String { window.title?.isEmpty == false ? window.title! : "Untitled window" }
    public var app: String { window.owningApplication?.applicationName ?? "Unknown application" }
}
@MainActor public enum Permissions {
    public static var screenRecording: Bool { CGPreflightScreenCaptureAccess() }
    public static var accessibility: Bool { AXIsProcessTrusted() }
    public static func requestScreen() { CGRequestScreenCaptureAccess() }
    public static func requestAccessibility() {
        let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
        _ = AXIsProcessTrustedWithOptions(options)
    }
    public static func openScreenSettings() { NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture")!) }
}
public enum WindowCapture {
    public static func selected(id: CGWindowID, pid: pid_t, in available: [WindowChoice]) throws -> WindowChoice {
        guard let original = available.first(where: { $0.id == id && $0.window.owningApplication?.processID == pid }) else {
            throw LensError.invalid("The selected window is no longer available. Capture stopped; no other window was substituted.")
        }
        return original
    }
    public static func windows() async throws -> [WindowChoice] {
        let content = try await SCShareableContent.excludingDesktopWindows(true, onScreenWindowsOnly: true)
        let ownPID = ProcessInfo.processInfo.processIdentifier
        return content.windows.filter {
            $0.owningApplication?.processID != ownPID && $0.windowLayer == 0 && $0.frame.width > 80 && $0.frame.height > 60
        }.map { WindowChoice(window: $0) }.sorted { ($0.app, $0.title) < ($1.app, $1.title) }
    }
    public static func image(window: SCWindow) async throws -> (CGImage, Double) {
        let filter = SCContentFilter(desktopIndependentWindow: window)
        let scale = Double(filter.pointPixelScale)
        let config = SCStreamConfiguration()
        config.width = max(1, Int(filter.contentRect.width * scale))
        config.height = max(1, Int(filter.contentRect.height * scale))
        config.showsCursor = false; config.ignoreShadowsSingleWindow = true
        let image = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: config)
        return (image, scale)
    }
}
/// All comparison and encoding work runs on this actor, away from the UI thread.
public actor CaptureProcessor {
    private var selector: FrameSelector
    private let root: URL
    private var lastImage: CGImage?
    private var lastLuma: LumaFrame?
    private var lastMeta: Frame?
    private var sequence = 0
    private var lastTime = -1
    private let log = Logger(subsystem: "dev.contextlens.app", category: "Capture")
    public init(root: URL, selector: FrameSelector) { self.root = root; self.selector = selector }
    public func process(image: CGImage, at ms: Int, scale: Double, title: String?, app: String?, event: String?, manual: Bool, holding: Bool = false) throws -> Frame? {
        try Task.checkCancellation()
        guard ms >= 0, scale.isFinite, scale > 0 else { throw LensError.invalid("Invalid capture timestamp or scale.") }
        guard ms >= lastTime else { log.debug("Ignored out-of-order sample"); return nil }
        let luma = try Images.luma(image)
        // Commit selector state only after a successful write; a disk error can be retried safely.
        var next = selector
        let decision = next.observe(luma, at: ms, manual: manual, holding: holding)
        lastImage = image; lastLuma = luma
        lastMeta = Frame(id: "pending", timestampMS: ms, name: "", imagePath: "pending.png", width: image.width, height: image.height, displayScale: scale, windowTitle: title, applicationName: app, event: event)
        let frame = try decision.map { try write(image, decision: $0) }
        selector = next; lastTime = ms
        return frame
    }
    public func flush() throws -> Frame? {
        var next = selector
        guard let image = lastImage, let luma = lastLuma, let decision = next.flush(luma) else { return nil }
        let frame = try write(image, decision: decision)
        selector = next
        return frame
    }
    private func write(_ image: CGImage, decision: Selection) throws -> Frame {
        guard var frame = lastMeta else { throw LensError.invalid("Missing capture metadata.") }
        let nextSequence = sequence + 1
        frame.id = String(format: "frame-%03d", nextSequence); frame.name = "State \(nextSequence)"
        frame.imagePath = "frames/\(frame.id).png"; frame.captureReason = decision.reason; frame.changeScore = decision.score
        let folder = root.appendingPathComponent("frames")
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        try Images.png(image, to: root.appendingPathComponent(frame.imagePath))
        sequence = nextSequence
        log.debug("Committed frame \(nextSequence, privacy: .public)")
        return frame
    }
}
