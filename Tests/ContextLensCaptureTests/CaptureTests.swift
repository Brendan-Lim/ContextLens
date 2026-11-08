import XCTest
import CoreGraphics
import ContextLensCore
import ContextLensImaging
@testable import ContextLensCapture
final class CaptureTests: XCTestCase {
    func image(width: Int = 200, height: Int = 100, changed: Bool = false) -> CGImage {
        let ctx = CGContext(data: nil, width: width, height: height, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
        ctx.setFillColor(CGColor(gray: changed ? 0.8 : 0.2, alpha: 1)); ctx.fill(CGRect(x: 0, y: 0, width: width, height: height)); return ctx.makeImage()!
    }
    func testStreamCommitsSettledStateAndFlushesResize() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let worker = CaptureProcessor(root: root, selector: FrameSelector())
        func sample(_ image: CGImage, _ ms: Int) async throws -> Frame? {
            try await worker.process(image: image, at: ms, scale: 2, title: nil, app: "Fixture", event: nil, manual: false)
        }
        let first = try await sample(image(),0); XCTAssertEqual(first?.captureReason,"initial")
        let duplicate = try await sample(image(),250); XCTAssertNil(duplicate)
        let transition = try await sample(image(changed:true),500); XCTAssertNil(transition)
        let stable = try await sample(image(changed:true),1000); XCTAssertEqual(stable?.captureReason,"visual_change")
        let resizing = try await sample(image(width:300,height:200,changed:true),1100); XCTAssertNil(resizing)
        let flushed = try await worker.flush(); XCTAssertEqual(flushed?.captureReason,"stop_flush"); XCTAssertEqual(flushed?.width,300); XCTAssertEqual(flushed?.height,200)
        XCTAssertEqual(flushed?.displayScale,2)
        XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath:root.appendingPathComponent("frames").path).count,3)
        let again = try await worker.flush(); XCTAssertNil(again)
        for frame in [first,stable,flushed].compactMap({$0}) {
            let img = try Images.load(SessionStore.resolve(frame.imagePath,in:root)); XCTAssertEqual(img.width,frame.width); XCTAssertEqual(img.height,frame.height)
        }
    }
    func testSameAspectRatioResizeIsStillPreserved() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let worker = CaptureProcessor(root: root, selector: FrameSelector())
        _ = try await worker.process(image: image(), at: 0, scale: 1, title: nil, app: nil, event: nil, manual: false)
        let pending = try await worker.process(image: image(width:400,height:200), at: 100, scale: 1, title: nil, app: nil, event: nil, manual: false)
        XCTAssertNil(pending)
        let committed = try await worker.process(image: image(width:400,height:200), at: 600, scale: 1, title: nil, app: nil, event: nil, manual: false)
        XCTAssertEqual(committed?.width,400); XCTAssertEqual(committed?.height,200)
    }
    func testNoSelectedWindowNeverFallsBack() throws {
        XCTAssertThrowsError(try WindowCapture.selected(id:42,pid:123,in:[]))
    }
}

extension CaptureTests {
    func testOutOfOrderSampleCannotReplacePendingFlushImage() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let worker = CaptureProcessor(root: root, selector: FrameSelector())
        _ = try await worker.process(image: image(), at: 0, scale: 1, title: nil, app: nil, event: nil, manual: false)
        _ = try await worker.process(image: image(changed: true), at: 500, scale: 1, title: "new", app: nil, event: nil, manual: false)
        _ = try await worker.process(image: image(), at: 250, scale: 1, title: "stale", app: nil, event: nil, manual: false)
        let flushed = try await worker.flush()
        XCTAssertEqual(flushed?.timestampMS, 500); XCTAssertEqual(flushed?.windowTitle, "new")
    }
    func testFailedWriteCanRetryWithoutLosingStateOrSequence() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        try Data("block directory creation".utf8).write(to: root)
        let worker = CaptureProcessor(root: root, selector: FrameSelector())
        do {
            _ = try await worker.process(image: image(), at: 0, scale: 1, title: nil, app: nil, event: nil, manual: false)
            XCTFail("Expected write failure")
        } catch { }
        try FileManager.default.removeItem(at: root)
        let retry = try await worker.process(image: image(), at: 0, scale: 1, title: nil, app: nil, event: nil, manual: false)
        XCTAssertEqual(retry?.id, "frame-001"); XCTAssertEqual(retry?.captureReason, "initial")
    }
}
