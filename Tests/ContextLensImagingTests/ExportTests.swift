import XCTest
import CoreGraphics
import ContextLensCore
@testable import ContextLensImaging

final class ExportTests: XCTestCase {
    func fixture() throws -> (Session, URL, CGImage) {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root.appendingPathComponent("frames"), withIntermediateDirectories: true)
        let ctx = CGContext(data: nil, width: 100, height: 100, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
        ctx.setFillColor(CGColor(red: 1, green: 0, blue: 0, alpha: 1)); ctx.fill(CGRect(x: 0, y: 0, width: 100, height: 100))
        let image = ctx.makeImage()!; try Images.png(image, to: root.appendingPathComponent("frames/frame-001.png"))
        var s = Session(id: "test-export")
        s.frames = [Frame(id: "frame-001", timestampMS: 0, name: "Fixture", imagePath: "frames/frame-001.png", width: 100, height: 100)]
        return (s,root,image)
    }
    func rgb(_ image: CGImage, x: Int, y: Int) -> [UInt8] {
        var bytes = [UInt8](repeating: 0, count: image.width * image.height * 4)
        bytes.withUnsafeMutableBytes { data in
            let ctx = CGContext(data: data.baseAddress, width: image.width, height: image.height, bitsPerComponent: 8, bytesPerRow: image.width*4, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
            ctx.draw(image, in: CGRect(x: 0, y: 0, width: image.width, height: image.height))
        }
        let i = (y*image.width+x)*4
        return Array(bytes[i..<i+3])
    }
    func testRedactionBurnsFullImageAndUsesTopLeftCoordinates() throws {
        let (_, root, img) = try fixture(); defer { try? FileManager.default.removeItem(at: root) }
        let a = Annotation(id: "CL-001", frameID: "frame-001", kind: .redaction, region: Region(x: 0.1, y: 0.1, width: 0.2, height: 0.2))
        let result = try Images.render(img, annotations: [a], overlays: false)
        XCTAssertEqual(rgb(result, x: 20, y: 20), [0,0,0]); XCTAssertEqual(rgb(result, x: 20, y: 80), rgb(img, x: 20, y: 80))
    }
    func testAllOutputsRedactedPortableAndAtomic() throws {
        var (s, root, baseline) = try fixture(); defer { try? FileManager.default.removeItem(at: root) }
        _ = try s.addAnnotation(frameID: "frame-001", kind: .redaction, region: Region(x: 0.1, y: 0.1, width: 0.2, height: 0.2))
        _ = try s.addAnnotation(frameID: "frame-001", kind: .rectangle, region: Region(x: 0.1, y: 0.1, width: 0.2, height: 0.2), instruction: "Check region")
        let dest = root.appendingPathComponent("export")
        let m = try Exporter.export(s, source: root, destination: dest)
        XCTAssertEqual(m.issues.count, 1); XCTAssertEqual(m.frames.count, 1)
        let paths = [m.frames[0].imagePath, m.issues[0].annotatedPath, m.issues[0].cropPath]
        for path in paths {
            let img = try Images.load(dest.appendingPathComponent(path))
            XCTAssertEqual(rgb(img, x: 20, y: 20), [0,0,0], "Unredacted \(path)")
        }
        let original = try Images.load(root.appendingPathComponent(s.frames[0].imagePath))
        XCTAssertEqual(rgb(original, x: 20, y: 20), rgb(baseline, x: 20, y: 20))
        XCTAssertThrowsError(try Exporter.export(s, source: root, destination: dest, options: .allFrames))
        XCTAssertFalse(try String(contentsOf: dest.appendingPathComponent("manifest.json")).contains(root.path))
        let moved = root.appendingPathComponent("moved"); try FileManager.default.moveItem(at: dest, to: moved)
        for path in paths { XCTAssertNoThrow(try Images.load(SessionStore.resolve(path, in: moved))) }
    }
    func testFailedExportLeavesNoPartialDestination() throws {
        var (s, root, _) = try fixture(); defer { try? FileManager.default.removeItem(at: root) }
        s.frames[0].width = 101
        let dest = root.appendingPathComponent("broken")
        XCTAssertThrowsError(try Exporter.export(s, source: root, destination: dest, options: .allFrames))
        XCTAssertFalse(FileManager.default.fileExists(atPath: dest.path))
        XCTAssertFalse(try FileManager.default.contentsOfDirectory(atPath: root.path).contains { $0.hasPrefix(".contextlens-") })
    }
    func testCropClampsEdgesAndLumaDimensions() throws {
        let (_, root, img) = try fixture(); defer { try? FileManager.default.removeItem(at: root) }
        let crop = try Images.crop(img, around: Region(x: 0, y: 0, width: 0.2, height: 0.2))
        XCTAssertEqual(crop.width, 44); XCTAssertEqual(crop.height, 44)
        let luma = try Images.luma(img); XCTAssertEqual(luma.width, 240); XCTAssertEqual(luma.height, 240)
    }
}

extension ExportTests {
    func testStateOverviewKeepsAllMarksAndBurnsRedactions() throws {
        var (s, root, baseline) = try fixture(); defer { try? FileManager.default.removeItem(at: root) }
        _ = try s.addAnnotation(frameID: "frame-001", kind: .redaction, region: Region(x: 0.1, y: 0.1, width: 0.2, height: 0.2), instruction: "PRIVATE REDACTION LABEL")
        let box = try s.addAnnotation(frameID: "frame-001", kind: .rectangle, region: Region(x: 0.6, y: 0.1, width: 0.2, height: 0.2), instruction: "Align Save")
        let highlight = try s.addAnnotation(frameID: "frame-001", kind: .highlight, region: Region(x: 0.55, y: 0.55, width: 0.3, height: 0.3), points: [Point(x: 0.6, y: 0.6), Point(x: 0.8, y: 0.8)])
        let dest = root.appendingPathComponent("new package")
        let manifest = try Exporter.export(s, source: root, destination: dest)
        let overview = try Images.load(dest.appendingPathComponent(ContextReport.stateImagePath(frameID: "frame-001")))
        XCTAssertEqual(overview.width, baseline.width); XCTAssertEqual(overview.height, baseline.height)
        XCTAssertEqual(rgb(overview, x: 20, y: 20), [0,0,0])
        XCTAssertNotEqual(rgb(overview, x: 60, y: 20), rgb(baseline, x: 60, y: 20))
        XCTAssertNotEqual(rgb(overview, x: 70, y: 70), rgb(baseline, x: 70, y: 70))
        XCTAssertEqual(manifest.issues.map { $0.annotation.id }, [box, highlight])
        for issue in manifest.issues {
            XCTAssertNoThrow(try Images.load(dest.appendingPathComponent(issue.annotatedPath)))
            XCTAssertNoThrow(try Images.load(dest.appendingPathComponent(issue.cropPath)))
        }
        let brief = try String(contentsOf: dest.appendingPathComponent("context.md"))
        XCTAssertTrue(brief.contains(box)); XCTAssertTrue(brief.contains(highlight))
        XCTAssertFalse(brief.contains("PRIVATE REDACTION LABEL"))
        let metadata = try String(contentsOf: dest.appendingPathComponent("metadata/session.json"))
        XCTAssertFalse(metadata.contains("PRIVATE REDACTION LABEL"))
    }
    func testOptionalTimelinePreservesEverySelectedStateWithoutExpandingBrief() throws {
        var (s, root, _) = try fixture(); defer { try? FileManager.default.removeItem(at: root) }
        s.frames[0].event = "Control opened"
        var second = s.frames[0]; second.id = "frame-002"; second.name = "Next state"; second.timestampMS = 200; s.frames.append(second)
        _ = try s.addAnnotation(frameID: "frame-001", kind: .rectangle, region: Region(x: 0, y: 0, width: 0.2, height: 0.2), instruction: "Fix this")
        let dest = root.appendingPathComponent("export")
        _ = try Exporter.export(s, source: root, destination: dest, options: .allFrames)
        let timeline = try String(contentsOf: dest.appendingPathComponent("metadata/timeline.md"))
        XCTAssertTrue(timeline.contains("frames/frame-001.png")); XCTAssertTrue(timeline.contains("frames/frame-002.png"))
        XCTAssertTrue(timeline.contains("200 ms")); XCTAssertTrue(timeline.contains("Control opened"))
        let brief = try String(contentsOf: dest.appendingPathComponent("context.md"))
        XCTAssertFalse(brief.contains("Control opened")); XCTAssertFalse(brief.contains("Next state"))
        XCTAssertTrue(brief.contains("metadata/timeline.md"))
    }
}
