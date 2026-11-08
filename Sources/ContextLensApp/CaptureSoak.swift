import AppKit
import ScreenCaptureKit
import ContextLensCore
import ContextLensCapture
import ContextLensImaging

/// Explicit developer-only self-window recording. It never opens the normal picker or targets another process.
@MainActor enum CaptureSoak {
    static func run(output: URL, seconds: Int, sensitivity: Sensitivity) async {
        var report: [String: Any] = ["kind": "self-window-capture-soak", "requested_seconds": seconds,
            "sensitivity": sensitivity.rawValue,
            "limitations": "Generated animation and scripted scroll holding, not human scroll events or real video. CPU/RSS include fixture animation and app UI. No external window is captured."]
        let fm = FileManager.default
        let root = fm.temporaryDirectory.appendingPathComponent("contextlens-soak-" + UUID().uuidString)
        defer {
            try? fm.removeItem(at: root)
            do { try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: output, options: .atomic) }
            catch { fputs("Could not write soak report.\n", stderr) }
        }
        guard (1...600).contains(seconds), Permissions.screenRecording else {
            report["status"] = "blocked"; report["reason"] = "Valid duration and existing Screen Recording approval are required. No permission prompt requested."; return
        }
        let fixture = NSWindow(contentRect: NSRect(x: 100, y: 100, width: 960, height: 600), styleMask: [.titled], backing: .buffered, defer: false)
        fixture.title = "ContextLens generated capture workload"; fixture.isReleasedWhenClosed = false
        let view = BusyFixture(frame: NSRect(x: 0, y: 0, width: 960, height: 600))
        fixture.contentView = view; fixture.orderFront(nil)
        let timer = Timer.scheduledTimer(withTimeInterval: 1.0 / 30, repeats: true) { [weak view] _ in
            guard let view else { return }; view.needsDisplay = true
        }
        defer { timer.invalidate(); fixture.close() }
        do {
            try await Task.sleep(nanoseconds: 300_000_000)
            let id = CGWindowID(fixture.windowNumber), pid = ProcessInfo.processInfo.processIdentifier
            var selector = FrameSelector(); selector.sensitivity = sensitivity; selector.maximumFrames = 10_000
            let worker = CaptureProcessor(root: root, selector: selector)
            var session = Session(id: "soak-generated")
            let start = ProcessInfo.processInfo.systemUptime
            view.startedAt = start
            var sampleTimes: [Double] = [], perMinute = [Int](repeating: 0, count: (seconds+59)/60)
            var scrollCommits = 0, samples = 0
            var previous: LumaFrame?, maxDifference = 0.0, lastImage: CGImage?
            while ProcessInfo.processInfo.systemUptime - start < Double(seconds) {
                let tick = ProcessInfo.processInfo.systemUptime
                let content = try await SCShareableContent.excludingDesktopWindows(true, onScreenWindowsOnly: true)
                let selected = try WindowCapture.selected(id: id, pid: pid, in: content.windows.map { WindowChoice(window: $0) })
                let (image, scale) = try await WindowCapture.image(window: selected.window)
                let luma = try Images.luma(image)
                if let previous { maxDifference = max(maxDifference, Difference.compare(previous, luma).global) }
                previous = luma; lastImage = image
                if samples == 0 { try Images.png(image, to: output.deletingPathExtension().appendingPathExtension("first.png")) }
                let elapsed = ProcessInfo.processInfo.systemUptime - start
                // Each minute: 20 s continuous scrolling, 10 s static, 30 s animated content.
                let holding = elapsed.truncatingRemainder(dividingBy: 60) < 20
                if let frame = try await worker.process(image: image, at: Int(elapsed * 1000), scale: scale, title: nil, app: nil, event: nil, manual: false, holding: holding) {
                    session.frames.append(frame)
                    perMinute[min(perMinute.count-1, Int(elapsed / 60))] += 1
                    if frame.captureReason == "scroll" { scrollCommits += 1 }
                }
                samples += 1; sampleTimes.append((ProcessInfo.processInfo.systemUptime - tick) * 1000)
                try await Task.sleep(nanoseconds: 250_000_000)
            }
            if let frame = try await worker.flush() {
                session.frames.append(frame); perMinute[perMinute.count-1] += 1
                if frame.captureReason == "scroll" { scrollCommits += 1 }
            }
            let elapsed = ProcessInfo.processInfo.systemUptime - start
            if let lastImage { try Images.png(lastImage, to: output.deletingPathExtension().appendingPathExtension("last.png")) }
            report["maximum_sample_global_difference"] = maxDifference
            report["image_width"] = lastImage?.width; report["image_height"] = lastImage?.height
            try SessionStore.save(session, to: root)
            let sorted = sampleTimes.sorted()
            report["status"] = samples > 1 && maxDifference > 0.01 ? "passed" : "failed-no-changing-workload"; report["elapsed_seconds"] = elapsed; report["samples"] = samples
            report["states"] = session.frames.count; report["states_per_minute"] = Double(session.frames.count) / elapsed * 60
            report["states_by_minute"] = perMinute; report["scroll_commits"] = scrollCommits
            report["expected_completed_scroll_periods"] = seconds >= 21 ? (seconds-21)/60+1 : 0
            report["sample_work_mean_ms"] = sampleTimes.reduce(0,+) / Double(max(1, samples))
            report["sample_work_p95_ms"] = sorted[min(sorted.count-1, Int(Double(sorted.count)*0.95))]
            report["fixture_draws"] = view.draws
            report["capture_boundary"] = "Own generated NSWindow ID plus this process ID only; production WindowCapture.image and CaptureProcessor."
            print("Self-window soak complete: \(sensitivity.rawValue), \(samples) samples, \(session.frames.count) states.")
        } catch { report["status"] = "failed"; report["reason"] = error.localizedDescription }
    }
}

@MainActor private final class BusyFixture: NSView {
    var startedAt = ProcessInfo.processInfo.systemUptime
    var draws = 0
    override func draw(_ dirtyRect: NSRect) {
        draws += 1
        let elapsed = ProcessInfo.processInfo.systemUptime - startedAt
        let phase = elapsed.truncatingRemainder(dividingBy: 60)
        let offset = phase < 20 ? Int(elapsed * 170) % 48 : phase < 30 ? 40 : (40 + Int((phase-30) * 250)) % 48
        NSColor(calibratedWhite: 0.12, alpha: 1).setFill(); bounds.fill()
        for row in -1..<14 {
            NSColor(calibratedRed: CGFloat((row+2)%5)/5, green: 0.4, blue: 0.65, alpha: 1).setFill()
            NSRect(x: 30, y: CGFloat(row*48-offset), width: 850, height: 30).fill()
        }
    }
}
