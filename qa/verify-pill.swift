import Foundation
import Vision

var records: [[String: Any]] = []
for path in CommandLine.arguments.dropFirst() {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = false
    request.recognitionLanguages = ["en-US"]
    do {
        try VNImageRequestHandler(url: URL(fileURLWithPath: path)).perform([request])
        let text = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }
        let fullStop = text.contains { $0.range(of: #"\bStop\b"#, options: .regularExpression) != nil }
        records.append(["file": URL(fileURLWithPath: path).lastPathComponent, "text": text, "fullStopLabelDetected": fullStop])
    } catch {
        records.append(["file": URL(fileURLWithPath: path).lastPathComponent, "fullStopLabelDetected": false, "ocrUnavailable": true])
    }
}
print(String(data: try JSONSerialization.data(withJSONObject: records, options: [.prettyPrinted, .sortedKeys]), encoding: .utf8)!)
exit(!records.isEmpty && records.allSatisfy { $0["fullStopLabelDetected"] as? Bool == true } ? 0 : 1)
