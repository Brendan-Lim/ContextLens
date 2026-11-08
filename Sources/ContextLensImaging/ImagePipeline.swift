import Foundation
import os
import CoreGraphics
import ImageIO
import ContextLensCore

/// Serial decoding prevents a large timeline from spawning one full image allocation per thumbnail.
/// Callers discard cancelled or superseded requests before publishing them on the main actor.
public actor ImagePipeline {
    public static let shared = ImagePipeline()
    private struct ThumbnailKey: Hashable { let url: URL; let revision: Int; let maximum: Int }
    private var thumbnails: CostCache<ThumbnailKey, CGImage>
    private var sourceKey: EditorRenderRequest?
    private var sourceImage: CGImage?
    private let log = Logger(subsystem: "dev.contextlens.app", category: "Images")
    public private(set) var thumbnailDecodes = 0
    public private(set) var editorDecodes = 0
    public private(set) var editorRenders = 0
    public var thumbnailBytes: Int { thumbnails.cost }
    public init(thumbnailLimit: Int = 32 * 1024 * 1024) { thumbnails = CostCache(limit: thumbnailLimit) }

    public func thumbnail(at url: URL, revision: Int = 0, maximum: Int = 520) throws -> CGImage {
        try Task.checkCancellation()
        guard (1...2048).contains(maximum) else { throw LensError.invalid("Invalid thumbnail size.") }
        let key = ThumbnailKey(url: url, revision: revision, maximum: maximum)
        if let cached = thumbnails.value(for: key) { return cached }
        let image = try autoreleasepool { () throws -> CGImage in
            let data = try Data(contentsOf: url, options: .mappedIfSafe)
            guard let source = CGImageSourceCreateWithData(data as CFData, [kCGImageSourceShouldCache: false] as CFDictionary),
                  let image = CGImageSourceCreateThumbnailAtIndex(source, 0, [kCGImageSourceCreateThumbnailFromImageAlways: true,
                      kCGImageSourceThumbnailMaxPixelSize: maximum, kCGImageSourceShouldCacheImmediately: true] as CFDictionary) else {
                throw LensError.invalid("Cannot decode thumbnail.")
            }
            return image
        }
        try Task.checkCancellation()
        thumbnailDecodes += 1
        thumbnails.insert(image, for: key, cost: image.bytesPerRow * image.height)
        assert(image.width <= maximum && image.height <= maximum)
        return image
    }
    public func render(_ request: EditorRenderRequest) throws -> CGImage {
        try Task.checkCancellation()
        let started = DispatchTime.now().uptimeNanoseconds
        defer {
            let ms = Double(DispatchTime.now().uptimeNanoseconds - started) / 1_000_000
            log.debug("Editor render ms=\(ms, privacy: .public) decodes=\(self.editorDecodes, privacy: .public) renders=\(self.editorRenders, privacy: .public)")
        }
        let key = EditorRenderRequest(source: request.source, revision: request.revision, frame: request.frame, annotations: [])
        let image: CGImage
        if sourceKey == key, let cached = sourceImage { image = cached }
        else {
            image = try Images.load(SessionStore.resolve(request.frame.imagePath, in: request.source))
            guard image.width == request.frame.width, image.height == request.frame.height else { throw LensError.invalid("Editor image dimensions disagree with metadata.") }
            try Task.checkCancellation()
            sourceKey = key; sourceImage = image; editorDecodes += 1
        }
        let rendered = try autoreleasepool { try Images.render(image, annotations: request.marks, overlays: true, labels: false) }
        try Task.checkCancellation()
        editorRenders += 1
        return rendered
    }
    public func clear() { thumbnails.removeAll(); sourceKey = nil; sourceImage = nil }
}
