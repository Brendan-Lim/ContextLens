import AppKit
import ApplicationServices

guard ProcessInfo.processInfo.environment["GITHUB_ACTIONS"] == "true" else{exit(2)}
_ = NSApplication.shared
let allowed:Set<String>=["com.apple.CoreServicesUIAgent","com.apple.SecurityAgent","dev.contextlens.app","com.apple.Safari"]
var result:[[String:Any]]=[]
for running in NSWorkspace.shared.runningApplications where allowed.contains(running.bundleIdentifier ?? "") {
    var texts:[String]=[]
    let app=AXUIElementCreateApplication(running.processIdentifier)
    AXUIElementSetMessagingTimeout(app,3)
    func get(_ e:AXUIElement,_ key:String)->CFTypeRef?{var raw:CFTypeRef?;AXUIElementCopyAttributeValue(e,key as CFString,&raw);return raw}
    func walk(_ e:AXUIElement,_ depth:Int){
        guard depth<14,texts.count<250 else{return}
        for key in [kAXTitleAttribute,kAXDescriptionAttribute,kAXValueAttribute]{if let text=get(e,key) as? String,!text.isEmpty{texts.append(text)}}
        for child in get(e,kAXChildrenAttribute) as? [AXUIElement] ?? []{walk(child,depth+1)}
    }
    let windows=get(app,kAXWindowsAttribute) as? [AXUIElement] ?? []
    for window in windows{walk(window,0)}
    result.append(["bundle":running.bundleIdentifier ?? "","pid":running.processIdentifier,"windows":windows.count,"observedText":texts])
}
print(String(data:try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]),encoding:.utf8)!)
