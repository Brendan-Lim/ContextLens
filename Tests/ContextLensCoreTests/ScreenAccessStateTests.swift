import XCTest
@testable import ContextLensCore

final class ScreenAccessStateTests: XCTestCase {
    func testUnverifiedDeniedAndEnumerationFailureHaveDistinctTitles() {
        let states: [ScreenAccessState] = [.unverified, .denied("declined"), .failed("service unavailable"), .verified]
        XCTAssertEqual(Set(states.map(\.title)).count, 4)
        XCTAssertTrue(states[0].title.contains("unverified"))
        XCTAssertTrue(states[1].title.contains("denied"))
        XCTAssertTrue(states[2].title.contains("failed"))
    }
    func testOnlySuccessfulEnumerationVerifiesAccess() {
        for state in [ScreenAccessState.unverified, .denied("declined"), .failed("timeout")] {
            XCTAssertFalse(state.isVerified)
        }
        XCTAssertTrue(ScreenAccessState.verified.isVerified)
        XCTAssertNil(ScreenAccessState.unverified.errorDetails)
        XCTAssertNil(ScreenAccessState.verified.errorDetails)
    }
    func testErrorClassificationRequiresExplicitDenial() {
        let error = NSError(domain: "SyntheticCaptureService", code: 7,
                            userInfo: [NSLocalizedDescriptionKey: "Service unavailable"])
        guard case .failed = ScreenAccessState(error: error, permissionDenied: false) else { return XCTFail("Generic errors must remain failures") }
        guard case .denied = ScreenAccessState(error: error, permissionDenied: true) else { return XCTFail("Explicit denial must remain denied") }
    }
    func testRealErrorDomainCodeReasonRecoveryAndUnderlyingErrorSurvive() {
        let underlying = NSError(domain: "SyntheticTransport", code: 54, userInfo: [NSLocalizedDescriptionKey: "Connection lost"])
        let error = NSError(domain: "SyntheticCaptureService", code: -9,
                            userInfo: [NSLocalizedDescriptionKey: "Enumeration failed", NSLocalizedFailureReasonErrorKey: "Service interrupted",
                                       NSLocalizedRecoverySuggestionErrorKey: "Retry the service", NSUnderlyingErrorKey: underlying])
        let details = ScreenAccessState(error: error, permissionDenied: false).errorDetails ?? ""
        for expected in ["SyntheticCaptureService", "-9", "Enumeration failed", "Service interrupted", "Retry the service", "SyntheticTransport", "54", "Connection lost"] {
            XCTAssertTrue(details.contains(expected), "Missing diagnostic: \(expected)")
        }
    }
    func testFailureDetailsSurviveBothDeniedAndFailedStates() {
        let error = NSError(domain: "SyntheticCaptureService", code: 4, userInfo: [NSLocalizedDescriptionKey: "Unavailable"])
        XCTAssertEqual(ScreenAccessState(error: error, permissionDenied: true).errorDetails,
                       ScreenAccessState(error: error, permissionDenied: false).errorDetails)
    }
}
