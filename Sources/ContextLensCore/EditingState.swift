import Foundation

/// Undo keeps metadata only, with a bounded history and a monotonic issue counter.
public struct SessionHistory: Sendable {
    private var past: [Session] = []
    private var future: [Session] = []
    public let limit: Int
    public init(limit: Int = 50) { self.limit = max(0, limit) }
    public var canUndo: Bool { !past.isEmpty }
    public var canRedo: Bool { !future.isEmpty }
    public mutating func checkpoint(_ session: Session) {
        if limit > 0 {
            past.append(session)
            if past.count > limit { past.removeFirst(past.count - limit) }
        }
        future.removeAll()
    }
    public mutating func undo(_ session: Session) -> Session? {
        guard var previous = past.popLast() else { return nil }
        future.append(session)
        previous.nextIssueNumber = max(previous.nextIssueNumber, session.nextIssueNumber)
        return previous
    }
    public mutating func redo(_ session: Session) -> Session? {
        guard var next = future.popLast() else { return nil }
        past.append(session)
        next.nextIssueNumber = max(next.nextIssueNumber, session.nextIssueNumber)
        return next
    }
    public mutating func reset() { past.removeAll(); future.removeAll() }
}

/// Identifies pixels in the editor. Notes, task text, ticks and names do not change these pixels.
public struct EditorRenderRequest: Equatable, Sendable {
    public let source: URL
    public let revision: Int
    public let frame: Frame
    public let marks: [Annotation]
    public init(source: URL, revision: Int, frame: Frame, annotations: [Annotation]) {
        self.source = source; self.revision = revision
        // Keep only fields used by decoding/rendering so text editing never decodes the screenshot again.
        self.frame = Frame(id: frame.id, timestampMS: 0, name: "", imagePath: frame.imagePath, width: frame.width, height: frame.height)
        self.marks = annotations.filter { $0.frameID == frame.id }.map {
            Annotation(id: $0.id, frameID: $0.frameID, kind: $0.kind, region: $0.region, points: $0.points)
        }
    }
}

public enum FrameSelection {
    public static func resolve(_ selected: String?, in session: Session, preferIncluded: Bool = false) -> String? {
        if let selected, session.frames.contains(where: { $0.id == selected }) { return selected }
        return (preferIncluded ? session.frames.first(where: \.selected) : nil)?.id ?? session.frames.first?.id
    }
}

/// No event contents are retained. A different topmost window cannot hold capture in scroll mode.
public struct ScrollActivity: Sendable {
    private var lastTime: TimeInterval?
    public init() {}
    public mutating func observe(at time: TimeInterval, targetWindowID: UInt32, windowUnderPointer: UInt32?) {
        guard time.isFinite, time >= 0, targetWindowID == windowUnderPointer else { return }
        lastTime = time
    }
    public func holding(at time: TimeInterval) -> Bool {
        guard let lastTime, time.isFinite else { return false }
        return time >= lastTime && time - lastTime < 0.5
    }
}

/// Deterministic byte-bounded LRU. Oversized values are returned by callers without being retained.
public struct CostCache<Key: Hashable & Sendable, Value: Sendable>: Sendable {
    private struct Entry: Sendable { var value: Value; var cost: Int }
    private var entries: [Key: Entry] = [:]
    private var order: [Key] = [] // oldest first; the cache is deliberately small
    public let limit: Int
    public private(set) var cost = 0
    public var count: Int { entries.count }
    public init(limit: Int) { self.limit = max(0, limit) }
    public mutating func value(for key: Key) -> Value? {
        guard let entry = entries[key] else { return nil }
        order.removeAll { $0 == key }; order.append(key)
        return entry.value
    }
    public mutating func insert(_ value: Value, for key: Key, cost newCost: Int) {
        if let old = entries.removeValue(forKey: key) { cost -= old.cost }
        order.removeAll { $0 == key }
        guard newCost >= 0, newCost <= limit else { return }
        while cost > limit - newCost, let oldest = order.first {
            order.removeFirst()
            if let old = entries.removeValue(forKey: oldest) { cost -= old.cost }
        }
        entries[key] = Entry(value: value, cost: newCost); order.append(key); cost += newCost
        assert(cost >= 0 && cost <= limit && entries.count == order.count)
    }
    public mutating func removeAll() { entries.removeAll(); order.removeAll(); cost = 0 }
}
