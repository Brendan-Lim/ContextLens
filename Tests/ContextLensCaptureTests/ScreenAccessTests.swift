import XCTest
@testable import ContextLensCapture

final class ScreenAccessTests: XCTestCase {
    func testExplicitCheckTriesScreenCaptureKitEvenWhenPreflightIsFalse() async throws {
        var calls = 0
        let windows = try await ScreenAccessProbe.windows(preflightGranted: false, userInitiated: true, previouslyVerified: false) {
            calls += 1; return []
        }
        XCTAssertEqual(calls, 1); XCTAssertNotNil(windows)
    }
    func testPassiveFirstLaunchDoesNotTriggerPermissionRequest() async throws {
        var calls = 0
        let windows = try await ScreenAccessProbe.windows(preflightGranted: false, userInitiated: false, previouslyVerified: false) {
            calls += 1; return []
        }
        XCTAssertEqual(calls, 0); XCTAssertNil(windows)
    }
    func testPreviouslyVerifiedAccessIsRecheckedDespiteStalePreflight() async throws {
        var calls = 0
        let windows = try await ScreenAccessProbe.windows(preflightGranted: false, userInitiated: false, previouslyVerified: true) {
            calls += 1; return []
        }
        XCTAssertEqual(calls, 1); XCTAssertNotNil(windows)
    }
    func testPositivePreflightDoesNotHideActualAPIFailure() async {
        enum Denied: Error { case access }
        do {
            _ = try await ScreenAccessProbe.windows(preflightGranted: true, userInitiated: false, previouslyVerified: false) { throw Denied.access }
            XCTFail("A positive preflight must not turn an API failure into granted access")
        } catch { XCTAssertTrue(error is Denied) }
    }
}
