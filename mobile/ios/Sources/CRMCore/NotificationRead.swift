import Foundation

public struct CRMNotification: Decodable, Identifiable, Equatable, Sendable {
    public let id: Int
    public let text: String?, category: String?, priority: String?, status: String?, channel: String?
    public let send_at: String?, read_at: String?, action_url: String?
    public let appointment_id: Int?
    public let readMarkerPresent: Bool
    private enum CodingKeys: String, CodingKey { case id, text, category, priority, status, channel, send_at, read_at, action_url, appointment_id }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(Int.self, forKey: .id)
        text = try c.decodeIfPresent(String.self, forKey: .text); category = try c.decodeIfPresent(String.self, forKey: .category)
        priority = try c.decodeIfPresent(String.self, forKey: .priority); status = try c.decodeIfPresent(String.self, forKey: .status)
        channel = try c.decodeIfPresent(String.self, forKey: .channel); send_at = try c.decodeIfPresent(String.self, forKey: .send_at)
        readMarkerPresent = c.contains(.read_at); read_at = try c.decodeIfPresent(String.self, forKey: .read_at)
        action_url = try c.decodeIfPresent(String.self, forKey: .action_url); appointment_id = try c.decodeIfPresent(Int.self, forKey: .appointment_id)
    }
    public var unread: Bool { readMarkerPresent && read_at == nil }
    public var appointmentTarget: Int? {
        guard let id = appointment_id, id > 0, let action_url else { return nil }
        return ["/app/calendar?appointment=\(id)", "/app/calendar/\(id)", "/app/calendar/\(id)/"].contains(action_url) ? id : nil
    }
    public var valid: Bool { id > 0 && [send_at, read_at].compactMap { $0 }.allSatisfy { Appointment.instant($0) != nil } }
}
public struct NotificationPage: Decodable, Sendable {
    public struct Summary: Decodable, Sendable { public let total: Int }
    public let business: Int
    public let items: [CRMNotification]
    public let summary: Summary
    public func valid(for scope: Int) -> Bool { scope > 0 && business == scope && summary.total >= items.count && items.allSatisfy(\.valid) && Set(items.map(\.id)).count == items.count }
}
