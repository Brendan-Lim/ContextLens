import XCTest
@testable import ContextLensCore

final class LeanHandoffTests: XCTestCase {
    func fixture() throws -> Session {
        var s = Session(id: "lean")
        s.frames = [Frame(id: "f-1", timestampMS: 100, name: "Settings", imagePath: "frames/f-1.png", width: 100, height: 100, event: "Control opened")]
        _ = try s.addAnnotation(frameID: "f-1", kind: .rectangle, region: Region(x: 0.1, y: 0.1, width: 0.2, height: 0.2), instruction: "Align Save with the dialog edge.")
        return s
    }
    func testOneBriefDoesNotRequireManifestOrEagerCrops() throws {
        let text = ContextReport.markdown(try fixture())
        XCTAssertFalse((text.components(separatedBy: "More context").first ?? text).contains("manifest.json"), "The first read must contain everything necessary to begin")
        XCTAssertTrue(text.contains("annotated/states/f-1.png"))
        XCTAssertTrue(text.contains("only if"), "Extra evidence is conditional, never forbidden")
        XCTAssertTrue(text.contains("untrusted")); XCTAssertTrue(text.lowercased().contains("verify"))
    }
    func testTimelineIsAnOptionalSeparateRead() throws {
        var s = try fixture()
        for n in 2...200 {
            s.frames.append(Frame(id: "f-\(n)", timestampMS: n * 100, name: "Recorded state \(n)", imagePath: "frames/f-\(n).png", width: 100, height: 100, event: "Observed event \(n)"))
        }
        let text = ContextReport.markdown(s)
        XCTAssertTrue(text.contains("metadata/timeline.md"))
        XCTAssertFalse(text.contains("Observed event 200"), "Capture history is preserved outside the first read")
        XCTAssertLessThan(text.utf8.count, 2500, "Unannotated history must not bloat a one-issue brief")
    }
    func testIdenticalTaskAndIssueInstructionAreNotRepeated() throws {
        var s = try fixture(); let instruction = s.annotations[0].instruction; s.task = instruction
        let text = ContextReport.markdown(s)
        XCTAssertEqual(text.components(separatedBy: instruction).count - 1, 1)
        XCTAssertTrue(text.contains("CL-001"))
    }
    func testCopiedPromptNamesTheExactEntryFile() {
        let text = ContextReport.instruction(path: "/my project/feedback", task: "Fix the Save alignment.")
        XCTAssertTrue(text.hasPrefix("Fix the Save alignment."))
        XCTAssertTrue(text.contains("`/my project/feedback/context.md`"))
        XCTAssertFalse(text.contains("manifest.json"))
    }
}

extension LeanHandoffTests {
    func testEveryExplicitRequestSurvivesLargeMultiIssueBrief() throws {
        var s = try fixture()
        for n in 2...80 {
            _ = try s.addAnnotation(frameID: "f-1", kind: .rectangle, region: Region(x: 0.1, y: 0.1, width: 0.2, height: 0.2), instruction: "Request \(n): preserve this exact requirement.\nSecond line \(n).")
        }
        let brief = ContextReport.markdown(s)
        for mark in s.annotations { XCTAssertTrue(brief.contains(mark.id)); XCTAssertTrue(brief.contains(mark.instruction.replacingOccurrences(of: "\n", with: "\n> "))) }
        XCTAssertEqual(brief.components(separatedBy: "annotated/states/f-1.png").count - 1, 1)
    }
    func testUnmarkedReferenceFramesRemainAvailableAndNeverInventIntent() throws {
        var s = try fixture(); s.annotations = []
        for n in 2...8 { var f = s.frames[0]; f.id = "f-\(n)"; f.name = "State \(n)"; s.frames.append(f) }
        let brief = ContextReport.markdown(s), timeline = ContextReport.timeline(s)
        XCTAssertTrue(brief.contains("No explicit change request")); XCTAssertTrue(brief.contains("first 3 of 8"))
        for frame in s.frames { XCTAssertTrue(timeline.contains("frames/\(frame.id).png")) }
    }
}
