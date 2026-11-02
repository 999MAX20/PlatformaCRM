import Foundation

public enum AgendaMode: String, CaseIterable, Hashable, Sendable { case list, calendar }
public enum AgendaTimeIssue: String, Sendable {
    case unknown = "agendaUnknownTime", invalidRange = "agendaInvalidRange", otherDay = "agendaOtherDay", sourceDay = "agendaSourceDayMismatch"
}
public struct AgendaDayRow: Identifiable, Sendable {
    public let appointment: Appointment
    public let issue: AgendaTimeIssue?
    public var id: Int { appointment.id }
}
// Display grouping only; retains every same-scope row and never invents slots/duration.
public struct AgendaDayDisplay: Sendable {
    public let sourceRows: [AgendaDayRow]
    public var uncertain: [AgendaDayRow] { sourceRows.filter { $0.issue != nil } }
    public var scheduled: [AgendaDayRow] {
        sourceRows.filter { $0.issue == nil }.sorted {
            guard let left = $0.appointment.start, let right = $1.appointment.start else { return false }
            return left == right ? $0.id < $1.id : left < right
        }
    }
    public init(items: [Appointment], day: String, responseDay: String?, timezone: String) {
        sourceRows = items.map { item in
            let issue: AgendaTimeIssue?
            if responseDay != day { issue = .sourceDay }
            else if !Day.isValid(day) || TimeZone(identifier: timezone) == nil { issue = .unknown }
            else if let start = item.start, let end = item.end {
                if end <= start { issue = .invalidRange }
                else if Day.string(start, timezone: timezone) != day { issue = .otherDay }
                else { issue = nil }
            } else { issue = .unknown }
            return AgendaDayRow(appointment: item, issue: issue)
        }
    }
}
