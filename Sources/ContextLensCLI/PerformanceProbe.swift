import Foundation
import CoreGraphics
import ContextLensCore
import ContextLensImaging

/// Generated workloads only: these timings never stand in for human effort or provider tokens.
enum PerformanceProbe {
    static func fixture(at root: URL, count: Int, gradient: Bool = false) throws {
        guard (1...1000).contains(count), !FileManager.default.fileExists(atPath: root.path) else { throw LensError.invalid("Choose a new fixture folder and 1–1000 frames.") }
        try FileManager.default.createDirectory(at: root.appendingPathComponent("frames"), withIntermediateDirectories: true)
        var session = Session(id: "stress-fixture")
        let w = 1920, h = 1200
        for i in 0..<count {
            try autoreleasepool {
                let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
                if gradient {
                    // Top-left normalized position in red/green; used by the native zoom check.
                    var bytes = [UInt8](repeating: 255, count: w * h * 4)
                    for y in 0..<h { for x in 0..<w {
                        let j = (y * w + x) * 4
                        bytes[j] = UInt8(x * 255 / (w - 1)); bytes[j+1] = UInt8(y * 255 / (h - 1)); bytes[j+2] = 80
                    } }
                    bytes.withUnsafeBytes { ptr in
                        let bitmap = CGContext(data: UnsafeMutableRawPointer(mutating: ptr.baseAddress!), width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
                        ctx.draw(bitmap.makeImage()!, in: CGRect(x: 0, y: 0, width: w, height: h))
                    }
                } else {
                    ctx.setFillColor(CGColor(gray: 0.12, alpha: 1)); ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
                    for row in 0..<24 {
                        ctx.setFillColor(CGColor(red: CGFloat(row % 5) / 5, green: 0.3, blue: 0.5, alpha: 1))
                        ctx.fill(CGRect(x: 80, y: 30 + row * 48, width: 1400 - row * 15, height: 28))
                    }
                    ctx.setFillColor(CGColor(red: CGFloat(i % 251) / 250, green: CGFloat(i / 251) / 4, blue: 0.9, alpha: 1))
                    ctx.fill(CGRect(x: 1500, y: 100, width: 300, height: 200))
                }
                let id = String(format: "frame-%03d", i + 1), path = "frames/\(id).png"
                try Images.png(ctx.makeImage()!, to: root.appendingPathComponent(path))
                session.frames.append(Frame(id: id, timestampMS: i * 1000, name: "Generated state \(i+1)", imagePath: path, width: w, height: h, displayScale: 2, captureReason: "synthetic_fixture"))
                if !gradient { _ = try session.addAnnotation(frameID: id, kind: .rectangle, region: Region(x: 0.78, y: 0.08, width: 0.16, height: 0.18), instruction: "Inspect generated state \(i+1).") }
            }
        }
        try SessionStore.save(session, to: root)
    }
    static func images(at root: URL) async throws -> [String: Any] {
        var session = try SessionStore.load(from: root)
        guard let frame = session.frames.first else { throw LensError.invalid("Empty fixture.") }
        let pipeline = ImagePipeline(), iterations = 30
        func elapsed(_ start: UInt64) -> Double { Double(DispatchTime.now().uptimeNanoseconds - start) / 1_000_000 }
        var legacy: [Double] = [], optimized: [Double] = [], geometry: [Double] = []
        let request = EditorRenderRequest(source: root, revision: 0, frame: frame, annotations: session.annotations)
        let coldStart = DispatchTime.now().uptimeNanoseconds
        _ = try await pipeline.render(request)
        let cold = elapsed(coldStart)
        // Same image and marks, same process, alternating legacy/optimized edits to reduce ordering bias.
        for i in 0..<iterations {
            let start = DispatchTime.now().uptimeNanoseconds
            try autoreleasepool {
                let image = try Images.load(SessionStore.resolve(frame.imagePath, in: root))
                _ = try Images.render(image, annotations: session.annotations.filter { $0.frameID == frame.id }, overlays: true, labels: false)
            }
            legacy.append(elapsed(start))
            let nextStart = DispatchTime.now().uptimeNanoseconds
            if let index = session.annotations.firstIndex(where: { $0.frameID == frame.id }) { session.annotations[index].instruction = "Note \(i)" }
            let next = EditorRenderRequest(source: root, revision: 0, frame: frame, annotations: session.annotations)
            if next != request { _ = try await pipeline.render(next) }
            optimized.append(elapsed(nextStart))
        }
        let noteDecodes = await pipeline.editorDecodes, noteRenders = await pipeline.editorRenders
        for i in 0..<iterations {
            let mark = Annotation(id: "CL-001", frameID: frame.id, kind: .rectangle, region: Region(x: Double(i) / 1000, y: 0.1, width: 0.2, height: 0.2))
            let start = DispatchTime.now().uptimeNanoseconds
            _ = try await pipeline.render(EditorRenderRequest(source: root, revision: 0, frame: frame, annotations: [mark]))
            geometry.append(elapsed(start))
        }
        let thumbStart = DispatchTime.now().uptimeNanoseconds
        for frame in session.frames { _ = try await pipeline.thumbnail(at: SessionStore.resolve(frame.imagePath, in: root)) }
        let thumbTime = elapsed(thumbStart), thumbBytes = await pipeline.thumbnailBytes
        func stats(_ values: [Double]) -> [String: Any] {
            let sorted = values.sorted()
            return ["n": values.count, "mean_ms": values.reduce(0, +) / Double(values.count), "p50_ms": sorted[sorted.count / 2], "p95_ms": sorted[min(sorted.count - 1, Int(Double(sorted.count) * 0.95))], "max_ms": sorted.last!]
        }
        return ["kind": "generated-image-workload", "frames": session.frames.count, "width": frame.width, "height": frame.height,
                "legacy_note_image_work": stats(legacy), "optimized_note_image_work": stats(optimized), "geometry_render": stats(geometry),
                "cold_editor_ms": cold, "editor_decodes_after_notes": noteDecodes, "editor_renders_after_notes": noteRenders,
                "thumbnail_sweep_ms": thumbTime, "retained_thumbnail_bytes": thumbBytes, "thumbnail_limit_bytes": 32 * 1024 * 1024,
                "limitations": "Image-work microbenchmark; excludes persistence, SwiftUI layout, keyboard/display latency, zoom/pan FPS, screen capture and human/agent savings. Generated compressible 2x frames."]
    }
}
