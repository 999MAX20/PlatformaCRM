import Foundation

public struct Business: Codable, Identifiable, Equatable, Sendable {
    public let id: Int
    public let name: String
    public let timezone: String
}
public struct Bootstrap: Decodable, Sendable {
    public let active_business: Business
    public let businesses: [Business]
}
public struct Appointment: Codable, Identifiable, Equatable, Sendable {
    public let id: Int
    public let title: String?
    public let status: String
    public let start_at: String?
    public let end_at: String?
    public let client_id: Int?
    public var start: Date? { Self.instant(start_at) }
    public var end: Date? { Self.instant(end_at) }
    public static func instant(_ value: String?) -> Date? {
        guard let value else { return nil }
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.date(from: value) ?? ISO8601DateFormatter().date(from: value)
    }
}
public struct AppointmentList: Codable, Sendable {
    public struct Summary: Codable, Sendable { public let total: Int }
    public let business: Int
    public let date: String
    public let items: [Appointment]
    public let summary: Summary
    public var isPartial: Bool { summary.total > items.count }
}
public struct AppointmentDetail: Codable, Sendable {
    public struct Fields: Codable, Sendable {
        public struct Named: Codable, Sendable { public let id: Int?; public let name: String? }
        public struct ClientReference: Codable, Sendable { public let id: Int? }
        public let client: ClientReference?
        public let notes: String?
        public let service: Named?
        public let resource: Named?
    }
    public let business: Int
    public let appointment: Appointment
    public struct Related: Codable, Sendable { public let tasks: [WorkTask]? }
    public struct Budget: Codable, Sendable { public let max_related_per_section: Int? }
    public let details: Fields
    public let related: Related?
    public let payload_budget: Budget?
}
public enum ReadFailure: Error, Equatable, Sendable {
    case denied, notFound, unavailable, invalidPayload, invalidContext
}
public struct Selection: Equatable, Sendable {
    public let business: Business
    public let day: String
    public let revision: Int
}
public struct DetailSelection: Equatable, Sendable {
    public let scope: Selection
    public let id: Int
    public let revision: Int
}
public enum Day {
    public static func string(_ date: Date, timezone: String) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(identifier: timezone) ?? TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: date)
    }
    public static func isValid(_ value: String) -> Bool {
        let f = DateFormatter(); f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(secondsFromGMT: 0); f.dateFormat = "yyyy-MM-dd"; f.isLenient = false
        guard let date = f.date(from: value) else { return false }
        return f.string(from: date) == value
    }
}
