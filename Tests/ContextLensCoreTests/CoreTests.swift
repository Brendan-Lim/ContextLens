import XCTest
@testable import ContextLensCore

final class CoreTests: XCTestCase {
    func image(_ edits: [(Int, UInt8)] = []) throws -> LumaFrame {
        var p = [UInt8](repeating: 100, count: 10000)
        for (i,v) in edits { p[i] = v }
        return try LumaFrame(width: 100, height: 100, pixels: p)
    }
    func testInitialAndDuplicateFrames() throws {
        var s = FrameSelector(); let a = try image()
        XCTAssertEqual(s.observe(a, at: 0)?.reason, "initial")
        for time in stride(from: 100, to: 5000, by: 100) { XCTAssertNil(s.observe(a, at: time)) }
        XCTAssertEqual(s.committedCount, 1)
    }
    func testRegionalCheckboxChangeAndSettling() throws {
        let a = try image(), b = try image((0..<5).flatMap { y in (0..<5).map { (y*100+$0, UInt8(230)) } })
        let diff = Difference.compare(a, b)
        XCTAssertLessThan(diff.global, 0.025); XCTAssertGreaterThan(diff.regional, 0.16)
        var s = FrameSelector(); _ = s.observe(a, at: 0)
        XCTAssertNil(s.observe(b, at: 100)); XCTAssertNil(s.observe(b, at: 300))
        XCTAssertEqual(s.observe(b, at: 500)?.reason, "visual_change")
    }
    func testNoiseAndCaretAreIgnored() throws {
        var s = FrameSelector(); _ = s.observe(try image(), at: 0)
        let noise = try LumaFrame(width: 100, height: 100, pixels: Array(repeating: 108, count: 10000))
        XCTAssertNil(s.observe(noise, at: 100)); XCTAssertNil(s.observe(try image([(1, 255), (101,255)]), at: 1000))
    }
    func testAnimationWaitAndStopFlush() throws {
        var s = FrameSelector(); _ = s.observe(try image(), at: 0)
        let b = try LumaFrame(width: 100, height: 100, pixels: Array(repeating: 220, count: 10000))
        XCTAssertNil(s.observe(b, at: 100)); XCTAssertNotNil(s.flush(b)); XCTAssertNil(s.flush(b))
        var animated = FrameSelector(); _ = animated.observe(try image(), at: 0)
        for t in stride(from: 100, through: 1500, by: 100) {
            let im = try LumaFrame(width: 100, height: 100, pixels: Array(repeating: t % 200 == 0 ? 180 : 250, count: 10000))
            XCTAssertNil(animated.observe(im, at: t))
        }
        XCTAssertNotNil(animated.observe(b, at: 1600))
    }
    func testManualLimitResizeAndOutOfOrder() throws {
        var s = FrameSelector(); s.maximumFrames = 2
        let a = try image(); _ = s.observe(a, at: 10)
        XCTAssertNil(s.observe(a, at: 9, manual: true))
        XCTAssertEqual(s.observe(a, at: 20, manual: true)?.reason, "manual")
        XCTAssertNil(s.observe(a, at: 30, manual: true))
        let b = try LumaFrame(width: 10, height: 10, pixels: Array(repeating: 100, count: 100))
        XCTAssertEqual(Difference.compare(a, b).global, 1)
    }
    func session() -> Session {
        var s = Session(id: "test", createdAt: Date(timeIntervalSince1970: 1700000000))
        s.frames.append(Frame(id: "frame-001", timestampMS: 0, name: "Observed", imagePath: "frames/frame-001.png", width: 100, height: 100))
        return s
    }
    func testStableIDsAndBounds() throws {
        var s = session()
        let r = Region(x: 0.2, y: 0.3, width: 0.1, height: 0.1)
        XCTAssertEqual(try s.addAnnotation(frameID: "frame-001", kind: .rectangle, region: r), "CL-001")
        s.annotations.removeAll()
        XCTAssertEqual(try s.addAnnotation(frameID: "frame-001", kind: .rectangle, region: r), "CL-002")
        XCTAssertThrowsError(try s.addAnnotation(frameID: "missing", kind: .rectangle, region: r))
        XCTAssertThrowsError(try Region(x: 0.99, y: 0, width: 0.2, height: 0.2).validate())
        XCTAssertThrowsError(try Region(x: .nan, y: 0, width: 0.2, height: 0.2).validate())
        try s.validate()
        s.nextIssueNumber = 1; XCTAssertThrowsError(try s.validate())
    }
    func testStorageRoundTripAndTraversal() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let s = session(); try SessionStore.save(s, to: root)
        XCTAssertEqual(try SessionStore.load(from: root), s)
        for path in ["../secret.png", "/tmp/a.png", "frames/../a.png", "frames//a.png", "file:a", "a\\b"] { XCTAssertThrowsError(try SessionStore.resolve(path, in: root)) }
        try FileManager.default.createSymbolicLink(at: root.appendingPathComponent("escape"), withDestinationURL: URL(fileURLWithPath: "/tmp"))
        XCTAssertThrowsError(try SessionStore.resolve("escape/a.png", in: root))
    }
    func testCaseInsensitiveIdentifierCollisionsAreRejected() throws {
        var s = session(); var duplicate = s.frames[0]; duplicate.id = "FRAME-001"; s.frames.append(duplicate)
        XCTAssertThrowsError(try s.validate())
    }
    func testReportsDoNotInventIntentOrEvents() throws {
        var s = session()
        XCTAssertTrue(ContextReport.markdown(s).contains("No explicit change request"))
        XCTAssertFalse(ContextReport.markdown(s).contains("clicked"))
        _ = try s.addAnnotation(frameID: "frame-001", kind: .rectangle, region: Region(x: 0, y: 0, width: 0.2, height: 0.2), instruction: "Move right")
        XCTAssertTrue(ContextReport.markdown(s).contains("Move right"))
        s.frames[0].selected = false; XCTAssertFalse(ContextReport.markdown(s).contains("Move right"))
    }
}
