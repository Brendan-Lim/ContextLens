import XCTest
@testable import ContextLensCore

extension CoreTests {
    func testLowAndHighDistinguishSmallChangesWithoutLosingLargeChanges() throws {
        let baseline = try image()
        let small = try image((0..<3).flatMap { y in (0..<3).map { (y*100+$0, UInt8(240)) } })
        let large = try image((0..<4).flatMap { y in (0..<10).map { (y*100+$0, UInt8(240)) } })
        for sensitivity in Sensitivity.allCases {
            var selector = FrameSelector(); selector.sensitivity = sensitivity
            _ = selector.observe(baseline, at: 0)
            XCTAssertNil(selector.observe(small, at: 100))
            let capturedSmall = selector.observe(small, at: 600)
            XCTAssertEqual(capturedSmall != nil, sensitivity == .high)

            var largerChange = FrameSelector(); largerChange.sensitivity = sensitivity
            _ = largerChange.observe(baseline, at: 0)
            XCTAssertNil(largerChange.observe(large, at: 100))
            XCTAssertNotNil(largerChange.observe(large, at: 600))
        }
    }
}
