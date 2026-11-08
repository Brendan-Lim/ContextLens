import Foundation

public enum LensError: Error, LocalizedError {
    case invalid(String)
    public var errorDescription: String? { if case .invalid(let s) = self { return s }; return nil }
}
public struct Region: Codable, Equatable, Sendable {
    public var x: Double; public var y: Double; public var width: Double; public var height: Double
    public init(x: Double, y: Double, width: Double, height: Double) {
        self.x = x; self.y = y; self.width = width; self.height = height
    }
    public func validate() throws {
        guard [x,y,width,height].allSatisfy({ $0.isFinite && $0 >= 0 && $0 <= 1 }),
              width > 0, height > 0, x + width <= 1.0000001, y + height <= 1.0000001 else {
            throw LensError.invalid("Annotation lies outside the image bounds.")
        }
    }
}
public struct Point: Codable, Equatable, Sendable {
    public var x: Double; public var y: Double
    public init(x: Double, y: Double) { self.x = x; self.y = y }
}
public enum AnnotationKind: String, Codable, CaseIterable, Sendable {
    case rectangle, arrow, highlight, text, marker, redaction
    /// Older kinds remain decodable; only these tools can create new marks.
    public static let drawingTools: [AnnotationKind] = [.rectangle, .highlight]
    public var label: String { self == .highlight ? "Highlighter" : rawValue.capitalized }
}
public struct Annotation: Codable, Equatable, Identifiable, Sendable {
    public var id: String
    public var frameID: String
    public var kind: AnnotationKind
    public var region: Region
    public var points: [Point]
    public var instruction: String
    public var severity: String
    public init(id: String, frameID: String, kind: AnnotationKind, region: Region,
                points: [Point] = [], instruction: String = "", severity: String = "normal") {
        self.id = id; self.frameID = frameID; self.kind = kind; self.region = region
        self.points = points; self.instruction = instruction; self.severity = severity
    }
}
public struct Frame: Codable, Equatable, Identifiable, Sendable {
    public var id: String
    public var timestampMS: Int
    public var name: String
    public var imagePath: String
    public var width: Int
    public var height: Int
    public var displayScale: Double
    public var windowTitle: String?
    public var applicationName: String?
    public var captureReason: String
    public var changeScore: Double
    public var event: String?
    public var selected: Bool
    public init(id: String, timestampMS: Int, name: String, imagePath: String, width: Int, height: Int,
                displayScale: Double = 1, windowTitle: String? = nil, applicationName: String? = nil,
                captureReason: String = "visual_change", changeScore: Double = 0, event: String? = nil, selected: Bool = true) {
        self.id = id; self.timestampMS = timestampMS; self.name = name; self.imagePath = imagePath
        self.width = width; self.height = height; self.displayScale = displayScale; self.windowTitle = windowTitle
        self.applicationName = applicationName; self.captureReason = captureReason
        self.changeScore = changeScore; self.event = event; self.selected = selected
    }
}
public enum SessionMode: String, Codable, CaseIterable, Sendable { case visualFeedback, referenceCapture }
public struct Session: Codable, Equatable, Sendable {
    public var schemaVersion = 1
    public var id: String
    public var createdAt: Date
    public var mode: SessionMode
    public var task: String?
    public var frames: [Frame] = []
    public var annotations: [Annotation] = []
    public var nextIssueNumber = 1
    public init(id: String = UUID().uuidString.lowercased(), mode: SessionMode = .visualFeedback, createdAt: Date = Date()) {
        self.id = id; self.mode = mode; self.createdAt = createdAt
    }
    public mutating func addAnnotation(frameID: String, kind: AnnotationKind, region: Region, points: [Point] = [], instruction: String = "") throws -> String {
        try region.validate()
        guard frames.contains(where: { $0.id == frameID }) else { throw LensError.invalid("Unknown annotation frame.") }
        guard points.allSatisfy({ $0.x.isFinite && $0.y.isFinite && (0...1).contains($0.x) && (0...1).contains($0.y) }),
              nextIssueNumber > 0, nextIssueNumber < Int.max else { throw LensError.invalid("Invalid annotation points or exhausted issue counter.") }
        let id = String(format: "CL-%03lld", Int64(nextIssueNumber)); nextIssueNumber += 1
        annotations.append(Annotation(id: id, frameID: frameID, kind: kind, region: region, points: points, instruction: instruction))
        return id
    }
    public func validate() throws {
        guard schemaVersion == 1 else { throw LensError.invalid("Unsupported session schema version.") }
        guard Self.safeName(id), nextIssueNumber > 0,
              Set(frames.map { $0.id.lowercased() }).count == frames.count, Set(annotations.map { $0.id.lowercased() }).count == annotations.count else {
            throw LensError.invalid("Invalid or duplicate session identifiers.")
        }
        for f in frames {
            guard Self.safeName(f.id), f.width > 0, f.height > 0, f.width <= 32768, f.height <= 32768,
                  f.timestampMS >= 0, f.displayScale.isFinite, f.displayScale > 0,
                  f.changeScore.isFinite, (0...1).contains(f.changeScore) else { throw LensError.invalid("Invalid frame metadata.") }
            try Self.validatePath(f.imagePath)
        }
        let frameIDs = Set(frames.map(\.id))
        for a in annotations {
            guard Self.safeName(a.id), frameIDs.contains(a.frameID),
                  a.points.allSatisfy({ $0.x.isFinite && $0.y.isFinite && (0...1).contains($0.x) && (0...1).contains($0.y) }) else {
                throw LensError.invalid("Invalid annotation metadata.")
            }
            try a.region.validate()
        }
        let maxID = annotations.compactMap { Int($0.id.replacingOccurrences(of: "CL-", with: "")) }.max() ?? 0
        guard nextIssueNumber > maxID else { throw LensError.invalid("Issue counter would reuse an identifier.") }
    }
    public static func safeName(_ name: String) -> Bool {
        !name.isEmpty && name.unicodeScalars.allSatisfy { CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_").contains($0) }
    }
    public static func validatePath(_ path: String) throws {
        guard !path.isEmpty, !path.hasPrefix("/"), !path.contains("\\"), !path.contains(":"),
              path.split(separator: "/", omittingEmptySubsequences: false).allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }) else {
            throw LensError.invalid("Unsafe relative path: \(path)")
        }
    }
}
public enum SessionStore {
    public static func encoder() -> JSONEncoder {
        let e = JSONEncoder(); e.outputFormatting = [.prettyPrinted, .sortedKeys]; e.dateEncodingStrategy = .iso8601; return e
    }
    public static func save(_ session: Session, to folder: URL) throws {
        try session.validate()
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        try encoder().encode(session).write(to: folder.appendingPathComponent("session.json"), options: .atomic)
    }
    public static func load(from folder: URL) throws -> Session {
        let d = JSONDecoder(); d.dateDecodingStrategy = .iso8601
        let s = try d.decode(Session.self, from: Data(contentsOf: folder.appendingPathComponent("session.json")))
        try s.validate()
        for f in s.frames { _ = try resolve(f.imagePath, in: folder) }
        return s
    }
    public static func resolve(_ path: String, in root: URL) throws -> URL {
        try Session.validatePath(path)
        let base = root.resolvingSymlinksInPath().standardizedFileURL
        let url = path.split(separator: "/").reduce(base) { parent, part in
            parent.appendingPathComponent(String(part)).resolvingSymlinksInPath().standardizedFileURL
        }
        guard url.path.hasPrefix(base.path + "/") else { throw LensError.invalid("Image path escapes session directory.") }
        return url
    }
}
