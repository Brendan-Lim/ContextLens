import Foundation
import AppKit
import ContextLensCore
import ContextLensImaging
import ContextLensCapture

@main struct LensCLI {
    static func main() async {
        do {
            let args = Array(CommandLine.arguments.dropFirst())
            switch args.first {
            case "validate":
                guard args.count == 2 else { throw LensError.invalid("Usage: contextlens validate SESSION_FOLDER") }
                let root = URL(fileURLWithPath: args[1]); let s = try SessionStore.load(from: root)
                for f in s.frames { let img = try Images.load(SessionStore.resolve(f.imagePath, in: root)); guard img.width == f.width, img.height == f.height else { throw LensError.invalid("Image dimensions mismatch.") } }
                print("Valid session: \(s.frames.count) frames, \(s.annotations.count) annotations")
            case "export":
                guard args.count >= 3 else { throw LensError.invalid("Usage: contextlens-cli export SESSION_FOLDER NEW_EXPORT_FOLDER [--all-frames] [--keep-duplicates]") }
                let flags = Set(args.dropFirst(3))
                guard flags.isSubset(of: ["--all-frames", "--keep-duplicates"]) else { throw LensError.invalid("Unknown export option.") }
                let root = URL(fileURLWithPath: args[1]); let s = try SessionStore.load(from: root)
                let options = ExportOptions(annotatedOnly: !flags.contains("--all-frames"), excludeDuplicates: !flags.contains("--keep-duplicates"))
                let m = try Exporter.export(s, source: root, destination: URL(fileURLWithPath: args[2]), options: options)
                print("Exported \(m.frames.count) frames and \(m.issues.count) annotations")
                if let summary = m.summary { print("Excluded \(summary.excludedUnannotated) unannotated and \(summary.excludedDuplicates) duplicate frames") }
            case "demo":
                guard args.count == 2 else { throw LensError.invalid("Usage: contextlens demo NEW_SESSION_FOLDER") }
                let root = URL(fileURLWithPath: args[1])
                guard !FileManager.default.fileExists(atPath: root.path) else { throw LensError.invalid("Demo destination exists.") }
                try FileManager.default.createDirectory(at: root.appendingPathComponent("frames"), withIntermediateDirectories: true)
                var s = Session(id: "demo-session")
                for i in 1...3 {
                    let image = try demoImage(index: i)
                    let id = String(format: "frame-%03d", i)
                    try Images.png(image, to: root.appendingPathComponent("frames/\(id).png"))
                    s.frames.append(Frame(id: id, timestampMS: (i-1)*1000, name: ["Dashboard", "Settings", "Confirmation"][i-1], imagePath: "frames/\(id).png", width: 960, height: 600, applicationName: "Generated fixture", captureReason: "synthetic_fixture", changeScore: 0.2))
                }
                _ = try s.addAnnotation(frameID: "frame-003", kind: .rectangle, region: Region(x: 0.31, y: 0.65, width: 0.18, height: 0.1), instruction: "Align the confirmation button to the right edge of the dialog.")
                _ = try s.addAnnotation(frameID: "frame-002", kind: .redaction, region: Region(x: 0.35, y: 0.25, width: 0.3, height: 0.12))
                try SessionStore.save(s, to: root); print(root.path)
            case "replay":
                guard args.count == 3 else { throw LensError.invalid("Usage: contextlens-cli replay EVENTS_JSON NEW_SESSION_FOLDER") }
                let eventURL = URL(fileURLWithPath: args[1]), root = URL(fileURLWithPath: args[2])
                guard !FileManager.default.fileExists(atPath: root.path) else { throw LensError.invalid("Replay destination exists.") }
                struct ReplayEvent: Decodable { let timestampMS: Int; let imagePath: String; let event: String?; let manual: Bool? }
                let events = try JSONDecoder().decode([ReplayEvent].self, from: Data(contentsOf: eventURL))
                var s = Session(id: "replay-" + UUID().uuidString.lowercased())
                // Archived browser fixtures were recorded with this configuration.
                // Native capture has only Low/High and defaults to High.
                var replaySelector = FrameSelector(); replaySelector.sensitivity = .legacyBalanced
                let worker = CaptureProcessor(root: root, selector: replaySelector)
                for event in events {
                    let image = try Images.load(SessionStore.resolve(event.imagePath, in: eventURL.deletingLastPathComponent()))
                    if let f = try await worker.process(image: image, at: event.timestampMS, scale: 1, title: nil, app: "Benchmark browser fixture", event: event.event, manual: event.manual ?? false) { s.frames.append(f) }
                }
                if let f = try await worker.flush() { s.frames.append(f) }
                try SessionStore.save(s, to: root); print("Replayed \(events.count) samples into \(s.frames.count) states")
            case "stress-fixture":
                guard (3...4).contains(args.count), let count = Int(args[2]), args.count == 3 || args[3] == "--gradient" else { throw LensError.invalid("Usage: contextlens-cli stress-fixture NEW_FOLDER COUNT [--gradient]") }
                try PerformanceProbe.fixture(at: URL(fileURLWithPath: args[1]), count: count, gradient: args.count == 4)
            case "profile-images":
                guard args.count == 2 else { throw LensError.invalid("Usage: contextlens-cli profile-images SESSION_FOLDER") }
                let result = try await PerformanceProbe.images(at: URL(fileURLWithPath: args[1]))
                print(String(decoding: try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys]), as: UTF8.self))
            case "profile":
                let size = 240*150
                let a = try LumaFrame(width: 240, height: 150, pixels: Array(repeating: 100, count: size))
                var pixels = a.pixels
                for y in 20..<30 { for x in 20..<30 { pixels[y*240+x] = 240 } }
                let b = try LumaFrame(width: 240, height: 150, pixels: pixels)
                let start = DispatchTime.now().uptimeNanoseconds
                var changes = 0
                for _ in 0..<1000 { if Difference.compare(a,b).regional > 0.1 { changes += 1 } }
                let elapsed = Double(DispatchTime.now().uptimeNanoseconds-start)/1_000_000
                print("{\"kind\":\"frame-comparison-microbenchmark\",\"samples\":1000,\"width\":240,\"height\":150,\"elapsed_ms\":\(elapsed),\"mean_ms\":\(elapsed/1000),\"regional_detections\":\(changes)}")
            case "permissions":
                print("Screen Recording: \(Permissions.screenRecording); Accessibility: \(Permissions.accessibility)")
            case "windows":
                for w in try await WindowCapture.windows() { print("\(w.id)\t\(w.app)\t\(w.title)") }
            default:
                // Preserve the existing no-argument/unknown-command behavior; --help and -h
                // reach the same supported help path without enumerating windows or capturing.
                print("""
                ContextLens CLI
                  --help, -h
                  demo NEW_SESSION_FOLDER
                  validate SESSION_FOLDER
                  export SESSION_FOLDER NEW_EXPORT_FOLDER [--all-frames] [--keep-duplicates]
                  replay EVENTS_JSON NEW_SESSION_FOLDER
                  profile
                  stress-fixture NEW_FOLDER COUNT [--gradient]
                  profile-images SESSION_FOLDER
                  permissions
                  windows
                No network requests or agent execution are performed.
                """)
            }
        } catch { fputs("ContextLens: \(error.localizedDescription)\n", stderr); exit(1) }
    }
    static func demoImage(index: Int) throws -> CGImage {
        guard let ctx = CGContext(data: nil, width: 960, height: 600, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { throw LensError.invalid("Cannot create fixture.") }
        ctx.setFillColor(CGColor(red: 0.09, green: 0.10, blue: 0.13, alpha: 1)); ctx.fill(CGRect(x: 0, y: 0, width: 960, height: 600))
        ctx.setFillColor(CGColor(red: 0.14, green: 0.16, blue: 0.21, alpha: 1)); ctx.fill(CGRect(x: 0, y: 0, width: 210, height: 600))
        for row in 0..<5 { ctx.setFillColor(NSColor.systemGray.cgColor); ctx.fill(CGRect(x: 30, y: 520-row*65, width: 140, height: 16)) }
        ctx.setFillColor(NSColor.darkGray.cgColor); ctx.fill(CGRect(x: 280, y: 140, width: 600, height: 330))
        ctx.setFillColor(NSColor.systemTeal.cgColor); ctx.fill(CGRect(x: 300, y: 150, width: 170, height: 55))
        if index == 2 { ctx.setFillColor(NSColor.systemOrange.cgColor); ctx.fill(CGRect(x: 340, y: 380, width: 280, height: 45)) }
        if index == 3 { ctx.setFillColor(NSColor.systemIndigo.cgColor); ctx.fill(CGRect(x: 580, y: 260, width: 230, height: 140)) }
        return ctx.makeImage()!
    }
}
