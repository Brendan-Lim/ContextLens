// Check genuine Finder captures against the owned artwork, excluding draggable icons and labels.
// This checks rendered pixels only; a maintainer must still inspect the complete installer.
import AppKit

guard CommandLine.arguments.count == 3 else {
    fputs("Usage: swift verify-finder-background.swift FINDER.png BACKGROUND@1x.png\n", stderr)
    exit(2)
}
func load(_ path: String) -> NSBitmapImageRep {
    guard let data = try? Data(contentsOf: URL(fileURLWithPath: path)), let rep = NSBitmapImageRep(data: data) else { fatalError("Cannot decode image") }
    return rep
}
let capture = load(CommandLine.arguments[1]), artwork = load(CommandLine.arguments[2])
guard artwork.pixelsWide == 720, artwork.pixelsHigh == 440 else { fatalError("Unexpected artwork dimensions") }
let scale = Double(capture.pixelsWide) / 720
guard (0.9...2.1).contains(scale) else { fatalError("Unexpected Finder capture width") }
// Owned wordmark, heading, subheading, arrow and footer. Never sample actual Finder icons.
let patches = [CGRect(x: 40, y: 30, width: 220, height: 28),
               CGRect(x: 40, y: 97, width: 340, height: 28),
               CGRect(x: 42, y: 142, width: 340, height: 20),
               CGRect(x: 320, y: 230, width: 80, height: 40),
               CGRect(x: 200, y: 386, width: 320, height: 24)]
func rgb(_ rep: NSBitmapImageRep, _ x: Int, _ y: Int) -> [Double] {
    guard let color = rep.colorAt(x: x, y: y)?.usingColorSpace(.sRGB) else { return [1, 0, 1] }
    return [color.redComponent, color.greenComponent, color.blueComponent].map(Double.init)
}
var best = Double.infinity, bestOffset = 0, bestPatches: [Double] = []
// Include the system titlebar in the screenshot; discover its height rather than cropping pixels.
for offset in 0...64 {
    guard Int((440 + Double(offset)) * scale) <= capture.pixelsHigh + 2 else { continue }
    let errors = patches.map { patch -> Double in
        var error = 0.0, count = 0
        for y in stride(from: Int(patch.minY), to: Int(patch.maxY), by: 2) {
            for x in stride(from: Int(patch.minX), to: Int(patch.maxX), by: 2) {
                let expected = rgb(artwork, x, y)
                let actual = rgb(capture, Int((Double(x) + 0.5) * scale), Int((Double(y + offset) + 0.5) * scale))
                for c in 0..<3 { error += abs(expected[c] - actual[c]); count += 1 }
            }
        }
        return error / Double(count)
    }
    let mean = errors.reduce(0, +) / Double(errors.count)
    if mean < best { best = mean; bestOffset = offset; bestPatches = errors }
}
let passed = best < 0.035 && bestPatches.count == patches.count && bestPatches.allSatisfy { $0 < 0.055 }
let report: [String: Any] = ["renderedArtwork": passed, "meanAbsoluteRGBError": best.isFinite ? best : -1,
                           "patchErrors": bestPatches, "titlebarPoints": bestOffset, "scale": scale,
                           "maintainerVisualReviewRequired": true]
print(String(data: try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]), encoding: .utf8)!)
exit(passed ? 0 : 1)
