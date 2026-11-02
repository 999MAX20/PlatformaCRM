import Foundation

// Display labels for existing source values only. Never rewrites the wire value
// or validates a lifecycle command; unknown future statuses remain visible.
public enum AppointmentStatusText {
    public static func label(_ raw: String?, text: (String) -> String) -> String {
        let key: String
        switch raw {
        case "created": key = "appointmentCreated"
        case "confirmed": key = "appointmentConfirmed"
        case "cancelled": key = "appointmentCancelled"
        case "rescheduled": key = "appointmentRescheduled"
        case "completed": key = "appointmentCompleted"
        case "no_show": key = "appointmentNoShow"
        default:
            guard let raw, !raw.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return text("notAvailable") }
            return raw
        }
        return text(key)
    }
}
