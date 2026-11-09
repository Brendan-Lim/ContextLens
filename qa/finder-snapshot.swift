import AppKit
import ApplicationServices

guard ProcessInfo.processInfo.environment["GITHUB_ACTIONS"] == "true", CGPreflightScreenCaptureAccess() else { exit(2) }
_ = NSApplication.shared
let args = CommandLine.arguments
guard args.count == 3, FileManager.default.fileExists(atPath: args[1] + "/ContextLens.app/Contents/Resources/InstallerBackground.tiff") else { exit(3) }
guard let finder = NSWorkspace.shared.runningApplications.first(where: { $0.bundleIdentifier == "com.apple.finder" }) else { exit(4) }
let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
let matches = list.filter { ($0[kCGWindowOwnerPID as String] as? Int32) == finder.processIdentifier && ($0[kCGWindowName as String] as? String) == "ContextLens" }
guard matches.count == 1, let id = matches[0][kCGWindowNumber as String] as? Int else { print("No unique real installer window; no substitute captured"); exit(5) }
finder.activate(options: [])
RunLoop.current.run(until: Date().addingTimeInterval(0.5))
let capture = Process()
capture.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
capture.arguments = ["-x", "-o", "-l", String(id), args[2] + "/Finder.png"]
try capture.run(); capture.waitUntilExit()
print(String(data: try JSONSerialization.data(withJSONObject: ["windowID": id, "bounds": matches[0][kCGWindowBounds as String] ?? [:], "screens": NSScreen.screens.map { ["width": $0.frame.width, "height": $0.frame.height, "scale": $0.backingScaleFactor] }, "exitCode": capture.terminationStatus], options: [.prettyPrinted, .sortedKeys]), encoding: .utf8)!)
exit(capture.terminationStatus)
