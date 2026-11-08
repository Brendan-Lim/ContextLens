import Foundation

public struct LumaFrame: Equatable, Sendable {
    public let width: Int; public let height: Int; public let pixels: [UInt8]
    public let sourceWidth: Int; public let sourceHeight: Int
    public init(width: Int, height: Int, pixels: [UInt8], sourceWidth: Int? = nil, sourceHeight: Int? = nil) throws {
        guard width > 0, height > 0, width <= Int.max / height, pixels.count == width * height else { throw LensError.invalid("Invalid luminance buffer.") }
        self.width = width; self.height = height; self.pixels = pixels
        self.sourceWidth = sourceWidth ?? width; self.sourceHeight = sourceHeight ?? height
        guard self.sourceWidth > 0, self.sourceHeight > 0 else { throw LensError.invalid("Invalid source dimensions.") }
    }
}
public struct Difference: Sendable {
    public let global: Double; public let regional: Double; public let changedPixels: Int
    public static func compare(_ a: LumaFrame, _ b: LumaFrame) -> Difference {
        guard a.width == b.width, a.height == b.height, a.sourceWidth == b.sourceWidth, a.sourceHeight == b.sourceHeight else { return Difference(global: 1, regional: 1, changedPixels: max(a.pixels.count, b.pixels.count)) }
        let tile = 10, cols = (a.width + tile - 1) / tile, rows = (a.height + tile - 1) / tile
        var counts = [Int](repeating: 0, count: cols * rows), sizes = counts, changed = 0
        for i in a.pixels.indices {
            let bucket = (i / a.width / tile) * cols + (i % a.width / tile)
            sizes[bucket] += 1
            if abs(Int(a.pixels[i]) - Int(b.pixels[i])) >= 18 { changed += 1; counts[bucket] += 1 }
        }
        let regional = zip(counts, sizes).map { Double($0.0) / Double(max(1, $0.1)) }.max() ?? 0
        return Difference(global: Double(changed) / Double(a.pixels.count), regional: regional, changedPixels: changed)
    }
}
public enum Sensitivity: String, Codable, CaseIterable, Sendable {
    case low, high
    // Decode/replay old benchmark settings without exposing a third Capture choice.
    case legacyBalanced = "balanced"
    public static let allCases: [Sensitivity] = [.low, .high]
    public var thresholds: (Double, Double, Int) {
        switch self { case .low: return (0.06, 0.36, 12); case .legacyBalanced: return (0.025, 0.16, 6); case .high: return (0.008, 0.08, 3) }
    }
}
/// Pure, deterministic streaming selector. Memory is independent of session duration.
public struct FrameSelector: Sendable {
    public var sensitivity: Sensitivity = .high
    public var settlingMS = 350
    public var maximumWaitMS = 1500
    public var maximumFrames = 100
    public var deduplicate = true
    public private(set) var committedCount = 0
    private var lastCommitted: LumaFrame?
    private var previous: LumaFrame?
    private var candidateSince: Int?
    private var stableSince: Int?
    private var lastTime = -1
    private var pendingManual = false
    private var scrolledDuringCandidate = false
    public init() {}
    private func meaningful(_ d: Difference) -> Bool {
        let (g,r,n) = sensitivity.thresholds
        return d.global >= g || (d.regional >= r && d.changedPixels >= n)
    }
    /// `holding` is true while the person is scrolling the window. Scrolling is one change, not one state per
    /// scroll position: nothing is committed until it stops and the view settles, unless a snapshot is requested.
    public mutating func observe(_ image: LumaFrame, at time: Int, manual: Bool = false, holding: Bool = false) -> Selection? {
        guard time >= lastTime, committedCount < maximumFrames else { return nil }
        lastTime = time
        defer { previous = image }
        pendingManual = pendingManual || manual
        guard let baseline = lastCommitted else { return commit(image, reason: "initial", score: 1) }
        let diff = Difference.compare(baseline, image)
        if !meaningful(diff) && !pendingManual && deduplicate {
            candidateSince = nil; stableSince = nil; scrolledDuringCandidate = false; return nil
        }
        if candidateSince == nil { candidateSince = time; stableSince = time }
        if let previous, meaningful(Difference.compare(previous, image)) { stableSince = time }
        if holding {
            scrolledDuringCandidate = true
            // The maximum wait counts from the end of scrolling, so a long scroll still settles before saving.
            candidateSince = time; stableSince = time
        }
        if pendingManual || (!holding && (time - (stableSince ?? time) >= settlingMS || time - (candidateSince ?? time) >= maximumWaitMS)) {
            let reason = pendingManual ? "manual" : scrolledDuringCandidate ? "scroll" : "visual_change"
            return commit(image, reason: reason, score: max(diff.global, diff.regional))
        }
        return nil
    }
    public mutating func flush(_ image: LumaFrame) -> Selection? {
        guard committedCount < maximumFrames, let baseline = lastCommitted else { return nil }
        let d = Difference.compare(baseline, image)
        guard candidateSince != nil || pendingManual, meaningful(d) || pendingManual || !deduplicate else { return nil }
        return commit(image, reason: pendingManual ? "manual" : scrolledDuringCandidate ? "scroll" : "stop_flush", score: max(d.global, d.regional))
    }
    private mutating func commit(_ image: LumaFrame, reason: String, score: Double) -> Selection {
        lastCommitted = image; candidateSince = nil; stableSince = nil; pendingManual = false; scrolledDuringCandidate = false; committedCount += 1
        return Selection(reason: reason, score: score)
    }
}
public struct Selection: Sendable { public let reason: String; public let score: Double }
