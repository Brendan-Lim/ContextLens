import AppKit
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers
import ContextLensCore
import CryptoKit

public enum Images {
    public static func load(_ url: URL) throws -> CGImage {
        // Read through Foundation so file errors are reported directly before ImageIO decodes in memory.
        let data = try Data(contentsOf: url, options: .mappedIfSafe)
        return try decode(data, url: url)
    }
    /// The digest and decoded image describe the same read, never separate filesystem lookups.
    static func snapshot(_ url: URL) throws -> (image: CGImage, digest: SHA256.Digest) {
        let data = try Data(contentsOf: url)
        return (try decode(data, url: url), SHA256.hash(data: data))
    }
    private static func decode(_ data: Data, url: URL) throws -> CGImage {
        guard let source = CGImageSourceCreateWithData(data as CFData, nil), let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
            throw LensError.invalid("Cannot decode image: \(url.lastPathComponent)")
        }
        return image
    }
    public static func png(_ image: CGImage, to url: URL) throws {
        // ImageIO's URL writer hides disk-full and permission errors behind a false
        // finalize result. Encode separately, then let Foundation report the file
        // error and atomically preserve any existing image if the write fails.
        let data = NSMutableData()
        guard let dest = CGImageDestinationCreateWithData(data, UTType.png.identifier as CFString, 1, nil) else { throw LensError.invalid("Cannot encode PNG.") }
        CGImageDestinationAddImage(dest, image, nil)
        guard CGImageDestinationFinalize(dest) else { throw LensError.invalid("PNG encoding failed.") }
        try (data as Data).write(to: url, options: .atomic)
    }
    public static func luma(_ image: CGImage) throws -> LumaFrame {
        let w = 240, h = max(1, Int(Double(image.height) / Double(image.width) * Double(w)))
        let height = min(240, h)
        var bytes = [UInt8](repeating: 0, count: w * height)
        let ok = bytes.withUnsafeMutableBytes { data -> Bool in
            guard let ctx = CGContext(data: data.baseAddress, width: w, height: height, bitsPerComponent: 8, bytesPerRow: w, space: CGColorSpaceCreateDeviceGray(), bitmapInfo: 0) else { return false }
            ctx.interpolationQuality = .low; ctx.draw(image, in: CGRect(x: 0, y: 0, width: w, height: height)); return true
        }
        guard ok else { throw LensError.invalid("Cannot create comparison buffer.") }
        return try LumaFrame(width: w, height: height, pixels: bytes, sourceWidth: image.width, sourceHeight: image.height)
    }
    /// Coordinates match the editor: normalized, origin at the top left.
    /// `labels: false` leaves out the ID text; the editor draws its own numbered badges instead.
    public static func render(_ image: CGImage, annotations: [Annotation], overlays: Bool, labels: Bool = true) throws -> CGImage {
        // Validate all caller-supplied geometry before handing it to CoreGraphics/CoreText.
        for mark in annotations {
            try mark.region.validate()
            guard mark.points.allSatisfy({ $0.x.isFinite && $0.y.isFinite && (0...1).contains($0.x) && (0...1).contains($0.y) }) else {
                throw LensError.invalid("Invalid annotation drawing points.")
            }
        }
        let w = image.width, h = image.height
        guard let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                                  space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { throw LensError.invalid("Cannot allocate image renderer.") }
        ctx.draw(image, in: CGRect(x: 0, y: 0, width: w, height: h))
        ctx.translateBy(x: 0, y: CGFloat(h)); ctx.scaleBy(x: 1, y: -1)
        func rect(_ a: Annotation) -> CGRect {
            CGRect(x: a.region.x * Double(w), y: a.region.y * Double(h), width: a.region.width * Double(w), height: a.region.height * Double(h))
        }
        // Redactions are burned into every output before any overlay or crop is produced.
        for a in annotations where a.kind == .redaction {
            try a.region.validate(); ctx.setFillColor(CGColor(gray: 0, alpha: 1)); ctx.fill(rect(a).insetBy(dx: -1, dy: -1))
        }
        if overlays {
            let color = NSColor.systemOrange.cgColor
            ctx.setStrokeColor(color); ctx.setLineWidth(max(3, CGFloat(w) / 450)); ctx.setLineCap(.round); ctx.setLineJoin(.round)
            for a in annotations where a.kind != .redaction {
                let r = rect(a)
                switch a.kind {
                case .rectangle: ctx.stroke(r)
                case .highlight, .arrow:
                    let points = a.points.isEmpty ? [Point(x: a.region.x, y: a.region.y), Point(x: a.region.x + a.region.width, y: a.region.y + a.region.height)] : a.points
                    ctx.saveGState()
                    if a.kind == .highlight { ctx.setAlpha(0.45); ctx.setLineWidth(CGFloat(AnnotationGeometry.highlightWidth(imageWidth: Double(w)))) }
                    ctx.beginPath()
                    for (i,p) in points.enumerated() {
                        let point = CGPoint(x: p.x * Double(w), y: p.y * Double(h))
                        if i == 0 { ctx.move(to: point) } else { ctx.addLine(to: point) }
                    }
                    ctx.strokePath()
                    if a.kind == .arrow, let first = points.first, let last = points.last {
                        let p = CGPoint(x: last.x * Double(w), y: last.y * Double(h))
                        let angle = atan2(last.y * Double(h) - first.y * Double(h), last.x * Double(w) - first.x * Double(w))
                        for delta in [-0.5, 0.5] {
                            ctx.move(to: p); ctx.addLine(to: CGPoint(x: p.x - 18 * cos(angle + delta), y: p.y - 18 * sin(angle + delta)))
                        }
                        ctx.strokePath()
                    }
                    ctx.restoreGState()
                case .marker, .text: ctx.setFillColor(color); ctx.fillEllipse(in: CGRect(x: r.minX, y: r.minY, width: 25, height: 25))
                case .redaction: break
                }
                // Render stable issue IDs in every annotated image; text annotations also carry their label.
                guard labels else { continue }
                ctx.saveGState()
                let label = a.kind == .text ? "\(a.id): \(a.instruction)" : a.id
                ctx.translateBy(x: r.minX, y: max(18, r.minY)); ctx.scaleBy(x: 1, y: -1)
                let font = NSFont.monospacedSystemFont(ofSize: max(12, CGFloat(w) / 100), weight: .bold)
                let line = CTLineCreateWithAttributedString(NSAttributedString(string: label, attributes: [.font: font, .foregroundColor: NSColor.systemOrange]) as CFAttributedString)
                ctx.textPosition = .zero; CTLineDraw(line, ctx); ctx.restoreGState()
            }
        }
        guard let result = ctx.makeImage() else { throw LensError.invalid("Image rendering failed.") }; return result
    }
    public static func crop(_ image: CGImage, around region: Region) throws -> CGImage {
        try region.validate()
        let w = Double(image.width), h = Double(image.height)
        let r = CGRect(x: region.x * w, y: region.y * h, width: region.width * w, height: region.height * h)
        let padded = r.insetBy(dx: -max(24, w * 0.04), dy: -max(24, h * 0.04)).integral.intersection(CGRect(x: 0, y: 0, width: w, height: h))
        guard let crop = image.cropping(to: padded) else { throw LensError.invalid("Crop failed.") }; return crop
    }
}
