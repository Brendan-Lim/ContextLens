import XCTest
@testable import ContextLensCore

final class CaptureLifecycleTests: XCTestCase {
    let target = WindowIdentity(windowID: 42, processID: 7)
    func testIdentityNeverSubstitutesAnotherWindowOrProcess() {
        let alternatives = [WindowIdentity(windowID: 1, processID: 7), WindowIdentity(windowID: 42, processID: 8)]
        XCTAssertNil(target.selected(in: alternatives, identity: { $0 }))
        XCTAssertNil(target.selected(in: [WindowIdentity](), identity: { $0 }))
        XCTAssertEqual(target.selected(in: alternatives + [target], identity: { $0 }), target)
    }
    @MainActor func testStopDuringEnumerationDoesNotStartAScreenshot() async {
        var continuation: CheckedContinuation<[WindowIdentity], Never>?
        var captures = 0, saves = 0, cleanups = 0
        let run = CaptureRun<WindowIdentity, Int>(target: target,
            enumerate: { await withCheckedContinuation { continuation = $0 } }, identity: { $0 },
            capture: { _ in captures += 1; return 1 }, consume: { _,_ in true },
            flush: {}, save: { saves += 1 }, removeResources: { cleanups += 1 })
        let task = Task { await run.run() }
        while continuation == nil { await Task.yield() }
        let stopped = Task { await run.stop() }
        // Let stop cancel the suspended run, then return an otherwise valid target.
        while !run.isStopping { await Task.yield() }
        XCTAssertEqual(cleanups, 1, "Stop must release monitors/hotkeys even while an OS enumeration is still in flight")
        continuation?.resume(returning: [target])
        _ = await stopped.value; _ = await task.value
        XCTAssertEqual(captures, 0, "Stop during enumeration must not start a later screenshot")
        XCTAssertEqual(saves, 1); XCTAssertEqual(cleanups, 1)
    }
    func testFailedPersistenceDoesNotClaimSavedStates() {
        let result = CaptureCompletion(reason: .targetUnavailable, saveError: "injected disk error")
        XCTAssertFalse(result.status(frameCount: 2).contains("saved locally"))
        XCTAssertTrue(result.needsRecovery)
    }
    @MainActor func testFlushFailureStillAttemptsSavingExistingSession() async {
        enum Failure: Error { case disk }
        var saves = 0
        let run = CaptureRun<WindowIdentity, Int>(target: target, enumerate: { [] }, identity: { $0 },
            capture: { _ in XCTFail("No valid target"); return 0 }, consume: { _,_ in true },
            flush: { throw Failure.disk }, save: { saves += 1 }, removeResources: {})
        let result = await run.run()
        XCTAssertEqual(saves, 1, "A pending-image failure must not skip persistence of existing frames")
        XCTAssertNotNil(result.flushError)
    }
}

extension CaptureLifecycleTests {
    @MainActor func testStopDuringDelaySkipsBeginAndEnumerationAndFinalizesOnce() async {
        var delay: CheckedContinuation<Void, Never>?
        var began = 0, enumerations = 0, cleanups = 0, saves = 0
        var flushCancelled = true
        let run = CaptureRun<WindowIdentity, Int>(target: target, delayNanoseconds: 1,
            enumerate: { enumerations += 1; return [] }, identity: { $0 }, capture: { _ in 0 }, consume: { _,_ in true },
            flush: { flushCancelled = Task.isCancelled }, save: { saves += 1 }, removeResources: { cleanups += 1 },
            began: { began += 1 }, pause: { _ in await withCheckedContinuation { delay = $0 } })
        let task = Task { await run.run() }
        while delay == nil { await Task.yield() }
        let stopped = Task { await run.stop() }
        while !run.isStopping { await Task.yield() }
        delay?.resume()
        let result = await task.value; _ = await stopped.value
        XCTAssertEqual(result.reason, .userStopped)
        XCTAssertEqual(began, 0); XCTAssertEqual(enumerations, 0)
        XCTAssertEqual(cleanups, 1); XCTAssertEqual(saves, 1); XCTAssertFalse(flushCancelled)
    }
    @MainActor func testStopDuringCaptureDiscardsItsLateSampleAndDoesNotCaptureAgain() async {
        var capture: CheckedContinuation<Int, Never>?
        var captures = 0, consumed = 0
        let run = CaptureRun<WindowIdentity, Int>(target: target, enumerate: { [self.target] }, identity: { $0 },
            capture: { _ in captures += 1; return await withCheckedContinuation { capture = $0 } },
            consume: { _,_ in consumed += 1; return true }, flush: {}, save: {}, removeResources: {})
        let task = Task { await run.run() }
        while capture == nil { await Task.yield() }
        let stopped = Task { await run.stop() }
        while !run.isStopping { await Task.yield() }
        capture?.resume(returning: 1)
        _ = await task.value; _ = await stopped.value
        XCTAssertEqual(captures, 1); XCTAssertEqual(consumed, 0)
    }
    @MainActor func testDuplicateStopsShareTheSameFlushSaveAndResourceCleanup() async {
        var flush: CheckedContinuation<Void, Never>?
        var flushes = 0, saves = 0, cleanups = 0
        let run = CaptureRun<WindowIdentity, Int>(target: target, enumerate: { [] }, identity: { $0 }, capture: { _ in 0 },
            consume: { _,_ in true }, flush: { flushes += 1; await withCheckedContinuation { flush = $0 } },
            save: { saves += 1 }, removeResources: { cleanups += 1 })
        let running = Task { await run.run() }
        while flush == nil { await Task.yield() }
        let stop1 = Task { await run.stop() }, stop2 = Task { await run.stop() }
        await Task.yield(); flush?.resume()
        let original = await running.value, first = await stop1.value, second = await stop2.value
        XCTAssertEqual(original.reason, .targetUnavailable); XCTAssertEqual(first.reason, original.reason); XCTAssertEqual(second.reason, original.reason)
        _ = await run.run(); _ = await run.stop()
        XCTAssertEqual(flushes, 1); XCTAssertEqual(saves, 1); XCTAssertEqual(cleanups, 1)
    }
    @MainActor func testCallerCancellationAlsoStopsTheSamplingTask() async {
        var enumeration: CheckedContinuation<[WindowIdentity], Never>?
        var captures = 0
        let run = CaptureRun<WindowIdentity, Int>(target: target,
            enumerate: { await withCheckedContinuation { enumeration = $0 } }, identity: { $0 },
            capture: { _ in captures += 1; return 0 }, consume: { _,_ in true }, flush: {}, save: {}, removeResources: {})
        let task = Task { await run.run() }
        while enumeration == nil { await Task.yield() }
        task.cancel()
        while !run.isStopping { await Task.yield() }
        enumeration?.resume(returning: [target])
        let result = await task.value
        XCTAssertEqual(result.reason, .userStopped); XCTAssertEqual(captures, 0)
    }
    @MainActor func testApplicationExitAndPermissionOrCaptureErrorsStopAndSave() async {
        enum Failure: Error { case denied, capture }
        for reason in [CaptureEndReason.applicationExited, .permissionDenied, .captureFailed] {
            var saves = 0, cleanups = 0
            let run = CaptureRun<WindowIdentity, Int>(target: target,
                enumerate: { reason == .applicationExited ? [] : [self.target] }, identity: { $0 },
                capture: { _ in throw Failure.denied }, consume: { _,_ in XCTFail("Failed capture cannot be processed"); return true },
                flush: {}, save: { saves += 1 }, removeResources: { cleanups += 1 },
                missingReason: { .applicationExited }, classify: { _ in reason })
            let result = await run.run()
            XCTAssertEqual(result.reason, reason); XCTAssertEqual(saves, 1); XCTAssertEqual(cleanups, 1)
            XCTAssertFalse(result.needsRecovery)
        }
    }
    @MainActor func testFrameLimitAndEmptySessionHaveAccurateOutcomes() async {
        var captures = 0
        let run = CaptureRun<WindowIdentity, Int>(target: target, enumerate: { [self.target] }, identity: { $0 },
            capture: { _ in captures += 1; return 0 }, consume: { _,_ in false }, flush: {}, save: {}, removeResources: {})
        let result = await run.run()
        XCTAssertEqual(result.reason, .frameLimit); XCTAssertEqual(captures, 1)
        XCTAssertTrue(CaptureCompletion(reason: .userStopped).status(frameCount: 0).contains("No states captured"))
        XCTAssertTrue(CaptureCompletion(reason: .permissionDenied).status(frameCount: 1).contains("Screen Recording"))
    }
    @MainActor func testFlushAndSaveFailuresAreBothRetainedAndPreventSafeQuit() async {
        enum Failure: Error { case disk }
        let run = CaptureRun<WindowIdentity, Int>(target: target, enumerate: { [] }, identity: { $0 }, capture: { _ in 0 },
            consume: { _,_ in true }, flush: { throw Failure.disk }, save: { throw Failure.disk }, removeResources: {})
        let result = await run.run()
        XCTAssertNotNil(result.flushError); XCTAssertNotNil(result.saveError); XCTAssertTrue(result.needsRecovery)
        XCTAssertFalse(result.status(frameCount: 3).contains("saved locally"))
    }
}

extension CaptureLifecycleTests {
    @MainActor func testEnumerationErrorNeverFallsBackAndRapidNewRunsRemainIndependent() async {
        enum Failure: Error { case enumeration }
        var captures = 0, saves = 0, cleanups = 0
        let failed = CaptureRun<WindowIdentity, Int>(target: target, enumerate: { throw Failure.enumeration }, identity: { $0 },
            capture: { _ in captures += 1; return 0 }, consume: { _,_ in true },
            flush: {}, save: { saves += 1 }, removeResources: { cleanups += 1 })
        let failure = await failed.run()
        XCTAssertEqual(failure.reason, .captureFailed); XCTAssertNotNil(failure.captureError); XCTAssertEqual(captures, 0)
        for index in 0..<5 {
            let next = CaptureRun<WindowIdentity, Int>(target: WindowIdentity(windowID: UInt32(index+1), processID: 7),
                enumerate: { XCTFail("Stopped before start"); return [] }, identity: { $0 }, capture: { _ in 0 },
                consume: { _,_ in true }, flush: {}, save: { saves += 1 }, removeResources: { cleanups += 1 })
            let outcome = await next.stop()
            XCTAssertEqual(outcome.reason, .userStopped)
        }
        XCTAssertEqual(saves, 6); XCTAssertEqual(cleanups, 6)
    }
}

extension CaptureLifecycleTests {
    @MainActor func testStopBeforeRunDoesNotWaitThroughStartDelay() async {
        var delays = 0
        let run = CaptureRun<WindowIdentity, Int>(target: target, delayNanoseconds: 10_000_000_000,
            enumerate: { XCTFail("Already stopped"); return [] }, identity: { $0 }, capture: { _ in 0 },
            consume: { _,_ in true }, flush: {}, save: {}, removeResources: {}, pause: { _ in delays += 1 })
        let result = await run.stop()
        XCTAssertEqual(result.reason, .userStopped); XCTAssertEqual(delays, 0)
    }
}

extension CaptureLifecycleTests {
    @MainActor func testWindowClosingDuringCaptureMayFinishOriginalSampleButNeverSubstitutes() async {
        let replacement = WindowIdentity(windowID: 99, processID: target.processID)
        var available = [target], captures: [WindowIdentity] = [], consumed = 0
        let run = CaptureRun<WindowIdentity, Int>(target: target, enumerate: { available }, identity: { $0 },
            capture: { window in
                captures.append(window)
                available = [replacement] // Target disappears while its already-bound request finishes.
                return 1
            }, consume: { window,_ in XCTAssertEqual(window, self.target); consumed += 1; return true },
            flush: {}, save: {}, removeResources: {}, pause: { _ in })
        let result = await run.run()
        XCTAssertEqual(result.reason, .targetUnavailable); XCTAssertEqual(captures, [target]); XCTAssertEqual(consumed, 1)
    }
}
