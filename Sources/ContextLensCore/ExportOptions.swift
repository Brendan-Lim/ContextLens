import Foundation

public struct ExportOptions: Codable, Equatable, Sendable {
    public var annotatedOnly: Bool
    public var excludeDuplicates: Bool
    public init(annotatedOnly: Bool = true, excludeDuplicates: Bool = true) {
        self.annotatedOnly = annotatedOnly; self.excludeDuplicates = excludeDuplicates
    }
    public static let allFrames = ExportOptions(annotatedOnly: false, excludeDuplicates: false)
}

public struct ExportSummary: Codable, Equatable, Sendable {
    public var selectedFrames: Int
    public var includedFrames: Int
    public var includedAnnotations: Int
    public var unlabelledAnnotations: Int
    public var excludedUnannotated: Int
    public var excludedDuplicates: Int
    public var estimatedSourceBytes: Int64
    public init(selectedFrames: Int, includedFrames: Int, includedAnnotations: Int, unlabelledAnnotations: Int,
                excludedUnannotated: Int, excludedDuplicates: Int, estimatedSourceBytes: Int64) {
        self.selectedFrames = selectedFrames; self.includedFrames = includedFrames
        self.includedAnnotations = includedAnnotations; self.unlabelledAnnotations = unlabelledAnnotations
        self.excludedUnannotated = excludedUnannotated; self.excludedDuplicates = excludedDuplicates
        self.estimatedSourceBytes = estimatedSourceBytes
    }
}
