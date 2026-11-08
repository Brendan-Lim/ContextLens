import XCTest
@testable import ContextLensCore

final class NamingTests: XCTestCase {
    func testClickedControlNamesTheState() {
        XCTAssertEqual(StateNamer.name(sequence: 3, reason: "visual_change", windowTitle: "Checkout", previousTitle: "Checkout", clickedLabel: "  Place\norder "), "Clicked “Place order”")
    }
    func testFirstStateAndTitleChangesUseTheWindowTitle() {
        XCTAssertEqual(StateNamer.name(sequence: 1, reason: "initial", windowTitle: "Checkout", previousTitle: nil, clickedLabel: nil), "Checkout")
        XCTAssertEqual(StateNamer.name(sequence: 2, reason: "visual_change", windowTitle: "Order placed", previousTitle: "Checkout", clickedLabel: nil), "Order placed")
        XCTAssertEqual(StateNamer.name(sequence: 1, reason: "initial", windowTitle: nil, previousTitle: nil, clickedLabel: nil), "Start")
    }
    func testFallbacksKeepACounter() {
        XCTAssertEqual(StateNamer.name(sequence: 4, reason: "visual_change", windowTitle: "Checkout", previousTitle: "Checkout", clickedLabel: ""), "State 4")
        XCTAssertEqual(StateNamer.name(sequence: 5, reason: "manual", windowTitle: "Checkout", previousTitle: "Checkout", clickedLabel: nil), "Snapshot 5")
        XCTAssertEqual(StateNamer.name(sequence: 6, reason: "stop_flush", windowTitle: "Checkout", previousTitle: "Checkout", clickedLabel: nil), "Last state")
    }
    func testLongLabelsAreShortened() {
        let name = StateNamer.name(sequence: 2, reason: "visual_change", windowTitle: nil, previousTitle: nil, clickedLabel: String(repeating: "word ", count: 20))
        XCTAssertEqual(name.count, "Clicked “”".count + 32); XCTAssertTrue(name.hasSuffix("…”"))
    }
    func testPackageFolderIsReadableAndDated() {
        var session = Session()
        session.frames = [Frame(id: "frame-001", timestampMS: 0, name: "", imagePath: "frames/frame-001.png", width: 1, height: 1, windowTitle: "Café Checkout — Acme Store", applicationName: "Safari")]
        let date = Date(timeIntervalSince1970: 1_794_044_460) // 2026-11-07 09:41 UTC
        XCTAssertEqual(PackageName.folder(for: session, at: date, timeZone: TimeZone(identifier: "UTC")!), "contextlens-cafe-checkout-acme-store-2026-11-07-0941")
        session.frames[0].windowTitle = "設定"
        XCTAssertEqual(PackageName.folder(for: session, at: date, timeZone: TimeZone(identifier: "UTC")!), "contextlens-safari-2026-11-07-0941")
        XCTAssertEqual(PackageName.folder(for: Session(), at: date, timeZone: TimeZone(identifier: "UTC")!), "contextlens-session-2026-11-07-0941")
    }
    func testPackageFolderNeverReusesAnExistingFolder() throws {
        let parent = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: parent.appendingPathComponent("pkg"), withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: parent) }
        XCTAssertEqual(PackageName.unique("pkg", in: parent).lastPathComponent, "pkg-2")
        XCTAssertEqual(PackageName.unique("other", in: parent).lastPathComponent, "other")
    }
    func testPromptQuotesThePathAndLeadsWithTheTask() {
        let plain = ContextReport.instruction(path: "/Users/me/My App/pkg")
        XCTAssertTrue(plain.hasPrefix("Read `/Users/me/My App/pkg/context.md`"))
        let tasked = ContextReport.instruction(path: "/p", task: "  Fix the button alignment.\n")
        XCTAssertTrue(tasked.hasPrefix("Fix the button alignment.\n\nRead `/p/context.md`"))
        XCTAssertEqual(ContextReport.instruction(path: "/p", task: "   "), ContextReport.instruction(path: "/p"))
    }
}
