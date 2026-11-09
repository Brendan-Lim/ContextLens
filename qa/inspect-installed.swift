import AppKit
import ApplicationServices

_ = NSApplication.shared
var result:[String:Any]=[:]
if let app=NSWorkspace.shared.runningApplications.first(where:{$0.bundleIdentifier=="dev.contextlens.app" && $0.bundleURL?.path=="/Applications/ContextLens.app"}) {
    result["runningInstalledCopy"]=true;result["pid"]=app.processIdentifier
    result["finishedLaunching"]=app.isFinishedLaunching;result["active"]=app.isActive;result["hidden"]=app.isHidden;result["activationPolicy"]=app.activationPolicy.rawValue
    let bundle=Bundle(url:app.bundleURL!)!
    result["version"]=bundle.object(forInfoDictionaryKey:"CFBundleShortVersionString");result["build"]=bundle.object(forInfoDictionaryKey:"CFBundleVersion")
    let target=AXUIElementCreateApplication(app.processIdentifier)
    var windows:CFTypeRef?;AXUIElementCopyAttributeValue(target,kAXWindowsAttribute as CFString,&windows)
    result["windowCount"]=(windows as? [AXUIElement] ?? []).count
    if CommandLine.arguments.contains("--finish-onboarding"), ProcessInfo.processInfo.environment["GITHUB_ACTIONS"] == "true", AXIsProcessTrusted() {
        func get(_ element: AXUIElement, _ key: String) -> CFTypeRef? { var value: CFTypeRef?; AXUIElementCopyAttributeValue(element, key as CFString, &value); return value }
        func find(_ element: AXUIElement, _ depth: Int) -> AXUIElement? {
            guard depth < 20 else { return nil }
            if (get(element, kAXRoleAttribute) as? String) == kAXButtonRole,
               [kAXTitleAttribute, kAXDescriptionAttribute].contains(where: { (get(element, $0) as? String) == "Start using ContextLens" }) { return element }
            for child in get(element, kAXChildrenAttribute) as? [AXUIElement] ?? [] { if let button = find(child, depth+1) { return button } }
            return nil
        }
        if let button = find(target, 0) { result["onboardingButtonStatus"] = AXUIElementPerformAction(button, kAXPressAction as CFString).rawValue }
        else { result["onboardingButtonAbsent"] = true }
    }
    if CommandLine.arguments.contains("--terminate"), ProcessInfo.processInfo.environment["GITHUB_ACTIONS"] == "true" { result["terminationRequested"] = app.terminate() }
}else{result["runningInstalledCopy"]=false}
print(String(data:try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]),encoding:.utf8)!)
