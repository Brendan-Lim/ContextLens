// Deterministic illustration from owned browser fixture PNGs. Never captures a window.
import Foundation
import AppKit
import ImageIO
import UniformTypeIdentifiers
let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
let output = URL(fileURLWithPath: CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "/tmp/contextlens-fixture-demo.gif")
guard !FileManager.default.fileExists(atPath: output.path) else { fatalError("Choose a new demo output path") }
let frames = [
    ("Benchmarks/reports/browser-evidence/04/raw/initial.png", "Scripted synthetic browser fixture: menu closed"),
    ("Benchmarks/reports/browser-evidence/04/raw/interaction.png", "Scripted synthetic browser fixture: menu opened"),
    ("Benchmarks/reports/browser-evidence/04/contextlens/annotated/CL-001.png", "Synthetic fixture: example exported annotation")
]
guard let destination = CGImageDestinationCreateWithURL(output as CFURL, UTType.gif.identifier as CFString, frames.count, nil) else { fatalError("Cannot create GIF") }
CGImageDestinationSetProperties(destination, [kCGImagePropertyGIFDictionary: [kCGImagePropertyGIFLoopCount: 0]] as CFDictionary)
for (name, caption) in frames {
    guard let image = NSImage(contentsOf: root.appendingPathComponent(name)) else { fatalError("Missing public fixture") }
    let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 1100, pixelsHigh: 860, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
    NSColor(calibratedWhite: 0.96, alpha: 1).setFill(); NSRect(x: 0, y: 0, width: 1100, height: 860).fill()
    image.draw(in: NSRect(x: 0, y: 0, width: 1100, height: 800), from: .zero, operation: .sourceOver, fraction: 1)
    (caption as NSString).draw(at: NSPoint(x: 20, y: 818), withAttributes: [.font: NSFont.systemFont(ofSize: 21, weight: .semibold), .foregroundColor: NSColor.black])
    NSGraphicsContext.restoreGraphicsState()
    CGImageDestinationAddImage(destination, bitmap.cgImage!, [kCGImagePropertyGIFDictionary: [kCGImagePropertyGIFDelayTime: 1.6]] as CFDictionary)
}
guard CGImageDestinationFinalize(destination) else { fatalError("GIF encoding failed") }
print("Created a three-frame synthetic-fixture illustration. No native app workflow or first-run result is implied.")
