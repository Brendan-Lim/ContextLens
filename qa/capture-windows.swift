import AppKit
import ApplicationServices

guard ProcessInfo.processInfo.environment["GITHUB_ACTIONS"] == "true", ProcessInfo.processInfo.environment["RUNNER_ENVIRONMENT"] == "github-hosted", CGPreflightScreenCaptureAccess() else { exit(2) }

let output = URL(fileURLWithPath: CommandLine.arguments[1])
let allowed = Set(CommandLine.arguments.dropFirst(2))
let applications = NSWorkspace.shared.runningApplications
let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
var report: [[String: Any]] = []
for item in list {
    guard let pid = item[kCGWindowOwnerPID as String] as? Int32,
          let app = applications.first(where: { $0.processIdentifier == pid }),
          let bundle = app.bundleIdentifier, allowed.contains(bundle),
          let number = item[kCGWindowNumber as String] as? Int,
          (item[kCGWindowLayer as String] as? Int ?? 0) < 30 else { continue }
    let filename = "\(bundle)-\(number).png"
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
    process.arguments = ["-x", "-o", "-l", String(number), output.appendingPathComponent(filename).path]
    try process.run(); process.waitUntilExit()
    report.append(["bundle": bundle, "id": number, "bounds": item[kCGWindowBounds as String] ?? [:], "file": filename, "exitCode": process.terminationStatus])
}
print(String(data: try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]), encoding: .utf8)!)
