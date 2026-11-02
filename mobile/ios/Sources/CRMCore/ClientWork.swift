import Foundation

// Local read selection, not a wire DTO or an access grant.
public struct ClientReadSelection: Equatable, Sendable {
    public let business: Int
    public let id: Int
    public let revision: Int
    public init(business: Int, id: Int, revision: Int) { self.business = business; self.id = id; self.revision = revision }
}
public enum ClientWorkTarget: Equatable, Sendable { case task(Int), conversation(Int), appointment(Int) }
extension ClientProfile {
    public var providedAppointments: [Appointment]? {
        guard (1...5).contains(payload_budget.max_related_per_section), related.appointments.count <= payload_budget.max_related_per_section,
              Set(related.appointments.map { $0.appointment.id }).count == related.appointments.count,
              related.appointments.allSatisfy({ $0.clientID == client.id && $0.appointment.id > 0 }) else { return nil }
        return related.appointments.map(\.appointment)
    }
    public var providedTasks: [WorkTask]? {
        guard (1...5).contains(payload_budget.max_related_per_section), let rows = related.tasks,
              rows.count <= payload_budget.max_related_per_section, Set(rows.map(\.id)).count == rows.count,
              rows.allSatisfy({ $0.valid && $0.client_id == client.id }) else { return nil }
        return rows
    }
    public var providedConversations: [InboxConversation]? {
        guard (1...5).contains(payload_budget.max_related_per_section), let rows = related.conversations,
              rows.count <= payload_budget.max_related_per_section, Set(rows.map(\.id)).count == rows.count,
              rows.allSatisfy({ $0.id > 0 && $0.unread_count >= 0 }) else { return nil }
        return rows
    }
}
