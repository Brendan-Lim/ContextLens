import Foundation

/// A capture binds both identifiers once; list order and application membership cannot retarget it.
public struct WindowIdentity: Equatable, Hashable, Sendable {
    public let windowID: UInt32
    public let processID: Int32
    public init(windowID: UInt32, processID: Int32) { self.windowID = windowID; self.processID = processID }
    public func selected<Window>(in windows: [Window], identity: (Window) -> WindowIdentity?) -> Window? {
        windows.first { identity($0) == self }
    }
}

public enum CaptureEndReason: String, Sendable {
    case userStopped, targetUnavailable, applicationExited, permissionDenied, captureFailed, frameLimit
}

public struct CaptureCompletion: Sendable {
    public let reason: CaptureEndReason
    public var captureError: String?
    public var flushError: String?
    public var saveError: String?
    public init(reason: CaptureEndReason, captureError: String? = nil, flushError: String? = nil, saveError: String? = nil) {
        self.reason = reason; self.captureError = captureError; self.flushError = flushError; self.saveError = saveError
    }
    public var needsRecovery: Bool { flushError != nil || saveError != nil }
    public var errorDetails: String? {
        let values = [captureError, flushError, saveError].compactMap { $0 }
        return values.isEmpty ? nil : values.joined(separator: "\n")
    }
    public func status(frameCount: Int) -> String {
        let count = "\(frameCount) \(frameCount == 1 ? "state" : "states")"
        if saveError != nil { return "\(count) retained for recovery. Session save failed; free space or restore folder access, then choose Save Session." }
        if flushError != nil { return "\(count) saved. The last pending image could not be saved; choose Save Session to retry." }
        let saved = frameCount == 0 ? "No states captured. The empty session was saved." : "\(count) saved locally. Review and annotate."
        switch reason {
        case .targetUnavailable: return "The selected window is no longer available. Recording stopped. " + saved
        case .applicationExited: return "The selected application exited. Recording stopped. " + saved
        case .permissionDenied: return "Screen capture access was denied. Check Screen Recording settings and relaunch if requested. " + saved
        case .captureFailed: return "Screen capture stopped after an error. " + saved
        case .frameLimit: return "Maximum state count reached. " + saved
        case .userStopped: return frameCount == 0 ? saved + " Choose a window and start a new capture." : saved
        }
    }
}

/// One selected-target run. All OS, image, resource and persistence operations are injected.
/// Concurrent stop/run callers share one finalization; a new capture needs a new instance.
@MainActor public final class CaptureRun<Window, Sample> {
    public let target: WindowIdentity
    private let enumerate: () async throws -> [Window]
    private let identity: (Window) -> WindowIdentity?
    private let capture: (Window) async throws -> Sample
    private let consume: (Window, Sample) async throws -> Bool
    private let flush: () async throws -> Void
    private let save: () throws -> Void
    private let removeResources: () -> Void
    private let began: () -> Void
    private let missingReason: () -> CaptureEndReason
    private let classify: (Error) -> CaptureEndReason
    private let pause: (UInt64) async throws -> Void
    private let delay: UInt64
    private var task: Task<CaptureCompletion, Never>?
    private var requestedReason: CaptureEndReason?
    private var resourcesRemoved = false
    public var isStopping: Bool { requestedReason != nil || task?.isCancelled == true }
    public init(target: WindowIdentity, delayNanoseconds: UInt64 = 0,
                enumerate: @escaping () async throws -> [Window], identity: @escaping (Window) -> WindowIdentity?,
                capture: @escaping (Window) async throws -> Sample,
                consume: @escaping (Window, Sample) async throws -> Bool,
                flush: @escaping () async throws -> Void, save: @escaping () throws -> Void,
                removeResources: @escaping () -> Void, began: @escaping () -> Void = {},
                missingReason: @escaping () -> CaptureEndReason = { .targetUnavailable },
                classify: @escaping (Error) -> CaptureEndReason = { _ in .captureFailed },
                pause: @escaping (UInt64) async throws -> Void = { try await Task.sleep(nanoseconds: $0) }) {
        self.target = target; self.delay = delayNanoseconds; self.enumerate = enumerate; self.identity = identity
        self.capture = capture; self.consume = consume; self.flush = flush; self.save = save
        self.removeResources = removeResources; self.began = began; self.missingReason = missingReason
        self.classify = classify; self.pause = pause
    }
    public func run() async -> CaptureCompletion {
        if Task.isCancelled { cancelSampling() }
        let active: Task<CaptureCompletion, Never>
        if let task { active = task }
        else { active = Task { await self.execute() }; task = active }
        return await withTaskCancellationHandler {
            await active.value
        } onCancel: {
            active.cancel()
            Task { @MainActor in self.removeResourcesOnce() }
        }
    }
    public func stop() async -> CaptureCompletion {
        cancelSampling()
        return await run()
    }
    private func cancelSampling() {
        if requestedReason == nil { requestedReason = .userStopped }
        task?.cancel()
        removeResourcesOnce()
    }
    private func removeResourcesOnce() {
        guard !resourcesRemoved else { return }
        resourcesRemoved = true; removeResources()
    }
    private func checkActive() throws {
        try Task.checkCancellation()
        if requestedReason != nil { throw CancellationError() }
    }
    private func execute() async -> CaptureCompletion {
        var failure: String?
        do {
            try checkActive()
            if delay > 0 { try await pause(delay) }
            try checkActive(); began()
            while true {
                try checkActive()
                let windows = try await enumerate()
                try checkActive()
                guard let window = target.selected(in: windows, identity: identity) else {
                    requestedReason = requestedReason ?? missingReason(); break
                }
                let sample = try await capture(window)
                try checkActive()
                if try await !consume(window, sample) { requestedReason = requestedReason ?? .frameLimit; break }
                try checkActive(); try await pause(250_000_000)
            }
        } catch {
            if error is CancellationError || Task.isCancelled { requestedReason = requestedReason ?? .userStopped }
            else { failure = error.localizedDescription; requestedReason = requestedReason ?? classify(error) }
        }
        removeResourcesOnce()
        let reason = requestedReason ?? .userStopped
        // Finalization is deliberately independent of the cancelled sampling task.
        // A pending original-window image may still need encoding and persistence.
        let finalization = Task { @MainActor in
            var result = CaptureCompletion(reason: reason, captureError: failure)
            do { try await self.flush() } catch { result.flushError = error.localizedDescription }
            do { try self.save() } catch { result.saveError = error.localizedDescription }
            return result
        }
        return await finalization.value
    }
}
