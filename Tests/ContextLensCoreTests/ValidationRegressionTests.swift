import XCTest
@testable import ContextLensCore

final class ValidationRegressionTests: XCTestCase {
    func testInvalidStrokeDoesNotConsumeAnIssueID() throws {
        var session = Session(id: "validation")
        session.frames = [Frame(id: "f", timestampMS: 0, name: "", imagePath: "f.png", width: 10, height: 10)]
        let region = Region(x: 0, y: 0, width: 1, height: 1)
        for point in [Point(x: .nan, y: 0), Point(x: 0, y: .infinity), Point(x: -0.1, y: 0), Point(x: 0, y: 1.1)] {
            XCTAssertThrowsError(try session.addAnnotation(frameID: "f", kind: .highlight, region: region, points: [point]))
            XCTAssertTrue(session.annotations.isEmpty)
            XCTAssertEqual(session.nextIssueNumber, 1)
        }
    }
    func testDifferenceThresholdAndPartialTiles() throws {
        let a = try LumaFrame(width: 11, height: 11, pixels: Array(repeating: 0, count: 121))
        var pixels = a.pixels; pixels[120] = 17
        XCTAssertEqual(Difference.compare(a, try LumaFrame(width: 11, height: 11, pixels: pixels)).changedPixels, 0)
        pixels[120] = 18
        let diff = Difference.compare(a, try LumaFrame(width: 11, height: 11, pixels: pixels))
        XCTAssertEqual(diff.changedPixels, 1); XCTAssertEqual(diff.regional, 1); XCTAssertEqual(diff.global, 1.0 / 121)
    }
    func testSessionRejectsEscapingSymlink() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createSymbolicLink(at: root.appendingPathComponent("outside"), withDestinationURL: root.deletingLastPathComponent())
        XCTAssertThrowsError(try SessionStore.resolve("outside/private.png", in: root))
    }
}

extension ValidationRegressionTests {
    func testLargeIssueCountersDoNotTruncateTo32Bits() throws {
        var s = Session(id: "large-counter")
        s.frames = [Frame(id: "f", timestampMS: 0, name: "", imagePath: "f.png", width: 1, height: 1)]
        s.nextIssueNumber = Int(Int32.max) + 1
        let id = try s.addAnnotation(frameID: "f", kind: .rectangle, region: Region(x: 0, y: 0, width: 1, height: 1))
        XCTAssertEqual(id, "CL-2147483648"); XCTAssertNoThrow(try s.validate())
    }
}
