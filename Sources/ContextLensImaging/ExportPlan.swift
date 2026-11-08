import Foundation
import CryptoKit
import CoreGraphics
import ContextLensCore

/// A single immutable selection drives the preview, report, manifest, and written images.
public struct ExportPlan: Sendable {
    public let sourceSession: Session
    public let session: Session
    public let source: URL
    public let options: ExportOptions
    public let summary: ExportSummary

    public static func prepare(_ original: Session, source: URL, options: ExportOptions = ExportOptions()) throws -> ExportPlan {
        try original.validate()
        let selected = original.frames.filter(\.selected)
        // Every mark protects its frame, including blank labels and legacy annotation kinds.
        let annotatedIDs = Set(original.annotations.map(\.frameID))
        let candidates = selected.filter { !options.annotatedOnly || annotatedIDs.contains($0.id) }
        var fingerprints: [String: String] = [:]
        var sizes: [String: Int64] = [:]
        for frame in candidates {
            try Task.checkCancellation()
            let url = try SessionStore.resolve(frame.imagePath, in: source)
            let image = try Images.load(url)
            guard image.width == frame.width, image.height == frame.height else { throw LensError.invalid("Image dimensions disagree with metadata for \(frame.id).") }
            if options.excludeDuplicates && !options.annotatedOnly { fingerprints[frame.id] = try pixelFingerprint(image) }
            sizes[frame.id] = (try FileManager.default.attributesOfItem(atPath: url.path)[.size] as? NSNumber)?.int64Value ?? 0
        }
        var included = candidates
        if options.excludeDuplicates && !options.annotatedOnly {
            // Prefer annotated frames even when they occur later in review order.
            let protected = Set(candidates.filter { annotatedIDs.contains($0.id) }.compactMap { fingerprints[$0.id] })
            var seen = Set<String>()
            included = candidates.filter { frame in
                if annotatedIDs.contains(frame.id) { return true }
                guard let digest = fingerprints[frame.id], !protected.contains(digest), !seen.contains(digest) else { return false }
                seen.insert(digest); return true
            }
        }
        let includedIDs = Set(included.map(\.id))
        var filtered = original
        filtered.frames = included
        filtered.annotations = original.annotations.filter { includedIDs.contains($0.frameID) }
        let visible = filtered.annotations.filter { $0.kind != .redaction }
        let summary = ExportSummary(selectedFrames: selected.count, includedFrames: included.count, includedAnnotations: visible.count,
                                    unlabelledAnnotations: visible.filter { $0.instruction.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }.count,
                                    excludedUnannotated: selected.count-candidates.count, excludedDuplicates: candidates.count-included.count,
                                    estimatedSourceBytes: included.reduce(0) { $0 + (sizes[$1.id] ?? 0) })
        return ExportPlan(sourceSession: original, session: filtered, source: source, options: options, summary: summary)
    }

    /// Hash decoded, dimensioned sRGB pixels. PNG compression/metadata never determine duplicates.
    private static func pixelFingerprint(_ image: CGImage) throws -> String {
        let count = image.width * image.height * 4
        guard let space = CGColorSpace(name: CGColorSpace.sRGB),
              let ctx = CGContext(data: nil, width: image.width, height: image.height, bitsPerComponent: 8, bytesPerRow: image.width*4,
                                  space: space, bitmapInfo: CGBitmapInfo.byteOrder32Big.rawValue | CGImageAlphaInfo.premultipliedLast.rawValue),
              let data = ctx.data else { throw LensError.invalid("Cannot compare export image pixels.") }
        ctx.setBlendMode(.copy); ctx.draw(image, in: CGRect(x: 0, y: 0, width: image.width, height: image.height))
        var hash = SHA256()
        hash.update(data: Data("\(image.width)x\(image.height):".utf8))
        hash.update(bufferPointer: UnsafeRawBufferPointer(start: data, count: count))
        return hash.finalize().map { String(format: "%02x", $0) }.joined()
    }
}
