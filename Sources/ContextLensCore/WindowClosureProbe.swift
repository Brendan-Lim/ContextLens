import Foundation

public struct WindowClosureSample: Codable, Sendable {
    public let requestStartedMS: Double
    public let requestCompletedMS: Double
    public let windowIDListed: Bool
    public let identityMatched: Bool
}

public struct WindowClosureResult: Codable, Sendable {
    public let outcome: String
    public let deadlineMS: Double
    public let checkpointMS: Double
    public let samples: [WindowClosureSample]
    public let error: String?
    /// The first lookup after the original wait; not a detection-by-200-ms guarantee.
    public var originalCheckpointAbsent: Bool {
        ["first-observation-absent", "eventual-disappearance"].contains(outcome) &&
            samples.first.map { !$0.identityMatched && $0.requestStartedMS >= checkpointMS } == true
    }
    public var firstObservationAbsent: Bool { samples.first?.identityMatched == false }
}

/// Pure diagnostic polling with an injected enumerator, monotonic clock and sleeper.
/// An API call completing after the deadline is a timeout even if it reports absence.
public enum WindowClosureProbe {
    @MainActor public static func observe(target: WindowIdentity, closedAt: Double, deadlineMS: Double = 2_000,
                                          intervalMS: Double = 50,
                                          now: () -> Double = { ProcessInfo.processInfo.systemUptime },
                                          enumerate: () async throws -> [WindowIdentity],
                                          pause: (UInt64) async throws -> Void = { try await Task.sleep(nanoseconds: $0) }) async -> WindowClosureResult {
        var samples: [WindowClosureSample] = []
        func result(_ outcome: String, error: String? = nil) -> WindowClosureResult {
            WindowClosureResult(outcome: outcome, deadlineMS: deadlineMS, checkpointMS: 200, samples: samples, error: error)
        }
        guard deadlineMS.isFinite, intervalMS.isFinite, closedAt.isFinite,
              deadlineMS >= 200, deadlineMS <= 10_000, intervalMS >= 10, intervalMS <= deadlineMS else { return result("invalid-policy") }
        // Match the old protocol: first lookup begins after a 200 ms wait following close().
        // Its completion can be later; this never establishes a 200 ms detection bound.
        let initial = (now() - closedAt) * 1_000
        guard initial.isFinite, initial >= 0 else { return result("invalid-clock") }
        do { if initial < 200 { try await pause(UInt64(ceil((200 - initial) * 1_000_000))) } }
        catch { return result(error is CancellationError ? "cancelled" : "enumeration-error", error: error.localizedDescription) }
        for _ in 0..<(Int(ceil(deadlineMS / intervalMS)) + 2) {
            let started = (now() - closedAt) * 1_000
            guard started.isFinite, started >= 200 else { return result("invalid-clock") }
            if started > deadlineMS { return result("timeout") }
            do {
                try Task.checkCancellation()
                let windows = try await enumerate()
                let completed = (now() - closedAt) * 1_000
                guard completed.isFinite, completed >= started else { return result("invalid-clock") }
                let matched = target.selected(in: windows, identity: { $0 }) != nil
                samples.append(WindowClosureSample(requestStartedMS: started, requestCompletedMS: completed,
                                                   windowIDListed: windows.contains { $0.windowID == target.windowID }, identityMatched: matched))
                if completed > deadlineMS { return result("timeout") }
                if !matched { return result(samples.count == 1 ? "first-observation-absent" : "eventual-disappearance") }
                let remaining = deadlineMS - completed
                if remaining <= 0 { return result("timeout") }
                try await pause(UInt64(max(1, ceil(min(intervalMS, remaining) * 1_000_000))))
            } catch {
                return result(error is CancellationError ? "cancelled" : "enumeration-error", error: error.localizedDescription)
            }
        }
        return result("timeout")
    }
}
