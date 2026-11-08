import XCTest
@testable import ContextLensCore

extension CoreTests {
    func testOnlyRectangleAndHighlighterAreCreationTools() throws {
        XCTAssertEqual(AnnotationKind.drawingTools, [.rectangle, .highlight])
        for kind in ["arrow", "text", "marker", "redaction"] {
            XCTAssertNoThrow(try JSONDecoder().decode(AnnotationKind.self, from: Data("\"\(kind)\"".utf8)))
        }
    }
    func testHorizontalHighlightBoundsIncludeStrokeAndStayInsideImage() throws {
        let points = [Point(x: 0, y: 0), Point(x: 0.8, y: 0)]
        let r = AnnotationGeometry.highlightBounds(points: points, imageWidth: 1000, imageHeight: 600)!
        try r.validate(); XCTAssertEqual(r.x, 0); XCTAssertEqual(r.y, 0)
        XCTAssertGreaterThan(r.height, 0); XCTAssertGreaterThan(r.width, 0.8)
        XCTAssertNil(AnnotationGeometry.highlightBounds(points: [], imageWidth: 1000, imageHeight: 600))
    }
    func testReportPresentsInstructionsBeforeTimelineAndDoesNotInventBlankIntent() throws {
        var s = session(); s.task = "Update the local dashboard."
        let r = Region(x: 0.123456789, y: 0.1, width: 0.1, height: 0.1)
        _ = try s.addAnnotation(frameID: "frame-001", kind: .rectangle, region: r)
        _ = try s.addAnnotation(frameID: "frame-001", kind: .rectangle, region: r, instruction: "Make the title bigger")
        let text = ContextReport.markdown(s)
        XCTAssertTrue(text.contains(s.task!)); XCTAssertFalse(text.contains("0.123456789"))
        XCTAssertTrue(text.contains("CL-001")); XCTAssertTrue(text.contains("visual references, not change requests"))
        XCTAssertLessThan(text.range(of: "Make the title bigger")!.lowerBound, text.range(of: "## Visual evidence")!.lowerBound)
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: folder) }
        try SessionStore.save(s, to: folder); XCTAssertEqual(try SessionStore.load(from: folder).task, s.task)
    }
}
