import XCTest
import CoreGraphics
import ContextLensCore
@testable import ContextLensImaging

final class HandoffReliabilityTests: XCTestCase {
    func fixture(_ dimensions: [(Int, Int)] = [(100, 100), (100, 100)]) throws -> (Session, URL) {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("handoff-\(UUID().uuidString)/Project space 画面")
        try FileManager.default.createDirectory(at: root.appendingPathComponent("frames"), withIntermediateDirectories: true)
        var session = Session(id: "handoff", createdAt: Date(timeIntervalSince1970: 1_700_000_000))
        for (index, size) in dimensions.enumerated() {
            let id = "frame-\(index + 1)"
            let frame = Frame(id: id, timestampMS: index * 100, name: "State \(index + 1)", imagePath: "frames/\(id).png", width: size.0, height: size.1, displayScale: index == 1 ? 2 : 1)
            session.frames.append(frame)
            try writeImage(frame, root: root)
        }
        try SessionStore.save(session, to: root)
        return (session, root)
    }
    func writeImage(_ frame: Frame, root: URL, blue: Bool = false) throws {
        let context = CGContext(data: nil, width: frame.width, height: frame.height, bitsPerComponent: 8, bytesPerRow: 0,
                                space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
        context.setFillColor(CGColor(red: blue ? 0 : 1, green: 0, blue: blue ? 1 : 0, alpha: 1))
        context.fill(CGRect(x: 0, y: 0, width: frame.width, height: frame.height))
        try Images.png(context.makeImage()!, to: root.appendingPathComponent(frame.imagePath))
    }
    func assertNoExport(_ destination: URL, root: URL, file: StaticString = #filePath, line: UInt = #line) throws {
        XCTAssertFalse(FileManager.default.fileExists(atPath: destination.path), file: file, line: line)
        XCTAssertFalse(try FileManager.default.contentsOfDirectory(atPath: root.path).contains { $0.hasPrefix(".contextlens-") }, file: file, line: line)
    }
    func testIncludedImageChangedAtSameDimensionsRejectsStalePlanAndFreshRetrySucceeds() throws {
        let (session, root) = try fixture([(100, 100)])
        defer { try? FileManager.default.removeItem(at: root.deletingLastPathComponent()) }
        let saved = try Data(contentsOf: root.appendingPathComponent("session.json"))
        let plan = try ExportPlan.prepare(session, source: root, options: .allFrames)
        try writeImage(session.frames[0], root: root, blue: true)
        let destination = root.appendingPathComponent("new handoff")
        XCTAssertThrowsError(try Exporter.export(plan, destination: destination))
        try assertNoExport(destination, root: root)
        XCTAssertEqual(try Data(contentsOf: root.appendingPathComponent("session.json")), saved)
        let fresh = try Exporter.export(session, source: root, destination: destination, options: .allFrames)
        let pixel = ExportTests().rgb(try Images.load(destination.appendingPathComponent(fresh.frames[0].imagePath)), x: 50, y: 50)
        XCTAssertGreaterThan(pixel[2], 200); XCTAssertLessThan(pixel[0], 20)
    }
    func testPreviouslyDuplicateImageChangedAfterPreviewCannotBeSilentlyOmitted() throws {
        let (session, root) = try fixture()
        defer { try? FileManager.default.removeItem(at: root.deletingLastPathComponent()) }
        let options = ExportOptions(annotatedOnly: false, excludeDuplicates: true)
        let plan = try ExportPlan.prepare(session, source: root, options: options)
        XCTAssertEqual(plan.session.frames.count, 1)
        try writeImage(session.frames[1], root: root, blue: true)
        let destination = root.appendingPathComponent("new handoff")
        XCTAssertThrowsError(try Exporter.export(plan, destination: destination))
        try assertNoExport(destination, root: root)
        XCTAssertEqual(try Exporter.export(session, source: root, destination: destination, options: options).frames.count, 2)
    }
    func testMissingSecondImageAfterPreparationCleansPartialStageAndCanRetry() throws {
        let (session, root) = try fixture([(100, 100), (160, 90)])
        defer { try? FileManager.default.removeItem(at: root.deletingLastPathComponent()) }
        let plan = try ExportPlan.prepare(session, source: root, options: .allFrames)
        try FileManager.default.removeItem(at: root.appendingPathComponent(session.frames[1].imagePath))
        let destination = root.appendingPathComponent("retry")
        XCTAssertThrowsError(try Exporter.export(plan, destination: destination))
        try assertNoExport(destination, root: root)
        try writeImage(session.frames[1], root: root)
        XCTAssertEqual(try Exporter.export(plan, destination: destination).frames.count, 2)
    }
    func testExistingDanglingDestinationLinkIsPreserved() throws {
        let (session, root) = try fixture([(100, 100)])
        defer { try? FileManager.default.removeItem(at: root.deletingLastPathComponent()) }
        let destination = root.appendingPathComponent("existing link")
        try FileManager.default.createSymbolicLink(atPath: destination.path, withDestinationPath: "missing-target")
        XCTAssertThrowsError(try Exporter.export(session, source: root, destination: destination, options: .allFrames))
        XCTAssertEqual(try FileManager.default.destinationOfSymbolicLink(atPath: destination.path), "missing-target")
        XCTAssertFalse(try FileManager.default.contentsOfDirectory(atPath: root.path).contains { $0.hasPrefix(".contextlens-") })
    }

    func testReopenedEditsKeepReviewOrderSelectionAndIssueGaps() throws {
        var (session, root) = try fixture([(100, 80), (200, 160), (160, 90)])
        defer { try? FileManager.default.removeItem(at: root.deletingLastPathComponent()) }
        let region = Region(x: 0.2, y: 0.2, width: 0.2, height: 0.2)
        let first = try session.addAnnotation(frameID: "frame-1", kind: .rectangle, region: region, instruction: "Align this button")
        let deleted = try session.addAnnotation(frameID: "frame-2", kind: .highlight, region: region, instruction: "Deleted instruction")
        _ = try session.addAnnotation(frameID: "frame-3", kind: .rectangle, region: region, instruction: "Deselected instruction")
        session.annotations.removeAll { $0.id == deleted }
        let last = try session.addAnnotation(frameID: "frame-1", kind: .highlight, region: region, instruction: "Second request 画面")
        session.frames[0].name = "Renamed dialog 画面"
        session.frames[2].selected = false
        session.frames.swapAt(0, 1)
        try SessionStore.save(session, to: root)
        let original = try Data(contentsOf: root.appendingPathComponent("session.json"))
        let reopened = try SessionStore.load(from: root)
        XCTAssertEqual(reopened, session)
        let destination = root.appendingPathComponent("export 画面")
        let manifest = try Exporter.export(reopened, source: root, destination: destination, options: .allFrames)
        XCTAssertEqual(manifest.frames.map(\.id), ["frame-2", "frame-1"])
        XCTAssertEqual(manifest.frames.map(\.displayScale), [2, 1])
        XCTAssertEqual(manifest.issues.map { $0.annotation.id }, [first, last])
        let decoder = JSONDecoder(); decoder.dateDecodingStrategy = .iso8601
        let metadata = try decoder.decode(Session.self, from: Data(contentsOf: destination.appendingPathComponent("metadata/session.json")))
        XCTAssertEqual(metadata.nextIssueNumber, 5)
        let brief = try String(contentsOf: destination.appendingPathComponent("context.md"))
        let timeline = try String(contentsOf: destination.appendingPathComponent("metadata/timeline.md"))
        XCTAssertTrue(brief.contains(first)); XCTAssertTrue(brief.contains(last)); XCTAssertTrue(brief.contains("Renamed dialog 画面"))
        XCTAssertFalse(brief.contains("Deleted instruction")); XCTAssertFalse(brief.contains("Deselected instruction"))
        XCTAssertTrue(timeline.range(of: "[frame-2]")!.lowerBound < timeline.range(of: "[frame-1]")!.lowerBound)
        XCTAssertFalse(timeline.contains("frame-3"))
        for frame in manifest.frames {
            let image = try Images.load(SessionStore.resolve(frame.imagePath, in: destination))
            XCTAssertEqual(image.width, frame.width); XCTAssertEqual(image.height, frame.height)
        }
        XCTAssertEqual(try Data(contentsOf: root.appendingPathComponent("session.json")), original)
    }

    func testPreparedAppPathAndDirectCLIPathProduceIdenticalPackageContents() throws {
        var (session, root) = try fixture([(100, 100), (200, 160)])
        defer { try? FileManager.default.removeItem(at: root.deletingLastPathComponent()) }
        for frame in session.frames {
            _ = try session.addAnnotation(frameID: frame.id, kind: .rectangle, region: Region(x: 0.1, y: 0.1, width: 0.2, height: 0.2), instruction: "Align \(frame.id)")
        }
        _ = try session.addAnnotation(frameID: "frame-1", kind: .highlight, region: Region(x: 0.5, y: 0.5, width: 0.2, height: 0.2), points: [Point(x: 0.5, y: 0.5), Point(x: 0.7, y: 0.7)])
        _ = try session.addAnnotation(frameID: "frame-1", kind: .redaction, region: Region(x: 0.1, y: 0.6, width: 0.2, height: 0.2), instruction: "Never export this redaction note")
        let first = root.appendingPathComponent("prepared"), second = root.appendingPathComponent("direct")
        _ = try Exporter.export(ExportPlan.prepare(session, source: root), destination: first)
        _ = try Exporter.export(session, source: root, destination: second)
        func files(_ folder: URL) throws -> [String: Data] {
            var result: [String: Data] = [:]
            for case let relative as String in FileManager.default.enumerator(atPath: folder.path)! {
                let path = folder.appendingPathComponent(relative)
                if try path.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile == true {
                    result[relative] = try Data(contentsOf: path)
                }
            }
            return result
        }
        let a = try files(first), b = try files(second)
        XCTAssertEqual(a, b)
        XCTAssertNotNil(a[ContextReport.stateImagePath(frameID: "frame-1")])
        for text in ["context.md", "manifest.json", "metadata/session.json"] {
            XCTAssertFalse(String(decoding: try XCTUnwrap(a[text]), as: UTF8.self).contains("Never export this redaction note"))
        }
        for path in ["frames/frame-1.png", "annotated/CL-001.png", "annotated/CL-003.png", ContextReport.stateImagePath(frameID: "frame-1")] {
            XCTAssertEqual(ExportTests().rgb(try Images.load(first.appendingPathComponent(path)), x: 20, y: 70), [0, 0, 0])
        }
        let before = try files(first)
        XCTAssertThrowsError(try Exporter.export(session, source: root, destination: first))
        XCTAssertEqual(try files(first), before)
    }

    func testPermissionDeniedAndNonDirectoryParentsLeaveUserDataIntact() throws {
        let (session, root) = try fixture([(100, 100)])
        defer { try? FileManager.default.removeItem(at: root.deletingLastPathComponent()) }
        let blocker = root.appendingPathComponent("file-parent")
        try Data("preserve this file".utf8).write(to: blocker)
        XCTAssertThrowsError(try Exporter.export(session, source: root, destination: blocker.appendingPathComponent("export"), options: .allFrames))
        XCTAssertEqual(try String(contentsOf: blocker), "preserve this file")
        let locked = root.appendingPathComponent("read-only parent")
        try FileManager.default.createDirectory(at: locked, withIntermediateDirectories: true)
        try FileManager.default.setAttributes([.posixPermissions: 0o500], ofItemAtPath: locked.path)
        defer { try? FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: locked.path) }
        XCTAssertThrowsError(try Exporter.export(session, source: root, destination: locked.appendingPathComponent("export"), options: .allFrames))
        XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: locked.path), [])
    }

    func testEmptyDeselectedCorruptAndEscapingSourcesNeverPublish() throws {
        var (session, root) = try fixture([(100, 100)])
        defer { try? FileManager.default.removeItem(at: root.deletingLastPathComponent()) }
        let destination = root.appendingPathComponent("must not exist")
        XCTAssertThrowsError(try Exporter.export(Session(id: "empty"), source: root, destination: destination))
        session.frames[0].selected = false
        XCTAssertThrowsError(try Exporter.export(session, source: root, destination: destination, options: .allFrames))
        session.frames[0].selected = true
        let image = root.appendingPathComponent(session.frames[0].imagePath)
        try Data("corrupt image".utf8).write(to: image)
        XCTAssertThrowsError(try Exporter.export(session, source: root, destination: destination, options: .allFrames))
        try FileManager.default.removeItem(at: image)
        let outside = root.deletingLastPathComponent().appendingPathComponent("outside.png")
        try Data("synthetic outside marker".utf8).write(to: outside)
        try FileManager.default.createSymbolicLink(at: image, withDestinationURL: outside)
        XCTAssertThrowsError(try Exporter.export(session, source: root, destination: destination, options: .allFrames))
        XCTAssertEqual(try String(contentsOf: outside), "synthetic outside marker")
        try assertNoExport(destination, root: root)
    }

    func testRetryPreservesAnUnrelatedInterruptedStagingFolder() throws {
        let (session, root) = try fixture([(100, 100)])
        defer { try? FileManager.default.removeItem(at: root.deletingLastPathComponent()) }
        let orphan = root.appendingPathComponent(".contextlens-interrupted-synthetic")
        try FileManager.default.createDirectory(at: orphan, withIntermediateDirectories: true)
        let marker = orphan.appendingPathComponent("recoverable-marker")
        try Data("preserve interrupted work".utf8).write(to: marker)
        let destination = root.appendingPathComponent("retry handoff")
        let manifest = try Exporter.export(session, source: root, destination: destination, options: .allFrames)
        XCTAssertEqual(manifest.frames.count, 1)
        XCTAssertNoThrow(try Images.load(SessionStore.resolve(manifest.frames[0].imagePath, in: destination)))
        XCTAssertEqual(try String(contentsOf: marker), "preserve interrupted work")
    }
}
