import XCTest
import CoreGraphics
import ContextLensCore
@testable import ContextLensImaging

final class ImagePipelineTests: XCTestCase {
    func fixture() throws -> (Session, URL) {
        let (session, root, _) = try ExportTests().fixture()
        return (session, root)
    }
    func testThumbnailBoundCacheAndRevision() async throws {
        let (s, root) = try fixture(); defer { try? FileManager.default.removeItem(at: root) }
        let pipeline = ImagePipeline(thumbnailLimit: 64 * 1024)
        let url = root.appendingPathComponent(s.frames[0].imagePath)
        let first = try await pipeline.thumbnail(at: url, maximum: 40)
        XCTAssertLessThanOrEqual(first.width, 40); XCTAssertLessThanOrEqual(first.height, 40)
        _ = try await pipeline.thumbnail(at: url, maximum: 40)
        var decodes = await pipeline.thumbnailDecodes; XCTAssertEqual(decodes, 1)
        _ = try await pipeline.thumbnail(at: url, revision: 1, maximum: 40)
        decodes = await pipeline.thumbnailDecodes; XCTAssertEqual(decodes, 2)
        let bytes = await pipeline.thumbnailBytes; XCTAssertLessThanOrEqual(bytes, 64 * 1024)
        await pipeline.clear()
        let cleared = await pipeline.thumbnailBytes; XCTAssertEqual(cleared, 0)
    }
    func testOversizedThumbnailIsNotRetained() async throws {
        let (s, root) = try fixture(); defer { try? FileManager.default.removeItem(at: root) }
        let pipeline = ImagePipeline(thumbnailLimit: 1), url = root.appendingPathComponent(s.frames[0].imagePath)
        _ = try await pipeline.thumbnail(at: url); _ = try await pipeline.thumbnail(at: url)
        let bytes = await pipeline.thumbnailBytes, decodes = await pipeline.thumbnailDecodes
        XCTAssertEqual(bytes, 0); XCTAssertEqual(decodes, 2)
    }
    func testGeometryEditsReuseOneDecodedSourceAndRevisionReloadsRedaction() async throws {
        let (s, root) = try fixture(); defer { try? FileManager.default.removeItem(at: root) }
        let pipeline = ImagePipeline(), f = s.frames[0]
        let first = EditorRenderRequest(source: root, revision: 0, frame: f, annotations: [])
        _ = try await pipeline.render(first)
        let mark = Annotation(id: "CL-001", frameID: f.id, kind: .rectangle, region: Region(x: 0.1, y: 0.1, width: 0.2, height: 0.2))
        _ = try await pipeline.render(EditorRenderRequest(source: root, revision: 0, frame: f, annotations: [mark]))
        var decodes = await pipeline.editorDecodes; XCTAssertEqual(decodes, 1)
        let redaction = Annotation(id: "CL-002", frameID: f.id, kind: .redaction, region: Region(x: 0, y: 0, width: 1, height: 1))
        let black = try Images.render(Images.load(root.appendingPathComponent(f.imagePath)), annotations: [redaction], overlays: false)
        try Images.png(black, to: root.appendingPathComponent(f.imagePath))
        let result = try await pipeline.render(EditorRenderRequest(source: root, revision: 1, frame: f, annotations: []))
        decodes = await pipeline.editorDecodes; XCTAssertEqual(decodes, 2)
        XCTAssertEqual(ExportTests().rgb(result, x: 50, y: 50), [0, 0, 0])
    }
    func testCancelledQueuedWorkDoesNotDecode() async throws {
        let (s, root) = try fixture(); defer { try? FileManager.default.removeItem(at: root) }
        let pipeline = ImagePipeline()
        let request = EditorRenderRequest(source: root, revision: 0, frame: s.frames[0], annotations: [])
        let task = Task {
            withUnsafeCurrentTask { $0?.cancel() }
            return try await pipeline.render(request)
        }
        do { _ = try await task.value; XCTFail("Expected cancellation") } catch is CancellationError { }
        let decodes = await pipeline.editorDecodes; XCTAssertEqual(decodes, 0)
    }
    func testCorruptMissingAndInvalidSizeFailWithoutCaching() async throws {
        let (s, root) = try fixture(); defer { try? FileManager.default.removeItem(at: root) }
        let pipeline = ImagePipeline(), url = root.appendingPathComponent("broken.png")
        try Data("not an image".utf8).write(to: url)
        for (path, size) in [(url, 520), (root.appendingPathComponent("missing.png"), 520), (url, 0)] {
            do { _ = try await pipeline.thumbnail(at: path, maximum: size); XCTFail("Expected decode error") } catch { }
        }
        var frame = s.frames[0]; frame.width += 1
        do { _ = try await pipeline.render(EditorRenderRequest(source: root, revision: 0, frame: frame, annotations: [])); XCTFail("Expected dimensions error") } catch { }
        let decodes = await pipeline.editorDecodes; XCTAssertEqual(decodes, 0)
    }
    func testExportCancelledBeforeWritingLeavesNoStagingDirectory() async throws {
        let (s, root) = try fixture(); defer { try? FileManager.default.removeItem(at: root) }
        let plan = try ExportPlan.prepare(s, source: root, options: .allFrames)
        let task = Task {
            withUnsafeCurrentTask { $0?.cancel() }
            return try Exporter.export(plan, destination: root.appendingPathComponent("export"))
        }
        do { _ = try await task.value; XCTFail("Expected cancellation") } catch is CancellationError { }
        XCTAssertFalse(try FileManager.default.contentsOfDirectory(atPath: root.path).contains { $0 == "export" || $0.hasPrefix(".contextlens-") })
    }
    func testExportSourceChangedAfterPreviewFailsAtomically() throws {
        let (s, root) = try fixture(); defer { try? FileManager.default.removeItem(at: root) }
        let plan = try ExportPlan.prepare(s, source: root, options: .allFrames)
        try Data("corrupted after preview".utf8).write(to: root.appendingPathComponent(s.frames[0].imagePath))
        XCTAssertThrowsError(try Exporter.export(plan, destination: root.appendingPathComponent("export")))
        XCTAssertFalse(try FileManager.default.contentsOfDirectory(atPath: root.path).contains { $0 == "export" || $0.hasPrefix(".contextlens-") })
    }
}

extension ImagePipelineTests {
    func testRendererRejectsInvalidGeometryBeforeDrawing() throws {
        let (_, root, image) = try ExportTests().fixture(); defer { try? FileManager.default.removeItem(at: root) }
        for kind in AnnotationKind.allCases {
            let invalid = Annotation(id: "CL-001", frameID: "f", kind: kind, region: Region(x: -0.1, y: 0, width: 0.2, height: 0.2))
            XCTAssertThrowsError(try Images.render(image, annotations: [invalid], overlays: true))
        }
        let stroke = Annotation(id: "CL-002", frameID: "f", kind: .highlight, region: Region(x: 0, y: 0, width: 1, height: 1), points: [Point(x: 2, y: 0)])
        XCTAssertThrowsError(try Images.render(image, annotations: [stroke], overlays: true))
    }
}
