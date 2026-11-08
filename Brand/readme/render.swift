// README artwork: repository-owned vector composition rendered with AppKit and system fonts.
// Decorative brand art only. It draws no ContextLens window, control or captured state, and
// must never stand in for a screenshot of the application or a Finder window.
import AppKit
import ImageIO
import UniformTypeIdentifiers

let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
let output = URL(fileURLWithPath: CommandLine.arguments[1])
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)

func color(_ r: CGFloat, _ g: CGFloat, _ b: CGFloat, _ a: CGFloat = 1) -> NSColor {
    NSColor(srgbRed: r, green: g, blue: b, alpha: a)
}

struct Palette {
    let top: NSColor, bottom: NSColor, glow: NSColor
    let ink: NSColor, soft: NSColor, accent: NSColor
    let card: NSColor, cardEdge: NSColor, shadow: NSColor, wordmark: String
}
let light = Palette(top: color(0.965, 0.985, 1), bottom: color(0.79, 0.88, 1), glow: color(1, 1, 1, 0.34),
                    ink: color(0.118, 0.165, 0.353), soft: color(0.30, 0.39, 0.55), accent: color(0.27, 0.50, 0.86),
                    card: color(1, 1, 1, 0.66), cardEdge: color(1, 1, 1, 0.9), shadow: color(0.29, 0.48, 0.72, 0.10),
                    wordmark: "Brand/wordmark.svg")
let dark = Palette(top: color(0.055, 0.082, 0.18), bottom: color(0.12, 0.18, 0.37), glow: color(0.55, 0.76, 1, 0.07),
                   ink: color(0.97, 0.98, 1), soft: color(0.72, 0.82, 0.96), accent: color(0.53, 0.75, 1),
                   card: color(1, 1, 1, 0.06), cardEdge: color(1, 1, 1, 0.13), shadow: color(0, 0, 0, 0.22),
                   wordmark: "Brand/wordmark-white.svg")

func font(_ size: CGFloat, _ weight: NSFont.Weight) -> NSFont { NSFont.systemFont(ofSize: size, weight: weight) }
func width(_ string: String, _ f: NSFont) -> CGFloat { (string as NSString).size(withAttributes: [.font: f]).width }
func text(_ string: String, _ x: CGFloat, _ y: CGFloat, _ f: NSFont, _ ink: NSColor, kern: CGFloat = 0) {
    (string as NSString).draw(at: NSPoint(x: x, y: y), withAttributes: [.font: f, .foregroundColor: ink, .kern: kern])
}
func centered(_ string: String, _ cx: CGFloat, _ y: CGFloat, _ f: NSFont, _ ink: NSColor) {
    text(string, cx - width(string, f) / 2, y, f, ink)
}
func rounded(_ rect: NSRect, _ radius: CGFloat) -> NSBezierPath { NSBezierPath(roundedRect: rect, xRadius: radius, yRadius: radius) }
func fill(_ path: NSBezierPath, _ c: NSColor) { c.setFill(); path.fill() }
func stroke(_ path: NSBezierPath, _ c: NSColor, _ w: CGFloat, dash: [CGFloat] = []) {
    c.setStroke(); path.lineWidth = w; path.lineCapStyle = .round; path.lineJoinStyle = .round
    if !dash.isEmpty { path.setLineDash(dash, count: dash.count, phase: 0) }
    path.stroke()
}
func image(_ file: String, _ rect: NSRect) {
    NSImage(contentsOf: root.appendingPathComponent(file))!
        .draw(in: rect, from: .zero, operation: .sourceOver, fraction: 1, respectFlipped: true, hints: nil)
}
func glass(_ rect: NSRect, _ radius: CGFloat, _ p: Palette) {
    fill(rounded(rect.offsetBy(dx: 0, dy: 6), radius), p.shadow)
    fill(rounded(rect, radius), p.card)
    stroke(rounded(rect.insetBy(dx: 0.5, dy: 0.5), radius), p.cardEdge, 1)
}

func render(_ name: String, _ w: Int, _ h: Int, _ scale: Int, _ draw: () -> Void) {
    let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: w * scale, pixelsHigh: h * scale, bitsPerSample: 8,
                                  samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB,
                                  bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    let cg = NSGraphicsContext(bitmapImageRep: bitmap)!.cgContext
    cg.translateBy(x: 0, y: CGFloat(h * scale)); cg.scaleBy(x: CGFloat(scale), y: -CGFloat(scale))
    NSGraphicsContext.current = NSGraphicsContext(cgContext: cg, flipped: true)
    draw()
    NSGraphicsContext.restoreGraphicsState()
    let destination = CGImageDestinationCreateWithURL(output.appendingPathComponent(name) as CFURL, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(destination, bitmap.cgImage!, [:] as CFDictionary)
    precondition(CGImageDestinationFinalize(destination))
}

func background(_ p: Palette, _ w: CGFloat, _ h: CGFloat) {
    NSGradient(starting: p.top, ending: p.bottom)!.draw(in: NSRect(x: 0, y: 0, width: w, height: h), angle: -20)
}

// Hero: wordmark, promise, tagline, three facts and the app icon on a soft glow.
func hero(_ p: Palette) {
    background(p, 1200, 460)
    fill(NSBezierPath(ovalIn: NSRect(x: 760, y: -40, width: 540, height: 540)), p.glow)
    fill(NSBezierPath(ovalIn: NSRect(x: 830, y: 30, width: 400, height: 400)), p.glow)
    image(p.wordmark, NSRect(x: 72, y: 66, width: 270, height: 270 * 77 / 500))
    text("Give your AI agent eyes.", 66, 150, font(62, .semibold), p.ink, kern: -0.6)
    text("Stop explaining your UI. Just show it.", 70, 238, font(28, .regular), p.soft)
    var x: CGFloat = 70
    for fact in ["Native macOS", "Local-first", "Open source"] {
        let f = font(17, .medium), w = width(fact, f) + 36
        let pill = NSRect(x: x, y: 328, width: w, height: 40)
        fill(rounded(pill, 20), p.card); stroke(rounded(pill.insetBy(dx: 0.5, dy: 0.5), 20), p.cardEdge, 1)
        text(fact, x + 18, 337, f, p.ink)
        x += w + 12
    }
    image("Brand/AppIcon.icns", NSRect(x: 900, y: 100, width: 260, height: 260))
}

// Workflow banner: four abstract step glyphs. None of them depicts the application's interface.
func glyph(_ step: Int, _ cx: CGFloat, _ cy: CGFloat, _ p: Palette) {
    let line: CGFloat = 4
    switch step {
    case 0: // A generic window with a record dot: "choose a window and capture it".
        let frame = NSRect(x: cx - 46, y: cy - 32, width: 92, height: 64)
        stroke(rounded(frame, 10), p.ink, line)
        let bar = NSBezierPath(); bar.move(to: NSPoint(x: cx - 46, y: cy - 14)); bar.line(to: NSPoint(x: cx + 46, y: cy - 14))
        stroke(bar, p.ink, line)
        for i in 0..<3 { fill(NSBezierPath(ovalIn: NSRect(x: cx - 37 + CGFloat(i) * 11, y: cy - 27, width: 7, height: 7)), p.ink) }
        fill(NSBezierPath(ovalIn: NSRect(x: cx + 22, y: cy + 10, width: 34, height: 34)), p.top)
        fill(NSBezierPath(ovalIn: NSRect(x: cx + 27, y: cy + 15, width: 24, height: 24)), color(0.96, 0.36, 0.40))
    case 1: // Three stacked states, the front one kept.
        for i in (0..<3).reversed() {
            let o = CGFloat(i) * 12
            let card = NSRect(x: cx - 40 + o, y: cy - 30 - o + 12, width: 72, height: 54)
            fill(rounded(card, 9), p.top)
            stroke(rounded(card, 9), i == 0 ? p.ink : p.ink.withAlphaComponent(0.45), line)
        }
        let tick = NSBezierPath()
        tick.move(to: NSPoint(x: cx - 18, y: cy + 10)); tick.line(to: NSPoint(x: cx - 7, y: cy + 21)); tick.line(to: NSPoint(x: cx + 14, y: cy - 2))
        stroke(tick, p.accent, 5)
    case 2: // A dashed selection with a numbered badge.
        stroke(rounded(NSRect(x: cx - 42, y: cy - 26, width: 84, height: 58), 8), p.accent, line, dash: [9, 7])
        fill(NSBezierPath(ovalIn: NSRect(x: cx - 58, y: cy - 42, width: 30, height: 30)), p.accent)
        centered("1", cx - 43, cy - 38, font(18, .bold), color(1, 1, 1))
        let cursor = NSBezierPath()
        cursor.move(to: NSPoint(x: cx + 30, y: cy + 20)); cursor.line(to: NSPoint(x: cx + 30, y: cy + 50))
        cursor.line(to: NSPoint(x: cx + 38, y: cy + 42)); cursor.line(to: NSPoint(x: cx + 50, y: cy + 44)); cursor.close()
        fill(cursor, p.ink)
    default: // A brief leaving for the agent.
        let sheet = NSRect(x: cx - 52, y: cy - 38, width: 58, height: 76)
        fill(rounded(sheet, 8), p.top); stroke(rounded(sheet, 8), p.ink, line)
        for (i, w) in [CGFloat(34), 26, 30].enumerated() {
            let l = NSBezierPath(); let y = cy - 18 + CGFloat(i) * 15
            l.move(to: NSPoint(x: cx - 40, y: y)); l.line(to: NSPoint(x: cx - 40 + w, y: y)); stroke(l, p.ink.withAlphaComponent(0.5), 3.5)
        }
        let arrow = NSBezierPath()
        arrow.move(to: NSPoint(x: cx + 18, y: cy + 4)); arrow.line(to: NSPoint(x: cx + 54, y: cy + 4))
        arrow.move(to: NSPoint(x: cx + 42, y: cy - 8)); arrow.line(to: NSPoint(x: cx + 55, y: cy + 4)); arrow.line(to: NSPoint(x: cx + 42, y: cy + 16))
        stroke(arrow, p.accent, 5)
    }
}

func workflow(_ p: Palette) {
    background(p, 1200, 300)
    let steps = ["Capture", "Review", "Mark Up", "Hand Off"]
    let cardW: CGFloat = 246, gap: CGFloat = 52, left = (1200 - 4 * cardW - 3 * gap) / 2
    for (i, step) in steps.enumerated() {
        let x = left + CGFloat(i) * (cardW + gap)
        glass(NSRect(x: x, y: 30, width: cardW, height: 232), 28, p)
        text(String(format: "%02d", i + 1), x + 22, 46, font(15, .semibold), p.soft, kern: 1)
        glyph(i, x + cardW / 2, 126, p)
        centered(step, x + cardW / 2, 192, font(32, .semibold), p.ink)
        if i < 3 {
            let c = NSBezierPath(), ax = x + cardW + gap / 2
            c.move(to: NSPoint(x: ax - 6, y: 134)); c.line(to: NSPoint(x: ax + 6, y: 146)); c.line(to: NSPoint(x: ax - 6, y: 158))
            stroke(c, p.soft, 4)
        }
    }
}

render("hero-light.png", 1200, 460, 2) { hero(light) }
render("hero-dark.png", 1200, 460, 2) { hero(dark) }
render("workflow-light.png", 1200, 300, 2) { workflow(light) }
render("workflow-dark.png", 1200, 300, 2) { workflow(dark) }
