import Foundation

/// A preflight flag is a hint, not proof that ScreenCaptureKit can enumerate content.
public enum ScreenAccessProbe {
    public static func windows(preflightGranted: Bool, userInitiated: Bool, previouslyVerified: Bool,
                               load: () async throws -> [WindowChoice] = { try await WindowCapture.windows() }) async throws -> [WindowChoice]? {
        // Avoid triggering a first-use system prompt during passive app startup.
        guard preflightGranted || userInitiated || previouslyVerified else { return nil }
        // A successful API call, including an empty result, verifies access.
        return try await load()
    }
}
