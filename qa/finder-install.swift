import AppKit
import ApplicationServices

guard ProcessInfo.processInfo.environment["GITHUB_ACTIONS"] == "true",AXIsProcessTrusted(),CGPreflightPostEventAccess() else{print("Disposable hosted runner and existing input access required");exit(2)}
_ = NSApplication.shared
guard !FileManager.default.fileExists(atPath:"/Applications/ContextLens.app"),FileManager.default.isWritableFile(atPath:"/Applications") else{print("No safe empty writable installation destination");exit(3)}
guard let finder=NSWorkspace.shared.runningApplications.first(where:{$0.bundleIdentifier=="com.apple.finder"}) else{exit(4)}
let app=AXUIElementCreateApplication(finder.processIdentifier)
func get(_ e:AXUIElement,_ key:String)->CFTypeRef?{var v:CFTypeRef?;AXUIElementCopyAttributeValue(e,key as CFString,&v);return v}
let windows=get(app,kAXWindowsAttribute) as? [AXUIElement] ?? []
guard let window=windows.first(where:{(get($0,kAXTitleAttribute) as? String)=="ContextLens"}) else{print("Verified installer Finder window absent");exit(5)}
finder.activate(options:[]);AXUIElementPerformAction(window,kAXRaiseAction as CFString);RunLoop.current.run(until:Date().addingTimeInterval(0.5))
var origin=CGPoint.zero
guard let raw=get(window,kAXPositionAttribute),AXValueGetValue(raw as! AXValue,.cgPoint,&origin) else{exit(6)}
let start=CGPoint(x:origin.x+214,y:origin.y+28+254),end=CGPoint(x:origin.x+506,y:origin.y+28+254)
CGEvent(mouseEventSource:nil,mouseType:.leftMouseDown,mouseCursorPosition:start,mouseButton:.left)?.post(tap:.cghidEventTap)
RunLoop.current.run(until:Date().addingTimeInterval(0.5))
for i in 1...25{let f=Double(i)/25;let point=CGPoint(x:start.x+(end.x-start.x)*f,y:start.y+(end.y-start.y)*f);CGEvent(mouseEventSource:nil,mouseType:.leftMouseDragged,mouseCursorPosition:point,mouseButton:.left)?.post(tap:.cghidEventTap);RunLoop.current.run(until:Date().addingTimeInterval(0.04))}
CGEvent(mouseEventSource:nil,mouseType:.leftMouseUp,mouseCursorPosition:end,mouseButton:.left)?.post(tap:.cghidEventTap)
RunLoop.current.run(until:Date().addingTimeInterval(4))
let copied=FileManager.default.fileExists(atPath:"/Applications/ContextLens.app/Contents/Info.plist")
print("Real Finder drag produced installed app:",copied)
if let close=get(window,kAXCloseButtonAttribute){AXUIElementPerformAction(close as! AXUIElement,kAXPressAction as CFString)}
exit(copied ? 0:7)
