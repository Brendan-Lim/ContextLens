import XCTest
import CoreGraphics
@testable import ContextLensCore

final class ZoomStateTests: XCTestCase {
    let viewport = CGSize(width: 800, height: 600)
    let fit = CGSize(width: 800, height: 500)

    private func centered() -> ZoomState { var z = ZoomState(); z.clamp(content: fit, viewport: viewport); return z }
    /// The image point (0…1) under a viewport point.
    private func imagePoint(_ z: ZoomState, at p: CGPoint) -> CGPoint {
        CGPoint(x: (p.x - z.offset.x) / (fit.width * z.zoom), y: (p.y - z.offset.y) / (fit.height * z.zoom))
    }

    func testFitIsCentered() {
        XCTAssertEqual(centered().offset, CGPoint(x: 0, y: 50))
    }
    func testZoomKeepsThePointUnderTheCursor() {
        var z = centered()
        let cursor = CGPoint(x: 600, y: 400)
        let before = imagePoint(z, at: cursor)
        z.zoom(to: 2, at: cursor, content: fit, viewport: viewport)
        let after = imagePoint(z, at: cursor)
        XCTAssertEqual(z.zoom, 2)
        XCTAssertEqual(before.x, after.x, accuracy: 0.001); XCTAssertEqual(before.y, after.y, accuracy: 0.001)
        XCTAssertNotEqual(z.offset, .zero, "zooming at the bottom right must not jump to the top left")
    }
    func testEdgesClampAndZoomStaysInRange() {
        var z = centered()
        z.zoom(to: 3, at: CGPoint(x: 799, y: 599), content: fit, viewport: viewport)
        XCTAssertGreaterThanOrEqual(z.offset.x, viewport.width - fit.width * 3)
        XCTAssertLessThanOrEqual(z.offset.x, 0)
        // Panning stops at the 100% margin: none horizontally, 50 vertically for this letterboxed screenshot.
        z.pan(by: CGSize(width: 10_000, height: 10_000), content: fit, viewport: viewport)
        XCTAssertEqual(z.offset, CGPoint(x: 0, y: 50))
        z.pan(by: CGSize(width: -10_000, height: -10_000), content: fit, viewport: viewport)
        XCTAssertEqual(z.offset.x, viewport.width - fit.width * 3, accuracy: 0.001)
        XCTAssertEqual(z.offset.y, viewport.height - fit.height * 3 - 50, accuracy: 0.001)
        z.zoom(to: 10, at: .zero, content: fit, viewport: viewport); XCTAssertEqual(z.zoom, ZoomState.maximum)
        z.zoom(to: 0.2, at: .zero, content: fit, viewport: viewport); XCTAssertEqual(z, centered())
    }
    /// The enlarged view's case: a screenshot narrower than the viewport, zoomed near its right and bottom edges.
    func testZoomNearTheEdgesOfALetterboxedScreenshotStaysUnderThePointer() {
        let viewport = CGSize(width: 1296, height: 726), fit = CGSize(width: 1161.6, height: 726)
        var z = ZoomState(); z.clamp(content: fit, viewport: viewport)
        XCTAssertEqual(z.offset.x, (1296 - 1161.6) / 2, accuracy: 0.001)
        for cursor in [CGPoint(x: 1220, y: 700), CGPoint(x: 80, y: 20), CGPoint(x: 973, y: 181)] {
            var zoomed = z
            let before = CGPoint(x: (cursor.x - zoomed.offset.x) / (fit.width * zoomed.zoom), y: (cursor.y - zoomed.offset.y) / (fit.height * zoomed.zoom))
            for _ in 0..<6 { zoomed.zoom(to: zoomed.zoom * 1.16, at: cursor, content: fit, viewport: viewport) }
            let after = CGPoint(x: (cursor.x - zoomed.offset.x) / (fit.width * zoomed.zoom), y: (cursor.y - zoomed.offset.y) / (fit.height * zoomed.zoom))
            XCTAssertEqual(before.x, after.x, accuracy: 0.0005, "x drifted at \(cursor)")
            XCTAssertEqual(before.y, after.y, accuracy: 0.0005, "y drifted at \(cursor)")
        }
    }
    func testKeyboardSteps() {
        XCTAssertEqual(ZoomState(zoom: 1).larger, 1.25)
        XCTAssertEqual(ZoomState(zoom: 2).smaller, 1.5)
        XCTAssertEqual(ZoomState(zoom: 1).smaller, 1)
        XCTAssertEqual(ZoomState(zoom: 4).larger, 4)
    }
}
