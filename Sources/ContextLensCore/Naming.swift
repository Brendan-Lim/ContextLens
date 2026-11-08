import Foundation

/// Readable default names for captured states. People and agents both see these in context.md,
/// so a name says what happened ("Clicked “Save”") instead of a counter.
public enum StateNamer {
    public static func name(sequence: Int, reason: String, windowTitle: String?, previousTitle: String?, clickedLabel: String?) -> String {
        if let label = tidy(clickedLabel, limit: 32) { return "Clicked “\(label)”" }
        let title = tidy(windowTitle, limit: 48)
        if let title, reason == "initial" || title != tidy(previousTitle, limit: 48) { return title }
        switch reason {
        case "initial": return "Start"
        case "manual": return "Snapshot \(sequence)"
        case "scroll": return "Scrolled"
        case "stop_flush": return "Last state"
        default: return "State \(sequence)"
        }
    }
    /// Collapses whitespace and shortens long labels with an ellipsis.
    static func tidy(_ text: String?, limit: Int) -> String? {
        guard let text else { return nil }
        let words = text.split(whereSeparator: { $0.isWhitespace || $0.isNewline })
        let joined = words.joined(separator: " ")
        guard !joined.isEmpty else { return nil }
        guard joined.count > limit else { return joined }
        return String(joined.prefix(limit - 1)).trimmingCharacters(in: .whitespaces) + "…"
    }
}

/// Folder names for exported packages: `contextlens-checkout-page-2026-11-07-0941`.
public enum PackageName {
    public static func folder(for session: Session, at date: Date = Date(), timeZone: TimeZone = .current) -> String {
        let source = session.frames.first?.windowTitle ?? session.frames.first?.applicationName
        let slug = slug(source) ?? slug(session.frames.first?.applicationName) ?? "session"
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX"); formatter.timeZone = timeZone
        formatter.dateFormat = "yyyy-MM-dd-HHmm"
        return "contextlens-\(slug)-\(formatter.string(from: date))"
    }
    /// Returns `parent/name`, adding `-2`, `-3`… when that folder already exists.
    public static func unique(_ name: String, in parent: URL, fileManager: FileManager = .default) -> URL {
        var candidate = parent.appendingPathComponent(name), n = 2
        while fileManager.fileExists(atPath: candidate.path) { candidate = parent.appendingPathComponent("\(name)-\(n)"); n += 1 }
        return candidate
    }
    /// Lowercase ASCII words joined by hyphens, at most four words and 32 characters.
    static func slug(_ text: String?) -> String? {
        guard let text else { return nil }
        let folded = text.folding(options: [.diacriticInsensitive, .caseInsensitive, .widthInsensitive], locale: Locale(identifier: "en_US_POSIX")).lowercased()
        let words = folded.split(whereSeparator: { !(("a"..."z").contains($0) || ("0"..."9").contains($0)) }).prefix(4)
        var slug = ""
        for word in words {
            let next = slug.isEmpty ? String(word) : slug + "-" + word
            if next.count > 32 { break }
            slug = next
        }
        if slug.isEmpty, let first = words.first { slug = String(first.prefix(32)) }
        return slug.isEmpty ? nil : slug
    }
}
