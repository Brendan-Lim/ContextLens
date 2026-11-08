import XCTest
@testable import ContextLensCore

final class EditingStateTests: XCTestCase {
    func session() -> Session {
        var s = Session(id: "editing")
        s.frames = [Frame(id: "f", timestampMS: 0, name: "One", imagePath: "f.png", width: 100, height: 100)]
        return s
    }
    func testHistoryLimitAndRedoBranch() {
        var history = SessionHistory(limit: 2), s = session()
        for i in 1...3 { history.checkpoint(s); s.task = "\(i)" }
        s = history.undo(s)!; XCTAssertEqual(s.task, "2")
        s = history.undo(s)!; XCTAssertEqual(s.task, "1"); XCTAssertNil(history.undo(s))
        s = history.redo(s)!; XCTAssertEqual(s.task, "2")
        history.checkpoint(s); s.task = "branch"; XCTAssertFalse(history.canRedo)
        history.reset(); XCTAssertFalse(history.canUndo); XCTAssertFalse(history.canRedo)
    }
    func testUndoRedoNeverReusesDeletedIssueIDs() throws {
        var history = SessionHistory(), s = session()
        history.checkpoint(s)
        _ = try s.addAnnotation(frameID: "f", kind: .rectangle, region: Region(x: 0, y: 0, width: 1, height: 1))
        s = history.undo(s)!; XCTAssertEqual(s.nextIssueNumber, 2)
        s = history.redo(s)!; XCTAssertEqual(s.annotations.first?.id, "CL-001")
        s = history.undo(s)!; history.checkpoint(s)
        XCTAssertEqual(try s.addAnnotation(frameID: "f", kind: .rectangle, region: Region(x: 0, y: 0, width: 1, height: 1)), "CL-002")
        XCTAssertFalse(history.canRedo)
    }
    func testDisabledHistory() {
        var history = SessionHistory(limit: 0); history.checkpoint(session())
        XCTAssertFalse(history.canUndo); XCTAssertNil(history.redo(session()))
    }
    func testEditorNotesNamesTaskAndTicksDoNotChangePixels() throws {
        var s = session()
        _ = try s.addAnnotation(frameID: "f", kind: .rectangle, region: Region(x: 0, y: 0, width: 1, height: 1))
        let root = URL(fileURLWithPath: "/tmp/source")
        func request() -> EditorRenderRequest { EditorRenderRequest(source: root, revision: 0, frame: s.frames[0], annotations: s.annotations) }
        let before = request()
        s.annotations[0].instruction = "A long note"; s.annotations[0].severity = "high"
        s.task = "Task"; s.frames[0].name = "Renamed"; s.frames[0].selected = false
        XCTAssertEqual(before, request())
        s.annotations[0].region.width = 0.5; XCTAssertNotEqual(before, request())
    }
    func testEditorGeometrySourceAndRevisionInvalidate() throws {
        let s = session(), root = URL(fileURLWithPath: "/tmp/source")
        let before = EditorRenderRequest(source: root, revision: 0, frame: s.frames[0], annotations: [])
        XCTAssertNotEqual(before, EditorRenderRequest(source: root, revision: 1, frame: s.frames[0], annotations: []))
        XCTAssertNotEqual(before, EditorRenderRequest(source: root.appendingPathComponent("other"), revision: 0, frame: s.frames[0], annotations: []))
        let mark = Annotation(id: "CL-001", frameID: "f", kind: .redaction, region: Region(x: 0, y: 0, width: 1, height: 1))
        XCTAssertNotEqual(before, EditorRenderRequest(source: root, revision: 0, frame: s.frames[0], annotations: [mark]))
    }
    func testSelectionSurvivesUntickingAndResolvesDeletedFrames() {
        var s = session(); var f = s.frames[0]; f.id = "g"; s.frames.append(f); s.frames[0].selected = false
        XCTAssertEqual(FrameSelection.resolve("f", in: s, preferIncluded: true), "f")
        XCTAssertEqual(FrameSelection.resolve("deleted", in: s, preferIncluded: true), "g")
        XCTAssertEqual(FrameSelection.resolve(nil, in: s), "f")
        s.frames = []; XCTAssertNil(FrameSelection.resolve("f", in: s))
    }
    func testScrollRequiresMatchingWindowAndQuietPeriod() {
        var scroll = ScrollActivity(); XCTAssertFalse(scroll.holding(at: 0))
        scroll.observe(at: 1, targetWindowID: 2, windowUnderPointer: 3); XCTAssertFalse(scroll.holding(at: 1))
        scroll.observe(at: 1, targetWindowID: 2, windowUnderPointer: 2)
        XCTAssertTrue(scroll.holding(at: 1.49)); XCTAssertFalse(scroll.holding(at: 1.5)); XCTAssertFalse(scroll.holding(at: 0.9))
        scroll.observe(at: .nan, targetWindowID: 2, windowUnderPointer: 2); XCTAssertTrue(scroll.holding(at: 1.2))
    }
    func testCacheEvictsLeastRecentlyUsedAndAccountsReplacements() {
        var cache = CostCache<String, Int>(limit: 10)
        cache.insert(1, for: "a", cost: 4); cache.insert(2, for: "b", cost: 4)
        XCTAssertEqual(cache.value(for: "a"), 1)
        cache.insert(3, for: "c", cost: 4); XCTAssertNil(cache.value(for: "b")); XCTAssertEqual(cache.cost, 8)
        cache.insert(4, for: "a", cost: 10); XCTAssertEqual(cache.cost, 10); XCTAssertEqual(cache.count, 1)
        cache.insert(5, for: "a", cost: 11); XCTAssertEqual(cache.cost, 0); XCTAssertEqual(cache.count, 0)
        cache.insert(6, for: "invalid", cost: -1); XCTAssertEqual(cache.count, 0)
    }
    func testCacheStressAlwaysHonorsByteLimit() {
        var cache = CostCache<Int, Int>(limit: 1024)
        for i in 0..<10_000 {
            cache.insert(i, for: i % 97, cost: (i * 37) % 1500)
            _ = cache.value(for: (i + 31) % 97)
            XCTAssertLessThanOrEqual(cache.cost, 1024); XCTAssertGreaterThanOrEqual(cache.cost, 0)
        }
        cache.removeAll(); XCTAssertEqual(cache.cost, 0); XCTAssertEqual(cache.count, 0)
    }
    func testLumaRejectsOverflowingDimensions() {
        XCTAssertThrowsError(try LumaFrame(width: Int.max, height: 2, pixels: []))
        XCTAssertThrowsError(try LumaFrame(width: 1, height: 1, pixels: [0], sourceWidth: 0))
    }
}
