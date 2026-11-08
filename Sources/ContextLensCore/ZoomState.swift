import CoreGraphics

/// Zoom and pan for the screenshot, like a webpage: the point under the cursor (or between pinching fingers)
/// stays in place while zooming, and two-finger scrolling moves around when zoomed in.
public struct ZoomState: Equatable, Sendable {
    public var zoom: CGFloat = 1
    /// Top-left of the scaled screenshot inside the viewport.
    public var offset: CGPoint = .zero
    public init(zoom: CGFloat = 1, offset: CGPoint = .zero) { self.zoom = zoom; self.offset = offset }

    public static let maximum: CGFloat = 4

    /// Zooms to `target` while keeping `anchor` (viewport coordinates) fixed over the same image point.
    public mutating func zoom(to target: CGFloat, at anchor: CGPoint, content fit: CGSize, viewport: CGSize) {
        let next = min(Self.maximum, max(1, target))
        let ratio = next / zoom
        offset = CGPoint(x: anchor.x - (anchor.x - offset.x) * ratio, y: anchor.y - (anchor.y - offset.y) * ratio)
        zoom = next
        clamp(content: fit, viewport: viewport)
    }
    public mutating func pan(by delta: CGSize, content fit: CGSize, viewport: CGSize) {
        offset.x += delta.width; offset.y += delta.height
        clamp(content: fit, viewport: viewport)
    }
    /// Keeps the screenshot in view. It may show as much empty margin as it had at 100% (fitted and centred), never
    /// more. That margin is what lets zooming in hold any point of the screenshot exactly under the pointer,
    /// including near the edges of a letterboxed screenshot.
    public mutating func clamp(content fit: CGSize, viewport: CGSize) {
        func axis(_ offset: CGFloat, fitted: CGFloat, available: CGFloat) -> CGFloat {
            let margin = max(0, (available - fitted) / 2)
            let low = available - fitted * zoom - margin, high = margin
            return low >= high ? (low + high) / 2 : min(high, max(low, offset))
        }
        offset.x = axis(offset.x, fitted: fit.width, available: viewport.width)
        offset.y = axis(offset.y, fitted: fit.height, available: viewport.height)
    }
    /// Browser-like steps for ⌘+ and ⌘−.
    public static let steps: [CGFloat] = [1, 1.25, 1.5, 2, 2.5, 3, 4]
    public var larger: CGFloat { Self.steps.first { $0 > zoom + 0.01 } ?? Self.maximum }
    public var smaller: CGFloat { Self.steps.last { $0 < zoom - 0.01 } ?? 1 }
}
