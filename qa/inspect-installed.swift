import AppKit
import ApplicationServices

_ = NSApplication.shared
var result:[String:Any]=[:]
if let app=NSWorkspace.shared.runningApplications.first(where:{$0.bundleIdentifier=="dev.contextlens.app" && $0.bundleURL?.path=="/Applications/ContextLens.app"}) {
    result["runningInstalledCopy"]=true;result["pid"]=app.processIdentifier
    let bundle=Bundle(url:app.bundleURL!)!
    result["version"]=bundle.object(forInfoDictionaryKey:"CFBundleShortVersionString");result["build"]=bundle.object(forInfoDictionaryKey:"CFBundleVersion")
    let target=AXUIElementCreateApplication(app.processIdentifier)
    var windows:CFTypeRef?;AXUIElementCopyAttributeValue(target,kAXWindowsAttribute as CFString,&windows)
    result["windowCount"]=(windows as? [AXUIElement] ?? []).count
}else{result["runningInstalledCopy"]=false}
print(String(data:try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]),encoding:.utf8)!)
