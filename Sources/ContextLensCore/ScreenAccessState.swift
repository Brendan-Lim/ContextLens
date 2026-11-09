import Foundation

/// Access is verified only by a successful ScreenCaptureKit enumeration, never by preflight alone.
public enum ScreenAccessState: Equatable, Sendable {
    case unverified
    case verified
    case denied(String)
    case failed(String)

    public init(error: Error, permissionDenied: Bool) {
        var messages: [String] = []
        var current: NSError? = error as NSError
        // Bound nested diagnostics: malformed/cyclic error chains must not stall the UI.
        for _ in 0..<4 {
            guard let value = current else { break }
            messages.append("\(value.domain) (\(value.code)): \(value.localizedDescription)")
            if let reason = value.localizedFailureReason { messages.append(reason) }
            if let recovery = value.localizedRecoverySuggestion { messages.append(recovery) }
            current = value.userInfo[NSUnderlyingErrorKey] as? NSError
        }
        let details = messages.joined(separator: "\n")
        self = permissionDenied ? .denied(details) : .failed(details)
    }
    public var isVerified: Bool { self == .verified }
    public var errorDetails: String? {
        switch self {
        case .denied(let details), .failed(let details): return details
        default: return nil
        }
    }
    public var title: String {
        switch self {
        case .unverified: return "Screen Recording access unverified"
        case .verified: return "Screen Recording access verified"
        case .denied: return "Screen Recording access denied"
        case .failed: return "ScreenCaptureKit verification failed"
        }
    }
    public var message: String {
        switch self {
        case .unverified: return "Choose Check Access to try ScreenCaptureKit. macOS may ask you to allow this copy."
        case .verified: return "ScreenCaptureKit enumeration succeeded. Select a window to capture."
        case .denied: return "macOS denied ScreenCaptureKit access. Enable this copy in Screen & System Audio Recording, then reopen it if requested."
        case .failed: return "ScreenCaptureKit enumeration failed. Review the error details and choose Check Access to retry."
        }
    }
}
