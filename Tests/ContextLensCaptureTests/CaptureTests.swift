import XCTest
import CoreGraphics
import ScreenCaptureKit
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

extension CaptureTests {
    @MainActor func testSelectedTargetLossFlushesAndPersistsOnlyOriginalImages() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let original = WindowIdentity(windowID: 42, processID: 7)
        let substitute = WindowIdentity(windowID: 99, processID: 7)
        let worker = CaptureProcessor(root: root, selector: FrameSelector())
        var session = Session(id: "lifecycle-fixture"), enumerations = 0, captures = 0, finalSaves = 0, cleanups = 0
        let run = CaptureRun<WindowIdentity, CGImage>(target: original,
            enumerate: { enumerations += 1; return enumerations <= 2 ? [substitute, original] : [substitute] }, identity: { $0 },
            capture: { target in
                XCTAssertEqual(target, original); captures += 1
                return self.image(width: captures == 1 ? 200 : 300, height: captures == 1 ? 100 : 200, changed: captures > 1)
            }, consume: { _, image in
                if let frame = try await worker.process(image: image, at: (captures-1)*500, scale: 2, title: nil, app: "Fixture", event: nil, manual: false) {
                    session.frames.append(frame); try SessionStore.save(session, to: root)
                }
                return true
            }, flush: {
                if let frame = try await worker.flush() { session.frames.append(frame); try SessionStore.save(session, to: root) }
            }, save: { finalSaves += 1; try SessionStore.save(session, to: root) },
            removeResources: { cleanups += 1 }, pause: { _ in })
        let result = await run.run()
        XCTAssertEqual(result.reason, .targetUnavailable); XCTAssertFalse(result.needsRecovery)
        XCTAssertEqual(captures, 2); XCTAssertEqual(finalSaves, 1); XCTAssertEqual(cleanups, 1)
        let loaded = try SessionStore.load(from: root)
        XCTAssertEqual(loaded.frames.count, 2); XCTAssertEqual(loaded.frames.last?.captureReason, "stop_flush")
        XCTAssertEqual(loaded.frames.last?.width, 300); XCTAssertEqual(loaded.frames.last?.height, 200)
        for frame in loaded.frames {
            let image = try Images.load(SessionStore.resolve(frame.imagePath, in: root))
            XCTAssertEqual(image.width, frame.width); XCTAssertEqual(image.height, frame.height)
        }
    }
    @MainActor func testStopDuringPendingProcessingPreservesFlushAndValidSession() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let target = WindowIdentity(windowID: 1, processID: 7)
        let worker = CaptureProcessor(root: root, selector: FrameSelector())
        var session = Session(id: "pending-stop"), count = 0
        var pending: CheckedContinuation<Void, Never>?
        let run = CaptureRun<WindowIdentity, CGImage>(target: target, enumerate: { [target] }, identity: { $0 },
            capture: { _ in count += 1; return self.image(changed: count > 1) }, consume: { _, image in
                if let frame = try await worker.process(image: image, at: (count-1)*500, scale: 1, title: nil, app: "Fixture", event: nil, manual: false) { session.frames.append(frame) }
                if count == 2 { await withCheckedContinuation { pending = $0 } }
                return true
            }, flush: {
                XCTAssertFalse(Task.isCancelled)
                if let frame = try await worker.flush() { session.frames.append(frame) }
            }, save: { try SessionStore.save(session, to: root) }, removeResources: {}, pause: { _ in })
        let running = Task { await run.run() }
        while pending == nil { await Task.yield() }
        let stopped = Task { await run.stop() }
        while !run.isStopping { await Task.yield() }
        pending?.resume()
        _ = await stopped.value; _ = await running.value
        let loaded = try SessionStore.load(from: root)
        XCTAssertEqual(count, 2); XCTAssertEqual(loaded.frames.count, 2)
        XCTAssertEqual(loaded.frames.last?.captureReason, "stop_flush")
        let again = try await worker.flush(); XCTAssertNil(again)
    }
    func testOnlyExplicitScreenCaptureKitDenialIsClassifiedAsPermissionLoss() {
        XCTAssertEqual(WindowCapture.endReason(for: NSError(domain: SCStreamErrorDomain, code: SCStreamError.Code.userDeclined.rawValue)), .permissionDenied)
        XCTAssertEqual(WindowCapture.endReason(for: NSError(domain: "Synthetic", code: 1)), .captureFailed)
    }
}

extension CaptureTests {
    @MainActor func testPermissionLossAfterACommittedFramePreservesTheSession() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let target = WindowIdentity(windowID: 1, processID: 7)
        let worker = CaptureProcessor(root: root, selector: FrameSelector())
        var session = Session(id: "permission-loss"), captures = 0
        let run = CaptureRun<WindowIdentity, CGImage>(target: target, enumerate: { [target] }, identity: { $0 },
            capture: { _ in
                captures += 1
                if captures == 2 { throw NSError(domain: SCStreamErrorDomain, code: SCStreamError.Code.userDeclined.rawValue) }
                return self.image()
            }, consume: { _, image in
                if let frame = try await worker.process(image: image, at: 0, scale: 1, title: nil, app: "Fixture", event: nil, manual: false) { session.frames.append(frame) }
                return true
            }, flush: { if let frame = try await worker.flush() { session.frames.append(frame) } },
            save: { try SessionStore.save(session, to: root) }, removeResources: {},
            classify: { WindowCapture.endReason(for: $0) }, pause: { _ in })
        let result = await run.run()
        XCTAssertEqual(result.reason, .permissionDenied); XCTAssertFalse(result.needsRecovery)
        XCTAssertEqual(captures, 2); XCTAssertEqual(try SessionStore.load(from: root).frames.count, 1)
    }
}

extension CaptureTests {
    func testFailedPendingFlushCanRetryWithoutDuplicateFrameOrLostImage() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let worker = CaptureProcessor(root: root, selector: FrameSelector())
        let initial = try await worker.process(image: image(), at: 0, scale: 1, title: nil, app: nil, event: nil, manual: false)
        _ = try await worker.process(image: image(changed: true), at: 500, scale: 1, title: "pending", app: nil, event: nil, manual: false)
        let blocker = root.appendingPathComponent("frames/frame-002.png")
        try FileManager.default.createDirectory(at: blocker, withIntermediateDirectories: false)
        do { _ = try await worker.flush(); XCTFail("Expected image-write failure") } catch { }
        try FileManager.default.removeItem(at: blocker)
        let recovered = try await worker.flush()
        XCTAssertEqual(recovered?.id, "frame-002"); XCTAssertEqual(recovered?.windowTitle, "pending")
        var session = Session(id: "flush-recovery"); session.frames = [initial, recovered].compactMap { $0 }
        try SessionStore.save(session, to: root)
        XCTAssertEqual(try SessionStore.load(from: root).frames.count, 2)
        let again = try await worker.flush(); XCTAssertNil(again)
    }
}
