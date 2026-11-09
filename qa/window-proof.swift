import AppKit
import ScreenCaptureKit

guard ProcessInfo.processInfo.environment["GITHUB_ACTIONS"] == "true", CommandLine.arguments.count == 3,
      let id = UInt32(CommandLine.arguments[1]) else { exit(2) }
_ = NSApplication.shared
let content = try await SCShareableContent.excludingDesktopWindows(true,onScreenWindowsOnly:true)
guard let selected = content.windows.first(where: { $0.windowID == id }) else { exit(3) }
let filter = SCContentFilter(desktopIndependentWindow:selected)
guard let data = try? Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[2])),let pixels = NSBitmapImageRep(data:data) else { exit(4) }
let scale = Double(filter.pointPixelScale)
let configuration = SCStreamConfiguration()
configuration.width = Int(filter.contentRect.width * scale)
configuration.height = Int(filter.contentRect.height * scale)
configuration.showsCursor = false; configuration.ignoreShadowsSingleWindow = true
let image: CGImage = try await SCScreenshotManager.captureImage(contentFilter:filter,configuration:configuration)
let verified = scale == 2 && pixels.pixelsWide == Int(selected.frame.width * 2) && pixels.pixelsHigh == Int(selected.frame.height * 2)
let report:[String:Any] = ["windowID":id,"windowTitle":selected.title ?? "", "owner":selected.owningApplication?.applicationName ?? "",
    "windowBoundsPoints":["x":selected.frame.minX,"y":selected.frame.minY,"width":selected.frame.width,"height":selected.frame.height],
    "ScreenCaptureKitPointPixelScale":scale,"ScreenCaptureKitImagePixels":["width":image.width,"height":image.height],
    "nativeScreenshotPixels":["width":pixels.pixelsWide,"height":pixels.pixelsHigh],
    "genuine2x":verified,"captureMethod":"screencapture -x -o -l windowID; independent ScreenCaptureKit pointPixelScale and image check",
    "AppKitScreens":NSScreen.screens.map{["widthPoints":$0.frame.width,"heightPoints":$0.frame.height,"backingScaleFactor":$0.backingScaleFactor]}]
print(String(data:try JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]),encoding:.utf8)!)
exit(verified ? 0:5)
