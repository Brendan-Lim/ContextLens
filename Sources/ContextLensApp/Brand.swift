import SwiftUI

/// The Peek mascot, drawn from the same geometry as the published logo (a 100-unit box).
struct MascotView: View {
    enum Style { case icon, peek }
    var style: Style = .icon
    /// Smiling eyes and mouth: the mascot's "got it" face after a state is saved.
    var happy = false

    var body: some View {
        Canvas { context, size in
            let box: CGFloat = style == .icon ? 100 : 80
            let scale = min(size.width, size.height) / box
            context.translateBy(x: (size.width - box * scale) / 2, y: (size.height - box * scale) / 2)
            context.scaleBy(x: scale, y: scale)
            if style == .peek { context.translateBy(x: -10, y: -16) }
            if style == .icon { Mascot.drawTile(&context) }
            Mascot.drawBody(&context, happy: happy)
        }
        .accessibilityHidden(true)
    }
}

enum Mascot {
    static let navy = Color(hex: 0x1E2A5A)

    static func drawTile(_ context: inout GraphicsContext) {
        let tile = Path(roundedRect: CGRect(x: 0, y: 0, width: 100, height: 100), cornerRadius: 22.4, style: .continuous)
        context.fill(tile, with: .linearGradient(Gradient(colors: [Color(hex: 0xD3EBFF), Color(hex: 0x86BFFF)]),
                                                  startPoint: CGPoint(x: 50, y: 0), endPoint: CGPoint(x: 50, y: 100)))
        context.stroke(Path(roundedRect: CGRect(x: 0.7, y: 0.7, width: 98.6, height: 98.6), cornerRadius: 21.7, style: .continuous),
                       with: .color(.white.opacity(0.6)), lineWidth: 1.4)
        context.fill(sparkle(at: CGPoint(x: 20, y: 22), scale: 0.7), with: .color(.white))
    }

    static func sparkle(at center: CGPoint, scale k: CGFloat) -> Path {
        func point(_ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: center.x + x * k, y: center.y + y * k) }
        var path = Path()
        path.move(to: point(0, -6))
        path.addQuadCurve(to: point(6, 0), control: point(1, -1))
        path.addQuadCurve(to: point(0, 6), control: point(1, 1))
        path.addQuadCurve(to: point(-6, 0), control: point(-1, 1))
        path.addQuadCurve(to: point(0, -6), control: point(-1, -1))
        path.closeSubpath()
        return path
    }

    static func drawBody(_ context: inout GraphicsContext, happy: Bool = false) {
        var handle = Path()
        handle.move(to: CGPoint(x: 64, y: 38)); handle.addLine(to: CGPoint(x: 77, y: 25))
        context.stroke(handle, with: .color(navy), style: StrokeStyle(lineWidth: 8, lineCap: .round))

        let lens = Path(ellipseIn: CGRect(x: 29, y: 31, width: 42, height: 42))
        let glass = Gradient(stops: [.init(color: .white, location: 0), .init(color: Color(hex: 0xEAF4FF), location: 0.7),
                                     .init(color: Color(hex: 0xBFDDFF), location: 1)])
        context.fill(lens, with: .radialGradient(glass, center: CGPoint(x: 44.1, y: 43.6), startRadius: 0, endRadius: 35.7))
        context.stroke(lens, with: .color(navy), lineWidth: 6)

        var glint = Path()
        glint.addArc(center: CGPoint(x: 50, y: 52), radius: 14, startAngle: .degrees(200), endAngle: .degrees(244), clockwise: false)
        context.stroke(glint, with: .color(.white), style: StrokeStyle(lineWidth: 3.2, lineCap: .round))

        if happy {
            // Upturned eyes (∩ ∩) and a small smile between the mitts.
            for x: CGFloat in [43.5, 56.5] {
                var eye = Path()
                eye.addArc(center: CGPoint(x: x, y: 51), radius: 3.3, startAngle: .degrees(195), endAngle: .degrees(345), clockwise: false)
                context.stroke(eye, with: .color(navy), style: StrokeStyle(lineWidth: 2.6, lineCap: .round))
            }
            var smile = Path()
            smile.addArc(center: CGPoint(x: 50, y: 54.2), radius: 3.4, startAngle: .degrees(20), endAngle: .degrees(160), clockwise: false)
            context.stroke(smile, with: .color(navy), style: StrokeStyle(lineWidth: 2.2, lineCap: .round))
        } else {
            for x: CGFloat in [43.5, 56.5] {
                context.fill(Path(ellipseIn: CGRect(x: x - 3.1, y: 45.7, width: 6.2, height: 8.6)), with: .color(navy))
                context.fill(Path(ellipseIn: CGRect(x: x - 0.05, y: 47.15, width: 2.3, height: 2.3)), with: .color(.white))
            }
        }
        for x: CGFloat in [37.6, 62.4] {
            context.fill(Path(ellipseIn: CGRect(x: x - 3.6, y: 54.9, width: 7.2, height: 4.2)), with: .color(Color(hex: 0xFF8FB1, opacity: 0.8)))
        }
        context.fill(Path(roundedRect: CGRect(x: 14, y: 63.5, width: 72, height: 30), cornerRadius: 7), with: .color(Color(hex: 0x5E95E0, opacity: 0.35)))
        context.fill(Path(roundedRect: CGRect(x: 14, y: 62, width: 72, height: 30), cornerRadius: 7), with: .color(.white))
        let lights: [(CGFloat, UInt32)] = [(22, 0xFF6B6B), (28.5, 0xFFC34D), (35, 0x4CD97B)]
        for (x, hex) in lights {
            context.fill(Path(ellipseIn: CGRect(x: x - 2.3, y: 66.7, width: 4.6, height: 4.6)), with: .color(Color(hex: hex)))
        }
        context.fill(Path(roundedRect: CGRect(x: 22, y: 76, width: 36, height: 4), cornerRadius: 2), with: .color(Color(hex: 0xDCEAFF)))
        context.fill(Path(roundedRect: CGRect(x: 22, y: 83, width: 22, height: 4), cornerRadius: 2), with: .color(Color(hex: 0xDCEAFF)))
        for x: CGFloat in [40, 60] {
            let mitt = Path(ellipseIn: CGRect(x: x - 4.4, y: 59.3, width: 8.8, height: 6.6))
            context.fill(mitt, with: .color(.white))
            context.stroke(mitt, with: .color(navy), lineWidth: 2.4)
        }
    }
}

/// The hand-drawn "contextlens" lettering: one round monoline stroke, with the mascot's eyes in the "o".
struct WordmarkView: View {
    var color: Color = Lens.brandInk
    var body: some View {
        Canvas { context, size in
            let scale = size.width / 500
            context.scaleBy(x: scale, y: scale)
            context.translateBy(x: 7, y: 8)
            context.stroke(Wordmark.strokes, with: .color(color),
                           style: StrokeStyle(lineWidth: 9.5, lineCap: .round, lineJoin: .round))
            context.fill(Wordmark.eyes, with: .color(color))
        }
        .aspectRatio(500 / 77, contentMode: .fit)
        .accessibilityElement()
        .accessibilityLabel("ContextLens")
    }
}

enum Wordmark {
    static let strokes: Path = {
        var p = Path()
        func arc(_ x: CGFloat, _ y: CGFloat, _ r: CGFloat, _ from: Double, _ to: Double, clockwise: Bool) {
            p.addArc(center: CGPoint(x: x, y: y), radius: r, startAngle: .degrees(from), endAngle: .degrees(to), clockwise: clockwise)
        }
        func move(_ x: CGFloat, _ y: CGFloat) { p.move(to: CGPoint(x: x, y: y)) }
        func line(_ x: CGFloat, _ y: CGFloat) { p.addLine(to: CGPoint(x: x, y: y)) }
        // c
        move(35.32, 27.14); arc(20, 40, 20, -40, 40, clockwise: true)
        // o
        p.addEllipse(in: CGRect(x: 50, y: 20, width: 40, height: 40))
        // n
        move(105, 20); line(105, 60); move(105, 36); arc(121, 36, 16, 180, 360, clockwise: false); line(137, 60)
        // t
        move(162, 4); line(162, 48); arc(174, 48, 12, 180, 90, clockwise: true); move(152, 20); line(176, 20)
        // e
        move(191, 40); line(231, 40); arc(211, 40, 20, 0, 40, clockwise: true)
        // x
        move(246, 20); line(276, 60); move(276, 20); line(246, 60)
        // t
        move(301, 4); line(301, 48); arc(313, 48, 12, 180, 90, clockwise: true); move(291, 20); line(315, 20)
        // l
        move(330, -2); line(330, 48); arc(342, 48, 12, 180, 90, clockwise: true)
        // e
        move(357, 40); line(397, 40); arc(377, 40, 20, 0, 40, clockwise: true)
        // n
        move(412, 20); line(412, 60); move(412, 36); arc(428, 36, 16, 180, 360, clockwise: false); line(444, 60)
        // s
        move(479.53, 23.5); arc(470, 29, 11, -30, 90, clockwise: true); arc(470, 51, 11, -90, 150, clockwise: false)
        return p
    }()

    static let eyes: Path = {
        var p = Path()
        p.addEllipse(in: CGRect(x: 60.1, y: 34, width: 6.8, height: 10))
        p.addEllipse(in: CGRect(x: 73.1, y: 34, width: 6.8, height: 10))
        return p
    }()
}
