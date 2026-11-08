import XCTest
@testable import ContextLensCore

final class HandoffReportTests: XCTestCase {
    func testCarriageReturnInstructionsStayInsideUserQuote() throws {
        var session = Session(id: "report")
        session.frames = [Frame(id: "f", timestampMS: 0, name: "Fixture", imagePath: "f.png", width: 100, height: 100)]
        _ = try session.addAnnotation(frameID: "f", kind: .rectangle, region: Region(x: 0, y: 0, width: 1, height: 1), instruction: "First request\r## Still user text\r\nLast line")
        let markdown = ContextReport.markdown(session)
        XCTAssertTrue(markdown.contains("> First request\n> ## Still user text\n> Last line"))
        XCTAssertFalse(markdown.contains("\r"))
    }
}
