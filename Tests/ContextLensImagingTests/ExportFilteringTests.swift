import XCTest
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers
import ContextLensCore
@testable import ContextLensImaging

extension ExportTests {
    func filterFixture() throws -> (Session, URL) {
        var (s, root, a) = try fixture()
        let ctx = CGContext(data: nil, width: 100, height: 100, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
        ctx.setFillColor(CGColor(gray: 0.5, alpha: 1)); ctx.fill(CGRect(x: 0, y: 0, width: 100, height: 100))
        let b = ctx.makeImage()!
        ctx.setFillColor(CGColor(gray: 1, alpha: 1)); ctx.fill(CGRect(x: 50, y: 50, width: 1, height: 1))
        let c = ctx.makeImage()!
        s.frames = []
        for i in 1...8 {
            let id = "frame-\(i)", path = "frames/\(id).png"
            try Images.png(i <= 4 ? a : (i <= 6 ? b : c), to: root.appendingPathComponent(path))
            s.frames.append(Frame(id: id, timestampMS: i*100, name: "State \(i)", imagePath: path, width: 100, height: 100, selected: i != 8))
        }
        _ = try s.addAnnotation(frameID: "frame-2", kind: .rectangle, region: Region(x: 0.1, y: 0.1, width: 0.3, height: 0.3))
        _ = try s.addAnnotation(frameID: "frame-3", kind: .highlight, region: Region(x: 0.2, y: 0.2, width: 0.4, height: 0.4), points: [Point(x: 0.2, y: 0.2), Point(x: 0.6, y: 0.6)], instruction: "Keep this readable")
        _ = try s.addAnnotation(frameID: "frame-8", kind: .marker, region: Region(x: 0.1, y: 0.1, width: 0.1, height: 0.1), instruction: "Not selected")
        s.task = "Improve the local fixture page."
        s.createdAt = Date(timeIntervalSince1970: 1700000000)
        return (s, root)
    }
    func testEveryExportFilterCombinationPreservesAnnotatedDuplicates() throws {
        let (s, root) = try filterFixture(); defer { try? FileManager.default.removeItem(at: root) }
        try SessionStore.save(s, to: root)
        let before = try Data(contentsOf: root.appendingPathComponent("session.json"))
        for annotatedOnly in [false, true] {
            for excludeDuplicates in [false, true] {
                let options = ExportOptions(annotatedOnly: annotatedOnly, excludeDuplicates: excludeDuplicates)
                let plan = try ExportPlan.prepare(s, source: root, options: options)
                let expected = annotatedOnly ? [2,3] : (excludeDuplicates ? [2,3,5,7] : [1,2,3,4,5,6,7])
                XCTAssertEqual(plan.session.frames.map(\.id), expected.map { "frame-\($0)" })
                XCTAssertEqual(plan.summary.selectedFrames, 7)
                XCTAssertEqual(plan.summary.excludedUnannotated, annotatedOnly ? 5 : 0)
                XCTAssertEqual(plan.summary.excludedDuplicates, !annotatedOnly && excludeDuplicates ? 3 : 0)
                XCTAssertEqual(plan.summary.unlabelledAnnotations, 1)
                let dest = root.appendingPathComponent("export-\(annotatedOnly)-\(excludeDuplicates)")
                let m = try Exporter.export(plan, destination: dest)
                XCTAssertEqual(m.frames, plan.session.frames); XCTAssertEqual(m.summary, plan.summary)
                XCTAssertEqual(m.issues.map { $0.annotation.id }, ["CL-001", "CL-002"])
                let report = try String(contentsOf: dest.appendingPathComponent("context.md")) + String(contentsOf: dest.appendingPathComponent("metadata/timeline.md"))
                for frame in s.frames {
                    XCTAssertEqual(report.contains("frames/\(frame.id).png"), expected.map { "frame-\($0)" }.contains(frame.id))
                }
                let raw = try JSONSerialization.jsonObject(with: Data(contentsOf: dest.appendingPathComponent("manifest.json"))) as! [String: Any]
                let issues = raw["issues"] as! [[String: Any]], index = issues[1]["annotation"] as! [String: Any]
                XCTAssertNil(index["points"]); XCTAssertNil(index["region"])
                let metadata = try JSONSerialization.jsonObject(with: Data(contentsOf: dest.appendingPathComponent("metadata/session.json"))) as! [String: Any]
                let full = metadata["annotations"] as! [[String: Any]]
                XCTAssertEqual((full[1]["points"] as! [[String: Any]]).count, 2)
            }
        }
        XCTAssertEqual(try Data(contentsOf: root.appendingPathComponent("session.json")), before)
        XCTAssertEqual(try SessionStore.load(from: root), s)
    }
    func testDecodedPixelDuplicatesIgnorePNGMetadata() throws {
        var (s, root, img) = try fixture(); defer { try? FileManager.default.removeItem(at: root) }
        let url = root.appendingPathComponent("frames/other.png")
        let dest = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil)!
        CGImageDestinationAddImage(dest, img, [kCGImagePropertyPNGDictionary: [kCGImagePropertyPNGDescription: "Different container metadata"]] as CFDictionary)
        XCTAssertTrue(CGImageDestinationFinalize(dest))
        XCTAssertNotEqual(try Data(contentsOf: url), try Data(contentsOf: root.appendingPathComponent(s.frames[0].imagePath)))
        var second = s.frames[0]; second.id = "frame-002"; second.imagePath = "frames/other.png"; s.frames.append(second)
        let plan = try ExportPlan.prepare(s, source: root, options: ExportOptions(annotatedOnly: false, excludeDuplicates: true))
        XCTAssertEqual(plan.session.frames.count, 1); XCTAssertEqual(plan.summary.excludedDuplicates, 1)
    }
    func testLegacyAnnotationAndRedactionFramesAreNeverDeduplicated() throws {
        var (s, root, _) = try fixture(); defer { try? FileManager.default.removeItem(at: root) }
        var second = s.frames[0]; second.id = "frame-002"; s.frames.append(second)
        let r = Region(x: 0.1, y: 0.1, width: 0.2, height: 0.2)
        _ = try s.addAnnotation(frameID: "frame-001", kind: .redaction, region: r)
        _ = try s.addAnnotation(frameID: "frame-002", kind: .arrow, region: r)
        for options in [ExportOptions(), ExportOptions(annotatedOnly: false, excludeDuplicates: true)] {
            let p = try ExportPlan.prepare(s, source: root, options: options)
            XCTAssertEqual(p.session.frames.count, 2); XCTAssertEqual(p.summary.excludedDuplicates, 0)
        }
    }
    func testEmptyFilterSelectionIsPreviewableButCannotExport() throws {
        let (s, root, _) = try fixture(); defer { try? FileManager.default.removeItem(at: root) }
        let plan = try ExportPlan.prepare(s, source: root)
        XCTAssertTrue(plan.session.frames.isEmpty); XCTAssertEqual(plan.summary.excludedUnannotated, 1)
        let dest = root.appendingPathComponent("empty-export")
        XCTAssertThrowsError(try Exporter.export(plan, destination: dest))
        XCTAssertFalse(FileManager.default.fileExists(atPath: dest.path))
        XCTAssertEqual(try ExportPlan.prepare(s, source: root, options: .allFrames).session.frames.count, 1)
    }
    func testHighlighterRendersStrokeRatherThanItsBoundingBox() throws {
        let (_, root, image) = try fixture(); defer { try? FileManager.default.removeItem(at: root) }
        let points = [Point(x: 0.2, y: 0.2), Point(x: 0.2, y: 0.7), Point(x: 0.7, y: 0.7)]
        let region = AnnotationGeometry.highlightBounds(points: points, imageWidth: 100, imageHeight: 100)!
        let a = Annotation(id: "CL-001", frameID: "frame-001", kind: .highlight, region: region, points: points)
        let marked = try Images.render(image, annotations: [a], overlays: true)
        let baseline = try Images.render(image, annotations: [], overlays: true)
        XCTAssertNotEqual(rgb(marked, x: 20, y: 45), rgb(baseline, x: 20, y: 45))
        XCTAssertNotEqual(rgb(marked, x: 45, y: 70), rgb(baseline, x: 45, y: 70))
        XCTAssertEqual(rgb(marked, x: 45, y: 45), rgb(baseline, x: 45, y: 45))
        // No phantom rectangle edge opposite the actual L-shaped stroke.
        XCTAssertEqual(rgb(marked, x: 70, y: 45), rgb(baseline, x: 70, y: 45))
    }
}
