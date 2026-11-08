import XCTest
@testable import ContextLensCore

final class ScrollAndReportTests: XCTestCase {
    private func frame(_ value: UInt8) throws -> LumaFrame {
        try LumaFrame(width: 100, height: 100, pixels: Array(repeating: value, count: 10000))
    }

    func testScrollingSavesOneStateAfterItStops() throws {
        var s = FrameSelector()
        XCTAssertEqual(s.observe(try frame(100), at: 0)?.reason, "initial")
        // Three seconds of scrolling through different content: no state, even past the maximum wait.
        for (i, t) in stride(from: 250, through: 3000, by: 250).enumerated() {
            XCTAssertNil(s.observe(try frame(UInt8(140 + (i % 2) * 60)), at: t, holding: true))
        }
        // Scrolling stops; the view settles and one state is saved.
        XCTAssertNil(s.observe(try frame(200), at: 3250))
        XCTAssertEqual(s.observe(try frame(200), at: 3750)?.reason, "scroll")
        XCTAssertEqual(s.committedCount, 2)
    }
    func testScrollingBackToTheStartSavesNothing() throws {
        var s = FrameSelector(); _ = s.observe(try frame(100), at: 0)
        XCTAssertNil(s.observe(try frame(200), at: 250, holding: true))
        XCTAssertNil(s.observe(try frame(100), at: 500, holding: true))
        XCTAssertNil(s.observe(try frame(100), at: 1000))
        XCTAssertNil(s.observe(try frame(100), at: 2500))
        XCTAssertEqual(s.committedCount, 1)
    }
    func testSnapshotStillWorksWhileScrolling() throws {
        var s = FrameSelector(); _ = s.observe(try frame(100), at: 0)
        XCTAssertEqual(s.observe(try frame(200), at: 250, manual: true, holding: true)?.reason, "manual")
    }
    func testStoppingMidScrollKeepsTheScrollReason() throws {
        var s = FrameSelector(); _ = s.observe(try frame(100), at: 0)
        XCTAssertNil(s.observe(try frame(200), at: 250, holding: true))
        XCTAssertEqual(s.flush(try frame(200))?.reason, "scroll")
    }
    func testScrolledStatesAreNamed() {
        XCTAssertEqual(StateNamer.name(sequence: 3, reason: "scroll", windowTitle: "Feed", previousTitle: "Feed", clickedLabel: nil), "Scrolled")
    }

    func testNotesNameTheirStateAndWhereTheMarkIs() throws {
        var session = Session()
        session.frames = [Frame(id: "frame-002", timestampMS: 0, name: "Settings", imagePath: "frames/frame-002.png", width: 10, height: 10)]
        _ = try session.addAnnotation(frameID: "frame-002", kind: .rectangle, region: Region(x: 0.05, y: 0.04, width: 0.2, height: 0.1), instruction: "Bigger title")
        _ = try session.addAnnotation(frameID: "frame-002", kind: .highlight, region: Region(x: 0.4, y: 0.8, width: 0.2, height: 0.1))
        let text = ContextReport.markdown(session)
        XCTAssertTrue(text.contains("State: Settings [frame-002]"))
        XCTAssertTrue(text.contains("Mark: Box near the top left of the window (x 5%, y 4%, 20% × 10%)"))
        XCTAssertTrue(text.contains("- CL-002: Highlight near the bottom of the window (x 40%, y 80%, 20% × 10%) in Settings [frame-002]"))
    }
    func testPlacementWording() {
        func mark(_ r: Region) -> Annotation {
            Annotation(id: "CL-001", frameID: "f", kind: .rectangle, region: r, instruction: "")
        }
        XCTAssertTrue(ContextReport.placement(mark(Region(x: 0.4, y: 0.4, width: 0.2, height: 0.2))).hasPrefix("Box near the center of the window"))
        XCTAssertTrue(ContextReport.placement(mark(Region(x: 0.7, y: 0.4, width: 0.2, height: 0.2))).hasPrefix("Box near the right side of the window"))
        XCTAssertTrue(ContextReport.placement(mark(Region(x: 0, y: 0, width: 0.9, height: 0.9))).hasPrefix("Box covering most of the window"))
    }
}
