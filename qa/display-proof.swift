import AppKit
import CoreGraphics
import ScreenCaptureKit

func mode(_ m: CGDisplayMode) -> [String: Any] {
    ["width": m.width, "height": m.height, "pixelWidth": m.pixelWidth,
     "pixelHeight": m.pixelHeight, "refreshRate": m.refreshRate, "ioFlags": m.ioFlags]
}
func bounds(_ r: CGRect) -> [String: Double] {
    ["x": r.origin.x, "y": r.origin.y, "width": r.width, "height": r.height]
}
_ = NSApplication.shared
var displays = [CGDirectDisplayID](repeating: 0, count: 32)
var count: UInt32 = 0
CGGetOnlineDisplayList(32, &displays, &count)
let online = displays.prefix(Int(count)).map { id -> [String: Any] in
    var item: [String: Any] = ["id": id, "main": CGDisplayIsMain(id), "boundsPoints": bounds(CGDisplayBounds(id)),
        "CGDisplayPixelsWide": CGDisplayPixelsWide(id), "CGDisplayPixelsHigh": CGDisplayPixelsHigh(id),
        "vendor": CGDisplayVendorNumber(id), "model": CGDisplayModelNumber(id)]
    if let current = CGDisplayCopyDisplayMode(id) { item["currentMode"] = mode(current) }
    let options = [kCGDisplayShowDuplicateLowResolutionModes: true] as CFDictionary
    item["allModesIncludingDuplicateLowResolution"] = (CGDisplayCopyAllDisplayModes(id, options) as? [CGDisplayMode] ?? []).map(mode)
    return item
}
var result: [String: Any] = ["onlineDisplays": online, "screens": NSScreen.screens.map { s -> [String: Any] in
    ["displayID": (s.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber)?.uint32Value ?? 0,
     "framePoints": bounds(s.frame), "visibleFramePoints": bounds(s.visibleFrame), "backingScaleFactor": s.backingScaleFactor,
     "backingFramePixels": bounds(s.convertRectToBacking(s.frame))]
}, "macOS": ProcessInfo.processInfo.operatingSystemVersionString,
   "screenCapturePreflight": CGPreflightScreenCaptureAccess(), "hostEnvironment": "disposable GitHub-hosted runner"]
if CommandLine.arguments.contains("--fixture") {
    guard ProcessInfo.processInfo.environment["GITHUB_ACTIONS"] == "true" else { exit(2) }
    let window = NSWindow(contentRect: NSRect(x: 80,y: 80,width: 640,height: 320), styleMask: [.titled], backing: .buffered, defer: false)
    window.title = "ContextLens Retina rendering probe"
    let label = NSTextField(labelWithString: "Native AppKit Retina probe · Aa 123 · 13 pt")
    label.font = .systemFont(ofSize: 13); label.frame = NSRect(x: 20,y: 150,width: 590,height: 30)
    window.contentView?.addSubview(label); window.makeKeyAndOrderFront(nil)
    NSApp.activate(ignoringOtherApps: true)
    RunLoop.current.run(until: Date().addingTimeInterval(2))
    result["fixtureWindow"] = ["framePoints": bounds(window.frame), "backingScaleFactor": window.backingScaleFactor,
        "contentPixels": bounds(window.convertToBacking(window.contentView!.bounds)), "windowID": window.windowNumber]
    let destination = ProcessInfo.processInfo.environment["RUNNER_TEMP"]! + "/retina-probe.png"
    let capture = Process(); capture.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
    capture.arguments = ["-x","-o","-l",String(window.windowNumber),destination]
    try capture.run(); capture.waitUntilExit()
    if let data = try? Data(contentsOf: URL(fileURLWithPath: destination)), let image = NSBitmapImageRep(data: data) {
        result["nativeScreenshot"] = ["width":image.pixelsWide,"height":image.pixelsHigh,"exitCode":Int(capture.terminationStatus)]
    }
    let semaphore = DispatchSemaphore(value: 0)
    Task { @MainActor in
        do {
            let content = try await SCShareableContent.excludingDesktopWindows(true,onScreenWindowsOnly:true)
            if let selected = content.windows.first(where: { $0.windowID == CGWindowID(window.windowNumber) }) {
                let filter = SCContentFilter(desktopIndependentWindow:selected)
                let configuration = SCStreamConfiguration()
                configuration.width = Int(selected.frame.width * Double(filter.pointPixelScale))
                configuration.height = Int(selected.frame.height * Double(filter.pointPixelScale))
                configuration.showsCursor = false
                let image = try await SCScreenshotManager.captureImage(contentFilter:filter,configuration:configuration)
                result["ScreenCaptureKit"] = ["framePoints":bounds(selected.frame),"pointPixelScale":filter.pointPixelScale,
                    "capturedPixelWidth":image.width,"capturedPixelHeight":image.height]
            }
        } catch { result["ScreenCaptureKitError"] = String(describing:error) }
        semaphore.signal()
    }
    let deadline = Date().addingTimeInterval(20)
    while semaphore.wait(timeout:.now()) != .success && Date() < deadline { RunLoop.current.run(until:Date().addingTimeInterval(0.05)) }
    window.orderOut(nil)
}
print(String(data:try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]),encoding:.utf8)!)
