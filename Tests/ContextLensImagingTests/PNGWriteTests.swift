import XCTest
import CoreGraphics
import ContextLensCore
@testable import ContextLensImaging

final class PNGWriteTests: XCTestCase {
    func testMissingParentReportsFilesystemErrorAndCanRetry() throws {
        let (_, root, image) = try ExportTests().fixture()
        defer { try? FileManager.default.removeItem(at: root) }
        let parent = root.appendingPathComponent("missing")
        let destination = parent.appendingPathComponent("frame.png")
        XCTAssertThrowsError(try Images.png(image, to: destination)) { error in
            // ImageIO's generic encoding error must not hide a filesystem failure.
            XCTAssertEqual((error as NSError).domain, NSCocoaErrorDomain)
        }
        XCTAssertFalse(FileManager.default.fileExists(atPath: destination.path))
        try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: true)
        try Images.png(image, to: destination)
        let decoded = try Images.load(destination)
        XCTAssertEqual(decoded.width, image.width)
        XCTAssertEqual(decoded.height, image.height)
        let expected = try Images.load(root.appendingPathComponent("frames/frame-001.png"))
        XCTAssertEqual(ExportTests().rgb(decoded, x: 50, y: 50), ExportTests().rgb(expected, x: 50, y: 50))
    }

    func testFailedReplacementPreservesExistingPNGAndLeavesNoTemporaryFiles() throws {
        let (_, root, image) = try ExportTests().fixture()
        defer { try? FileManager.default.removeItem(at: root) }
        let parent = root.appendingPathComponent("frames")
        let destination = parent.appendingPathComponent("frame-001.png")
        let original = try Data(contentsOf: destination)
        try FileManager.default.setAttributes([.posixPermissions: 0o500], ofItemAtPath: parent.path)
        defer { try? FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: parent.path) }
        // Lock the file too so the original direct ImageIO writer cannot truncate it.
        try FileManager.default.setAttributes([.posixPermissions: 0o400], ofItemAtPath: destination.path)
        XCTAssertThrowsError(try Images.png(image, to: destination)) { error in
            XCTAssertEqual((error as NSError).domain, NSCocoaErrorDomain)
        }
        XCTAssertEqual(try Data(contentsOf: destination), original)
        XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: parent.path), ["frame-001.png"])
    }
}
