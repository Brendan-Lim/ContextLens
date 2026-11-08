// Repository-owned vector composition, rendered using system fonts and AppKit.
// No window, screen capture, Finder automation or third-party artwork is used.
import AppKit
import ImageIO
import UniformTypeIdentifiers

let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
let output = URL(fileURLWithPath: CommandLine.arguments[1])
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
let navy = NSColor(srgbRed: 0.118, green: 0.165, blue: 0.353, alpha: 1)
func color(_ r: CGFloat, _ g: CGFloat, _ b: CGFloat, _ a: CGFloat = 1) -> NSColor {
    NSColor(srgbRed: r, green: g, blue: b, alpha: a)
}
func text(_ string: String, _ x: CGFloat, _ y: CGFloat, _ size: CGFloat, _ weight: NSFont.Weight = .regular, _ ink: NSColor = navy) {
    (string as NSString).draw(at: NSPoint(x: x, y: y), withAttributes: [.font: NSFont.systemFont(ofSize: size, weight: weight), .foregroundColor: ink])
}
func rounded(_ rect: NSRect, _ radius: CGFloat, _ fill: NSColor) {
    fill.setFill(); NSBezierPath(roundedRect: rect, xRadius: radius, yRadius: radius).fill()
}
func brand(_ x: CGFloat, _ y: CGFloat, _ width: CGFloat) {
    let image = NSImage(contentsOf: root.appendingPathComponent("Brand/wordmark.svg"))!
    image.draw(in: NSRect(x: x, y: y, width: width, height: width * 77 / 500), from: .zero, operation: .sourceOver, fraction: 1, respectFlipped: true, hints: nil)
}
func render(_ name: String, _ width: Int, _ height: Int, _ scale: Int, _ draw: () -> Void) {
    let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: width * scale, pixelsHigh: height * scale, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    let cg = NSGraphicsContext(bitmapImageRep: bitmap)!.cgContext
    cg.translateBy(x: 0, y: CGFloat(height * scale)); cg.scaleBy(x: CGFloat(scale), y: -CGFloat(scale))
    NSGraphicsContext.current = NSGraphicsContext(cgContext: cg, flipped: true)
    draw()
    NSGraphicsContext.restoreGraphicsState()
    let destination = CGImageDestinationCreateWithURL(output.appendingPathComponent(name) as CFURL, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(destination, bitmap.cgImage!, [:] as CFDictionary)
    precondition(CGImageDestinationFinalize(destination))
}
func installer(_ alternate: Bool) {
    NSGradient(starting: color(0.96, 0.985, 1), ending: color(0.77, 0.87, 0.99))!.draw(in: NSRect(x: 0, y: 0, width: 720, height: 440), angle: 70)
    // Broad translucent light: no decorations behind the real Finder labels.
    rounded(NSRect(x: 396, y: -190, width: 520, height: 420), 210, color(1, 1, 1, 0.20))
    brand(40, 28, 182)
    text("Install ContextLens", 40, 91, 33, .semibold)
    text("Drag ContextLens into Applications to get started.", 42, 139, 15, .regular, color(0.30, 0.39, 0.54))
    let panel = alternate ? NSRect(x: 110, y: 190, width: 500, height: 161) : NSRect(x: 132, y: 184, width: 164, height: 165)
    rounded(panel.offsetBy(dx: 0, dy: 5), 30, color(0.29, 0.48, 0.72, 0.08))
    rounded(panel, 30, color(1, 1, 1, alternate ? 0.42 : 0.61))
    if !alternate {
        rounded(NSRect(x: 424, y: 189, width: 164, height: 165), 30, color(0.29, 0.48, 0.72, 0.08))
        rounded(NSRect(x: 424, y: 184, width: 164, height: 165), 30, color(1, 1, 1, 0.61))
    }
    // The icon wells remain empty. Only Finder supplies functional icons.
    let arrow = NSBezierPath()
    arrow.move(to: NSPoint(x: 326, y: 254)); arrow.curve(to: NSPoint(x: 392, y: 254), controlPoint1: NSPoint(x: 348, y: 240), controlPoint2: NSPoint(x: 371, y: 240))
    arrow.move(to: NSPoint(x: 381, y: 240)); arrow.line(to: NSPoint(x: 395, y: 254)); arrow.line(to: NSPoint(x: 381, y: 266))
    arrow.lineWidth = 4; arrow.lineCapStyle = .round; arrow.lineJoinStyle = .round
    color(0.29, 0.49, 0.79).setStroke(); arrow.stroke()
    text("Drag to Applications  ·  Open from Launchpad", 202, 389, 12, .medium, color(0.32, 0.41, 0.56))
}
render("background.png", 720, 440, 2) { installer(false) }
render("background@1x.png", 720, 440, 1) { installer(false) }
render("composition-b.png", 720, 440, 2) { installer(true) }
render("hero.png", 1200, 460, 1) {
    NSGradient(starting: color(0.96, 0.985, 1), ending: color(0.78, 0.88, 1))!.draw(in: NSRect(x: 0, y: 0, width: 1200, height: 460), angle: 20)
    rounded(NSRect(x: 870, y: -140, width: 450, height: 600), 220, color(1, 1, 1, 0.24))
    brand(64, 49, 290)
    text("Give your AI agent eyes.", 60, 139, 63, .semibold)
    text("Stop explaining your UI. Just show it.", 64, 226, 27, .regular)
    text("Capture   →   Review   →   Mark Up   →   Hand Off", 65, 324, 20, .medium, color(0.30, 0.41, 0.59))
    let mascot = NSImage(contentsOf: root.appendingPathComponent("Brand/AppIcon.icns"))!
    mascot.draw(in: NSRect(x: 910, y: 137, width: 216, height: 216), from: .zero, operation: .sourceOver, fraction: 1, respectFlipped: true, hints: nil)
    text("Native macOS  ·  Local-first  ·  Open source", 65, 401, 16, .regular, color(0.30, 0.41, 0.59))
}
// Explicit design proof with placeholders. Never represented as a Finder screenshot.
render("installer-preview.png", 720, 488, 2) {
    installer(false)
    for (x, file, label) in [(CGFloat(214), "Brand/AppIcon.icns", "ContextLens"),
                              (CGFloat(506), "Brand/mascot-icon.svg", "Applications") ] {
        if label == "ContextLens" {
            NSImage(contentsOf: root.appendingPathComponent(file))!.draw(in: NSRect(x: x - 52, y: 202, width: 104, height: 104), from: .zero, operation: .sourceOver, fraction: 1, respectFlipped: true, hints: nil)
        } else {
            // Diagrammatic folder; real disk uses the Finder-provided /Applications symlink icon.
            rounded(NSRect(x: x - 45, y: 220, width: 90, height: 63), 9, color(0.34, 0.64, 0.96))
            rounded(NSRect(x: x - 45, y: 210, width: 39, height: 22), 5, color(0.43, 0.72, 1))
            text("A", x - 12, 229, 34, .medium, color(1, 1, 1, 0.85))
        }
        let size = (label as NSString).size(withAttributes: [.font: NSFont.systemFont(ofSize: 13)])
        text(label, x - size.width / 2, 315, 13)
    }
    color(0.95, 0.97, 1).setFill(); NSRect(x: 0, y: 440, width: 720, height: 48).fill()
    text("DESIGN PREVIEW · Icon placement illustration · Finder appearance pending", 70, 457, 12, .medium)
}
