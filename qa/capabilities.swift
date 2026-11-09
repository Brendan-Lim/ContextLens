import AppKit
import ApplicationServices
import Virtualization

var data: [String: Any] = [
    "observedAt": ISO8601DateFormatter().string(from: Date()),
    "screens": NSScreen.screens.map { ["width": $0.frame.width, "height": $0.frame.height, "scale": $0.backingScaleFactor] },
    "accessibilityTrusted": AXIsProcessTrusted(),
    "screenCapturePreflight": CGPreflightScreenCaptureAccess(),
    "postEventPreflight": CGPreflightPostEventAccess(),
    "virtualizationSupported": VZVirtualMachine.isSupported,
    "memoryBytes": ProcessInfo.processInfo.physicalMemory
]
let applications = NSWorkspace.shared.runningApplications
data["relevantApplications"] = applications.filter { app in
    let id = app.bundleIdentifier ?? ""
    return ["dev.contextlens.app", "com.apple.finder", "com.utmapp.UTM", "com.apple.ScreenSharing", "com.prect.ServicesMenu", "com.docker.docker", "com.apple.Virtualization.VirtualMachine"].contains(id) || id.lowercased().contains("virtual")
}.map { app -> [String: Any] in
    var entry: [String: Any] = ["bundleID": app.bundleIdentifier ?? "", "pid": app.processIdentifier, "active": app.isActive]
    if app.bundleIdentifier == "dev.contextlens.app", let url = app.bundleURL, let bundle = Bundle(url: url) {
        entry["version"] = bundle.object(forInfoDictionaryKey: "CFBundleShortVersionString")
        entry["build"] = bundle.object(forInfoDictionaryKey: "CFBundleVersion")
        entry["officialReceiptPresent"] = FileManager.default.fileExists(atPath: url.appendingPathComponent("Contents/Resources/official.json").path)
    }
    return entry
}
data["finderWindowIDs"] = (CGWindowListCopyWindowInfo(.optionOnScreenOnly, kCGNullWindowID) as? [[String: Any]] ?? []).filter {
    ($0[kCGWindowOwnerPID as String] as? Int32).map { pid in applications.contains { $0.processIdentifier == pid && $0.bundleIdentifier == "com.apple.finder" } } ?? false
}.map { $0[kCGWindowNumber as String] ?? 0 }
print(String(data: try JSONSerialization.data(withJSONObject: data, options: [.prettyPrinted, .sortedKeys]), encoding: .utf8)!)
