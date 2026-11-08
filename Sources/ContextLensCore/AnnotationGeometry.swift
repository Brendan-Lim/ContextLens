import Foundation

public enum AnnotationGeometry {
    public static func highlightWidth(imageWidth: Double) -> Double { max(12, imageWidth / 70) }

    /// Bounds include the rounded stroke, not an artificial minimum-size box.
    public static func highlightBounds(points: [Point], imageWidth: Double, imageHeight: Double) -> Region? {
        guard !points.isEmpty, imageWidth > 0, imageHeight > 0 else { return nil }
        let radius = highlightWidth(imageWidth: imageWidth) / 2
        let x = max(0, (points.map(\.x).min() ?? 0) - radius / imageWidth)
        let y = max(0, (points.map(\.y).min() ?? 0) - radius / imageHeight)
        let right = min(1, (points.map(\.x).max() ?? 0) + radius / imageWidth)
        let bottom = min(1, (points.map(\.y).max() ?? 0) + radius / imageHeight)
        guard right > x, bottom > y else { return nil }
        return Region(x: x, y: y, width: right-x, height: bottom-y)
    }
}
