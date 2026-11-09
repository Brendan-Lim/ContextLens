import AppKit
import ApplicationServices

_ = NSApplication.shared
let args=CommandLine.arguments
let command=args.count>1 ? args[1] : "tree"
let options=args.count>2 ? (try JSONSerialization.jsonObject(with:Data(args[2].utf8)) as? [String:Any] ?? [:]) : [:]
func finish(_ value:[String:Any],_ status:Int32=0)->Never {print(String(data:try! JSONSerialization.data(withJSONObject:value,options:[.sortedKeys]),encoding:.utf8)!);exit(status)}
func drain(_ seconds:Double=0.2){RunLoop.current.run(until:Date().addingTimeInterval(seconds))}
if command=="display" {
    let display=CGMainDisplayID()
    let modes=CGDisplayCopyAllDisplayModes(display,nil) as? [CGDisplayMode] ?? []
    let candidates=modes.filter{$0.width>=1440 && $0.height>=900 && $0.width<=1920 && $0.height<=1200}.sorted{$0.width*$0.height > $1.width*$1.height}
    var status:CGError?;if let mode=candidates.first {status=CGDisplaySetDisplayMode(display,mode,nil)}
    finish(["modes":modes.map{["width":$0.width,"height":$0.height]},"setStatus":status?.rawValue ?? -1,"screens":NSScreen.screens.map{["width":$0.frame.width,"height":$0.frame.height,"scale":$0.backingScaleFactor]}])
}
guard AXIsProcessTrusted(), CGPreflightPostEventAccess() else{finish(["blocked":"Existing Accessibility/input access unavailable; no permission requested"],2)}
guard let running=NSWorkspace.shared.runningApplications.first(where:{$0.bundleIdentifier=="dev.contextlens.app"}) else{finish(["error":"Candidate not running"],3)}
guard running.bundleURL?.path.contains("/unpacked/ContextLens.app")==true else{finish(["error":"Refusing an unexpected application copy"],4)}
let app=AXUIElementCreateApplication(running.processIdentifier)
AXUIElementSetMessagingTimeout(app,3)
func get(_ e:AXUIElement,_ key:String)->CFTypeRef?{var v:CFTypeRef?;AXUIElementCopyAttributeValue(e,key as CFString,&v);return v}
let windows=get(app,kAXWindowsAttribute) as? [AXUIElement] ?? []
var nodes:[AXUIElement]=[];var rows:[[String:Any]]=[]
func walk(_ e:AXUIElement,_ depth:Int,_ parent:Int){
    guard depth<18 && nodes.count<2200 else{return}
    let id=nodes.count;nodes.append(e)
    var row:[String:Any]=["index":id,"depth":depth,"parent":parent]
    for key in [kAXRoleAttribute,kAXTitleAttribute,kAXDescriptionAttribute,kAXValueAttribute,kAXPlaceholderValueAttribute,kAXIdentifierAttribute,kAXHelpAttribute] {
        if let s=get(e,key) as? String {row[key]=s}
    }
    for key in [kAXEnabledAttribute,kAXSelectedAttribute,kAXFocusedAttribute] {if let b=get(e,key) as? NSNumber{row[key]=b}}
    if let p=get(e,kAXPositionAttribute),CFGetTypeID(p)==AXValueGetTypeID(){var v=CGPoint.zero;if AXValueGetValue(p as! AXValue,.cgPoint,&v){row["x"]=v.x;row["y"]=v.y}}
    if let p=get(e,kAXSizeAttribute),CFGetTypeID(p)==AXValueGetTypeID(){var v=CGSize.zero;if AXValueGetValue(p as! AXValue,.cgSize,&v){row["width"]=v.width;row["height"]=v.height}}
    var actions:CFArray?;if AXUIElementCopyActionNames(e,&actions) == .success{row["actions"]=actions as? [String] ?? []}
    rows.append(row)
    for child in get(e,kAXChildrenAttribute) as? [AXUIElement] ?? []{walk(child,depth+1,id)}
}
for window in windows{walk(window,0,-1)}
if command=="tree"{finish(["pid":running.processIdentifier,"nodes":rows])}
func area(_ window:AXUIElement)->Double {guard let raw=get(window,kAXSizeAttribute),CFGetTypeID(raw)==AXValueGetTypeID() else{return 0};var size=CGSize.zero;AXValueGetValue(raw as! AXValue,.cgSize,&size);return size.width*size.height}
let mainWindow=windows.max(by:{area($0)<area($1)})
func activate(){running.activate(options:[]);if let window=mainWindow{AXUIElementPerformAction(window,kAXRaiseAction as CFString)};drain(0.3)}
func chosen()->Int? {
    if let i=options["index"] as? Int, nodes.indices.contains(i){return i}
    let text=options["text"] as? String ?? ""
    let role=options["role"] as? String
    let exact=options["exact"] as? Bool ?? true
    let hits=rows.indices.filter{i in
        if (rows[i][kAXEnabledAttribute] as? Bool)==false{return false}
        if let role,rows[i][kAXRoleAttribute] as? String != role{return false}
        if options["actionable"] as? Bool ?? true, !(rows[i]["actions"] as? [String] ?? []).contains(kAXPressAction){return false}
        return [kAXTitleAttribute,kAXDescriptionAttribute,kAXValueAttribute,kAXPlaceholderValueAttribute].contains{key in
            guard let value=rows[i][key] as? String else{return false};return exact ? value==text : value.localizedCaseInsensitiveContains(text)
        }
    }
    let n=options["nth"] as? Int ?? 0
    return hits.indices.contains(n) ? hits[n] : nil
}
func key(_ code:CGKeyCode,_ flags:CGEventFlags=[]){for down in [true,false]{let e=CGEvent(keyboardEventSource:nil,virtualKey:code,keyDown:down)!;e.flags=flags;e.post(tap:.cghidEventTap)};drain()}
if command=="resize" {
    guard let main=mainWindow else{finish(["error":"No window"],5)}
    var point=CGPoint(x:options["x"] as? Double ?? 40,y:options["y"] as? Double ?? 40)
    var size=CGSize(width:options["width"] as? Double ?? 1320,height:options["height"] as? Double ?? 860)
    let a=AXUIElementSetAttributeValue(main,kAXPositionAttribute as CFString,AXValueCreate(.cgPoint,&point)!)
    let b=AXUIElementSetAttributeValue(main,kAXSizeAttribute as CFString,AXValueCreate(.cgSize,&size)!)
    finish(["positionStatus":a.rawValue,"sizeStatus":b.rawValue])
}
if command=="press" {
    guard let i=chosen() else{finish(["error":"Control not found","query":options],6)}
    let label=options["text"] as? String ?? ""
    guard !["Allow","Open Anyway","Open Settings","Open System Settings","Check Access"].contains(label) else{finish(["blocked":"Security/privacy approval control refused"],7)}
    let status=AXUIElementPerformAction(nodes[i],kAXPressAction as CFString);drain(0.4)
    finish(["status":status.rawValue,"index":i,"label":label],status == .success ? 0:8)
}
if command=="type" {
    guard let i=chosen(),let text=options["value"] as? String else{finish(["error":"Text control unavailable"],9)}
    activate();AXUIElementSetAttributeValue(nodes[i],kAXFocusedAttribute as CFString,kCFBooleanTrue);drain()
    key(0,.maskCommand)
    let chars=Array(text.utf16)
    let event=CGEvent(keyboardEventSource:nil,virtualKey:0,keyDown:true)!
    chars.withUnsafeBufferPointer{event.keyboardSetUnicodeString(stringLength:chars.count,unicodeString:$0.baseAddress!)}
    event.post(tap:.cghidEventTap);key(48);drain(0.5)
    finish(["typed":text,"index":i])
}
if command=="keys" {
    activate();let code=options["code"] as? Int ?? 53
    var flags:CGEventFlags=[];if options["command"] as? Bool == true{flags.insert(.maskCommand)};if options["shift"] as? Bool == true{flags.insert(.maskShift)}
    key(CGKeyCode(code),flags);finish(["posted":true])
}
if command=="snapshot" {
    guard CGPreflightScreenCaptureAccess(),let file=options["file"] as? String else{finish(["blocked":"Existing Screen Recording permission or destination unavailable"],12)}
    let title=options["title"] as? String
    let list=CGWindowListCopyWindowInfo([.optionOnScreenOnly,.excludeDesktopElements],kCGNullWindowID) as? [[String:Any]] ?? []
    let candidates=list.filter{($0[kCGWindowOwnerPID as String] as? Int32)==running.processIdentifier && (title == nil || ($0[kCGWindowName as String] as? String)==title)}
    func windowArea(_ item:[String:Any])->Double{guard let b=item[kCGWindowBounds as String] as? [String:Any] else{return 0};return (b["Width"] as? Double ?? 0)*(b["Height"] as? Double ?? 0)}
    guard let target=candidates.max(by:{windowArea($0)<windowArea($1)}),let id=target[kCGWindowNumber as String] as? Int else{finish(["error":"Selected candidate window not found; no substitute"],13)}
    let task=Process();task.executableURL=URL(fileURLWithPath:"/usr/sbin/screencapture");task.arguments=["-x","-o","-l",String(id),file];try task.run();task.waitUntilExit()
    finish(["file":file,"id":id,"bounds":target[kCGWindowBounds as String] ?? [:],"exitCode":task.terminationStatus],task.terminationStatus)
}
if command=="drag" {
    activate();guard let a=options["from"] as? [Double],let b=options["to"] as? [Double],a.count==2,b.count==2 else{finish(["error":"Invalid geometry"],10)}
    let start=CGPoint(x:a[0],y:a[1]),end=CGPoint(x:b[0],y:b[1])
    CGEvent(mouseEventSource:nil,mouseType:.leftMouseDown,mouseCursorPosition:start,mouseButton:.left)?.post(tap:.cghidEventTap);drain(0.08)
    for i in 1...14{let f=Double(i)/14;let point=CGPoint(x:start.x+(end.x-start.x)*f,y:start.y+(end.y-start.y)*f);CGEvent(mouseEventSource:nil,mouseType:.leftMouseDragged,mouseCursorPosition:point,mouseButton:.left)?.post(tap:.cghidEventTap);drain(0.025)}
    CGEvent(mouseEventSource:nil,mouseType:.leftMouseUp,mouseCursorPosition:end,mouseButton:.left)?.post(tap:.cghidEventTap);drain(0.5);finish(["posted":true])
}
if command=="click" {
    activate();guard let point=options["point"] as? [Double],point.count==2 else{finish(["error":"Invalid point"],14)}
    for type:CGEventType in [.leftMouseDown,.leftMouseUp]{CGEvent(mouseEventSource:nil,mouseType:type,mouseCursorPosition:CGPoint(x:point[0],y:point[1]),mouseButton:.left)?.post(tap:.cghidEventTap)};drain();finish(["posted":true])
}
finish(["error":"Unknown command"],11)
