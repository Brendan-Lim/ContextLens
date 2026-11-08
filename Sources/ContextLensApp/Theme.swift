import SwiftUI
import AppKit

// Design tokens for the redesigned app. Light values match the approved mockups;
// dark values keep the same roles with enough contrast on a dark canvas.
extension NSColor {
    convenience init(hex: UInt32, alpha: CGFloat = 1) {
        self.init(srgbRed: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255,
                  blue: CGFloat(hex & 0xFF) / 255, alpha: alpha)
    }
    static func lens(light: UInt32, dark: UInt32) -> NSColor {
        NSColor(name: nil) { appearance in
            appearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua ? NSColor(hex: dark) : NSColor(hex: light)
        }
    }
}

extension Color {
    init(hex: UInt32, opacity: Double = 1) {
        self.init(.sRGB, red: Double((hex >> 16) & 0xFF) / 255, green: Double((hex >> 8) & 0xFF) / 255,
                  blue: Double(hex & 0xFF) / 255, opacity: opacity)
    }
}

enum Lens {
    static let canvasNS = NSColor.lens(light: 0xF4F8FF, dark: 0x11152A)
    static let canvas = Color(nsColor: canvasNS)
    static let surface = Color(nsColor: .lens(light: 0xFFFFFF, dark: 0x1A1F38))
    static let sunken = Color(nsColor: .lens(light: 0xEEF3FB, dark: 0x232946))
    static let track = Color(nsColor: .lens(light: 0xE6EEFA, dark: 0x262D4D))
    static let ink = Color(nsColor: .lens(light: 0x17203F, dark: 0xE9ECF8))
    static let brandInk = Color(nsColor: .lens(light: 0x1E2A5A, dark: 0xE9ECF8))
    static let muted = Color(nsColor: .lens(light: 0x55618A, dark: 0xA3ABCB))
    static let line = Color(nsColor: .lens(light: 0xE1E8F5, dark: 0x2C3354))
    static let lineStrong = Color(nsColor: .lens(light: 0xCBD6EA, dark: 0x3A4266))
    static let accent = Color(nsColor: .lens(light: 0x1E2A5A, dark: 0x9CC8FF))
    static let accentHover = Color(nsColor: .lens(light: 0x2A3A7A, dark: 0xB7D7FF))
    static let onAccent = Color(nsColor: .lens(light: 0xFFFFFF, dark: 0x0E1430))
    static let selectedFill = Color(nsColor: .lens(light: 0xE6EFFC, dark: 0x27325A))
    static let shadow = Color(nsColor: .lens(light: 0x1E2A5A, dark: 0x000000)).opacity(0.12)
    static let navy = Color(hex: 0x1E2A5A)
    static let sky = Color(hex: 0xD7E9FF)
    static let record = Color(hex: 0xE0434A)
    static let mark = Color(hex: 0xE8680C)
    static let highlightMark = Color(hex: 0xC99A00)
    static let success = Color(nsColor: .lens(light: 0x1B7A3D, dark: 0x5BD08A))
    static let successFill = Color(nsColor: .lens(light: 0xE6F5EA, dark: 0x1D3A2A))
    static let warning = Color(nsColor: .lens(light: 0x8A5A00, dark: 0xF2C46B))
    static let warningFill = Color(nsColor: .lens(light: 0xFFF5DB, dark: 0x3A3020))
    static let danger = Color(nsColor: .lens(light: 0xC2312F, dark: 0xFF7B78))
    static let dangerFill = Color(nsColor: .lens(light: 0xFFF4F3, dark: 0x3A2025))
    static let markChip = Color(nsColor: .lens(light: 0xFFF0E3, dark: 0x3A2A1C))
    static let markChipText = Color(nsColor: .lens(light: 0xA44708, dark: 0xFFB27A))

    static func font(_ size: CGFloat, _ weight: Font.Weight = .regular) -> Font {
        .system(size: size, weight: weight, design: .rounded)
    }
    static func mono(_ size: CGFloat = 11.5) -> Font { .system(size: size, design: .monospaced) }
}

/// Motion values from the redesign: strong ease-out for UI, short durations, transform and opacity only.
enum Motion {
    static func ease(_ duration: Double) -> Animation { .timingCurve(0.23, 1, 0.32, 1, duration: duration) }
    static let press = ease(0.15)
    static let quick = ease(0.15)
    static let standard = ease(0.2)
    static let enter = ease(0.24)
    /// Contextual icon swaps (copy → copied, permission → granted).
    static let swap = Animation.timingCurve(0.2, 0, 0, 1, duration: 0.3)
}

extension AnyTransition {
    /// Enter with a slight scale, leave with a fade. Reduced motion keeps only the fade.
    static func lensPop(_ reduce: Bool) -> AnyTransition {
        reduce ? .opacity : .asymmetric(insertion: .opacity.combined(with: .scale(scale: 0.96)), removal: .opacity)
    }
    static func lensRise(_ reduce: Bool, distance: CGFloat = 10) -> AnyTransition {
        reduce ? .opacity : .asymmetric(insertion: .opacity.combined(with: .offset(y: distance)), removal: .opacity)
    }
}

// MARK: Buttons

struct LensButtonStyle: ButtonStyle {
    enum Kind { case primary, ghost, quiet, danger, dangerSolid, record, onDark }
    var kind: Kind = .primary
    var height: CGFloat = 36
    var fullWidth = false
    func makeBody(configuration: Configuration) -> some View {
        LensButtonBody(configuration: configuration, kind: kind, height: height, fullWidth: fullWidth)
    }
}

private struct LensButtonBody: View {
    let configuration: ButtonStyle.Configuration
    let kind: LensButtonStyle.Kind
    let height: CGFloat
    let fullWidth: Bool
    @Environment(\.isEnabled) private var enabled
    @Environment(\.accessibilityReduceMotion) private var reduce
    @State private var hover = false

    var body: some View {
        let shape = RoundedRectangle(cornerRadius: height * 0.32, style: .continuous)
        configuration.label
            .font(Lens.font(height >= 42 ? 15 : 13.5, .bold))
            .lineLimit(1)
            .padding(.horizontal, height >= 42 ? 20 : 14)
            .frame(maxWidth: fullWidth ? .infinity : nil)
            .frame(height: height)
            .foregroundStyle(foreground)
            .background(shape.fill(background))
            .overlay { if hasBorder { shape.strokeBorder(border, lineWidth: 1.5) } }
            .contentShape(shape)
            .scaleEffect(configuration.isPressed && enabled && !reduce ? 0.96 : 1)
            .opacity(enabled ? 1 : 0.45)
            .animation(Motion.press, value: configuration.isPressed)
            .animation(.easeOut(duration: 0.15), value: hover)
            .onHover { hover = $0 }
    }
    private var hasBorder: Bool { kind == .ghost || kind == .danger }
    private var border: Color { kind == .danger ? Lens.danger.opacity(0.35) : Lens.lineStrong }
    private var foreground: Color {
        switch kind {
        case .primary: return Lens.onAccent
        case .ghost, .quiet: return Lens.accent
        case .danger: return Lens.danger
        case .dangerSolid, .record, .onDark: return .white
        }
    }
    private var background: Color {
        let lit = hover && enabled
        switch kind {
        case .primary: return lit ? Lens.accentHover : Lens.accent
        case .ghost, .quiet: return lit ? Lens.sunken : .clear
        case .danger: return lit ? Lens.dangerFill : .clear
        case .dangerSolid: return Lens.danger
        case .record: return lit ? Color(hex: 0xC93339) : Lens.record
        case .onDark: return .white.opacity(lit ? 0.2 : 0.12)
        }
    }
}

extension ButtonStyle where Self == LensButtonStyle {
    static func lens(_ kind: LensButtonStyle.Kind = .primary, height: CGFloat = 36, fullWidth: Bool = false) -> LensButtonStyle {
        LensButtonStyle(kind: kind, height: height, fullWidth: fullWidth)
    }
}

/// Square icon button used in toolbars and on cards.
struct LensIconButtonStyle: ButtonStyle {
    var size: CGFloat = 32
    var raised = false
    func makeBody(configuration: Configuration) -> some View { LensIconBody(configuration: configuration, size: size, raised: raised) }
}

private struct LensIconBody: View {
    let configuration: ButtonStyle.Configuration
    let size: CGFloat
    let raised: Bool
    @Environment(\.isEnabled) private var enabled
    @Environment(\.accessibilityReduceMotion) private var reduce
    @State private var hover = false
    var body: some View {
        configuration.label
            .font(.system(size: size * 0.44, weight: .semibold))
            .frame(width: size, height: size)
            .foregroundStyle(Lens.muted)
            .background(RoundedRectangle(cornerRadius: size * 0.3, style: .continuous)
                .fill(raised ? Lens.surface : (hover && enabled ? Lens.sunken : .clear)))
            .shadow(color: raised ? Lens.shadow : .clear, radius: 3, y: 1)
            .contentShape(Rectangle())
            .scaleEffect(configuration.isPressed && enabled && !reduce ? 0.96 : 1)
            .opacity(enabled ? 1 : 0.35)
            .animation(Motion.press, value: configuration.isPressed)
            .onHover { hover = $0 }
    }
}

// MARK: Switch

struct LensSwitchStyle: ToggleStyle {
    func makeBody(configuration: Configuration) -> some View { LensSwitch(configuration: configuration) }
}

private struct LensSwitch: View {
    let configuration: ToggleStyle.Configuration
    @Environment(\.isEnabled) private var enabled
    @Environment(\.accessibilityReduceMotion) private var reduce
    var body: some View {
        Button { configuration.isOn.toggle() } label: {
            HStack(alignment: .top, spacing: 14) {
                configuration.label.frame(maxWidth: .infinity, alignment: .leading)
                Capsule()
                    .fill(configuration.isOn ? Lens.accent : Lens.lineStrong)
                    .frame(width: 40, height: 24)
                    .overlay(alignment: configuration.isOn ? .trailing : .leading) {
                        Circle().fill(.white).padding(3).shadow(color: .black.opacity(0.2), radius: 1.5, y: 1)
                    }
                    .animation(reduce ? nil : Motion.standard, value: configuration.isOn)
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .opacity(enabled ? 1 : 0.5)
        .accessibilityRepresentation { Toggle(isOn: configuration.$isOn) { configuration.label } }
    }
}

// MARK: Segmented control with a sliding indicator

struct SegmentOption<Value: Hashable>: Identifiable {
    let value: Value
    let title: String
    var icon: String? = nil
    var id: String { title }
}

struct LensSegments<Value: Hashable>: View {
    @Binding var selection: Value
    let options: [SegmentOption<Value>]
    var filled = false
    var height: CGFloat = 28
    @Namespace private var namespace
    @Environment(\.accessibilityReduceMotion) private var reduce

    var body: some View {
        HStack(spacing: 0) {
            ForEach(options) { option in
                let on = option.value == selection
                Button {
                    withAnimation(reduce ? nil : Motion.standard) { selection = option.value }
                } label: {
                    HStack(spacing: 6) {
                        if let icon = option.icon { Image(systemName: icon) }
                        Text(option.title)
                    }
                    .font(Lens.font(13, .bold))
                    .foregroundStyle(on ? (filled ? Lens.onAccent : Lens.accent) : Lens.muted)
                    .padding(.horizontal, 10)
                    .frame(maxWidth: .infinity)
                    .frame(height: height)
                    .background {
                        if on {
                            RoundedRectangle(cornerRadius: 8, style: .continuous)
                                .fill(filled ? Lens.accent : Lens.surface)
                                .shadow(color: .black.opacity(filled ? 0 : 0.1), radius: 1.5, y: 1)
                                .matchedGeometryEffect(id: "indicator", in: namespace)
                        }
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(on ? .isSelected : [])
            }
        }
        .padding(3)
        .background(RoundedRectangle(cornerRadius: 11, style: .continuous).fill(Lens.track))
    }
}

// MARK: Small shared pieces

struct SectionLabel: View {
    let text: String
    init(_ text: String) { self.text = text }
    var body: some View {
        Text(text.uppercased()).font(Lens.font(11, .bold)).tracking(0.7).foregroundStyle(Lens.muted)
    }
}

struct MarkChip: View {
    let count: Int
    var body: some View {
        Text(count == 1 ? "1 mark" : "\(count) marks")
            .font(Lens.font(11.5, .heavy))
            .padding(.horizontal, 8).frame(height: 20)
            .background(Capsule().fill(Lens.markChip))
            .foregroundStyle(Lens.markChipText)
    }
}

/// Pulsing record dot. Constant motion is dropped under Reduce Motion.
struct RecordDot: View {
    var size: CGFloat = 8
    var color: Color = Lens.record
    @Environment(\.accessibilityReduceMotion) private var reduce
    @State private var dim = false
    var body: some View {
        Circle().fill(color).frame(width: size, height: size)
            .opacity(dim ? 0.35 : 1)
            .onAppear {
                guard !reduce else { return }
                withAnimation(.easeInOut(duration: 1.1).repeatForever(autoreverses: true)) { dim = true }
            }
            .accessibilityHidden(true)
    }
}

/// Swaps two icons with scale, blur and opacity, as used for copy and permission feedback.
struct SwapIcon: View {
    let from: String
    let to: String
    let swapped: Bool
    @Environment(\.accessibilityReduceMotion) private var reduce
    var body: some View {
        ZStack {
            Image(systemName: from)
                .opacity(swapped ? 0 : 1).scaleEffect(swapped && !reduce ? 0.25 : 1).blur(radius: swapped && !reduce ? 4 : 0)
            Image(systemName: to)
                .opacity(swapped ? 1 : 0).scaleEffect(swapped || reduce ? 1 : 0.25).blur(radius: swapped || reduce ? 0 : 4)
        }
        .animation(reduce ? .easeOut(duration: 0.2) : Motion.swap, value: swapped)
    }
}

extension View {
    func lensCard(radius: CGFloat = 16) -> some View {
        background(RoundedRectangle(cornerRadius: radius, style: .continuous).fill(Lens.surface))
            .overlay(RoundedRectangle(cornerRadius: radius, style: .continuous).strokeBorder(Lens.line, lineWidth: 1))
    }
}

/// Staged entrance for first-launch content: opacity, 4 pt blur and 12 pt rise, 100 ms apart.
struct StaggerIn: ViewModifier {
    let index: Int
    @State private var shown = false
    @Environment(\.accessibilityReduceMotion) private var reduce
    func body(content: Content) -> some View {
        content
            .opacity(shown ? 1 : 0)
            .offset(y: shown || reduce ? 0 : 12)
            .blur(radius: shown || reduce ? 0 : 4)
            .onAppear {
                withAnimation(.easeOut(duration: 0.3).delay(Double(index) * 0.1)) { shown = true }
            }
    }
}

extension View {
    func staggerIn(_ index: Int) -> some View { modifier(StaggerIn(index: index)) }
}

func formatTimestamp(_ ms: Int) -> String {
    String(format: "%02d:%02d", ms / 60000, (ms / 1000) % 60)
}
