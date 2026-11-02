import Foundation
import CRMCore

enum AppCopy {
    private static let copy: UICopy? = {
        guard let url = Bundle.main.resourceURL?.appendingPathComponent("contracts/ui-copy.json"),
              let data = try? Data(contentsOf: url) else { return nil }
        return try? UICopy(data: data, preferredLanguage: Locale.preferredLanguages.first ?? "en")
    }()
    static var language: String { copy?.language ?? "en" }
    static func text(_ key: String) -> String { copy?.text(key) ?? key }
    static func error(_ failure: ReadFailure) -> String {
        switch failure {
        case .denied: text("denied")
        case .notFound: text("notAvailable")
        default: text("unavailable")
        }
    }
}

// Presentation only; the source instant and Business context remain unchanged.
enum AppointmentDate {
    static func format(startAt: String?, timezone: String?, language: String) -> String? {
        guard let timezone, let zone = TimeZone(identifier: timezone),
              let instant = Appointment.instant(startAt) else { return nil }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: language)
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.timeZone = zone
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: instant)
    }
}

// Full endpoint dates and numeric offsets keep overnight/DST intervals unambiguous.
enum AgendaEndpoint {
    static func format(_ raw: String?, timezone: String?, language: String) -> String? {
        guard let timezone, let zone = TimeZone(identifier: timezone), let instant = Appointment.instant(raw),
              let label = AppointmentDate.format(startAt: raw, timezone: timezone, language: language) else { return nil }
        let offset = zone.secondsFromGMT(for: instant), absolute = abs(offset)
        var suffix = String(format: "UTC%@%02d:%02d", offset < 0 ? "-" : "+", absolute / 3600, (absolute % 3600) / 60)
        if absolute % 60 != 0 { suffix += String(format: ":%02d", absolute % 60) }
        return label + " (" + suffix + ")"
    }
}
