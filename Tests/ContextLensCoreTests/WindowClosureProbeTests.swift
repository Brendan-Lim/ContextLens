import XCTest
@testable import ContextLensCore

final class WindowClosureProbeTests: XCTestCase {
    private let target = WindowIdentity(windowID: 42, processID: 7)
    @MainActor func testFirstLookupAbsentIsAnObservationNotAnImmediateGuarantee() async {
        var clock = 0.0
        let result = await WindowClosureProbe.observe(target: target, closedAt: 0, now: { clock }, enumerate: { clock += 0.01; return [] }, pause: { clock += Double($0) / 1_000_000_000 })
        XCTAssertEqual(result.outcome, "first-observation-absent")
        XCTAssertTrue(result.firstObservationAbsent); XCTAssertTrue(result.originalCheckpointAbsent)
        XCTAssertEqual(result.samples[0].requestCompletedMS, 210, accuracy: 0.01)
    }
    @MainActor func testStaleEnumerationThenLateAbsenceDoesNotEraseOriginalFailure() async {
        var clock = 0.0, calls = 0
        let result = await WindowClosureProbe.observe(target: target, closedAt: 0, now: { clock }, enumerate: {
            calls += 1; return calls == 1 ? [self.target] : []
        }, pause: { clock += Double($0) / 1_000_000_000 })
        XCTAssertEqual(result.outcome, "eventual-disappearance")
        XCTAssertFalse(result.originalCheckpointAbsent)
        XCTAssertFalse(result.firstObservationAbsent)
        XCTAssertEqual(result.samples.last?.requestCompletedMS ?? 0, 250, accuracy: 0.01)
    }
    @MainActor func testPersistentMembershipTimesOutWithTrace() async {
        var clock = 0.0
        let result = await WindowClosureProbe.observe(target: target, closedAt: 0, deadlineMS: 400, now: { clock }, enumerate: { [self.target] }, pause: { clock += Double($0) / 1_000_000_000 })
        XCTAssertEqual(result.outcome, "timeout"); XCTAssertFalse(result.originalCheckpointAbsent)
        XCTAssertTrue(result.samples.allSatisfy(\.identityMatched))
        XCTAssertLessThanOrEqual(result.samples.count, 6)
    }
    @MainActor func testSlowQueryCannotEstablishDisappearanceWithinDeadline() async {
        var clock = 0.0
        let result = await WindowClosureProbe.observe(target: target, closedAt: 0, now: { clock }, enumerate: { clock = 3; return [] }, pause: { clock += Double($0) / 1_000_000_000 })
        XCTAssertEqual(result.outcome, "timeout"); XCTAssertFalse(result.originalCheckpointAbsent)
    }
    @MainActor func testEnumerationFailureIsNotAbsence() async {
        enum Denied: Error { case access }
        var clock = 0.0
        let result = await WindowClosureProbe.observe(target: target, closedAt: 0, now: { clock }, enumerate: { throw Denied.access }, pause: { clock += Double($0) / 1_000_000_000 })
        XCTAssertEqual(result.outcome, "enumeration-error"); XCTAssertTrue(result.samples.isEmpty)
        XCTAssertNotNil(result.error); XCTAssertFalse(result.originalCheckpointAbsent)
    }
    @MainActor func testWrongPIDIsRecordedWithoutSubstitutingThatWindow() async {
        var clock = 0.0
        let result = await WindowClosureProbe.observe(target: target, closedAt: 0, now: { clock }, enumerate: { [WindowIdentity(windowID: 42, processID: 9)] }, pause: { clock += Double($0) / 1_000_000_000 })
        XCTAssertTrue(result.samples[0].windowIDListed); XCTAssertFalse(result.samples[0].identityMatched)
    }
    @MainActor func testInvalidClockOrPolicyCannotPass() async {
        let policy = await WindowClosureProbe.observe(target: target, closedAt: 0, intervalMS: 0, now: { 0 }, enumerate: { [] })
        XCTAssertEqual(policy.outcome, "invalid-policy")
        let clock = await WindowClosureProbe.observe(target: target, closedAt: 1, now: { 0 }, enumerate: { [] })
        XCTAssertEqual(clock.outcome, "invalid-clock")
    }
}
