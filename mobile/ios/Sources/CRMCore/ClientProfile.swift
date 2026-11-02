import Foundation

public struct ClientVisit: Decodable, Sendable {
    public let appointment: Appointment
    public let clientID: Int
    private enum CodingKeys: String, CodingKey { case clientID = "client_id" }
    public init(from decoder: any Decoder) throws { appointment = try Appointment(from: decoder); clientID = try decoder.container(keyedBy: CodingKeys.self).decode(Int.self, forKey: .clientID) }
}
public struct ClientProfile: Decodable, Sendable {
    public struct Fields: Decodable, Sendable { public let notes: String? }
    public struct Related: Decodable, Sendable {
        public let appointments: [ClientVisit]
        public let tasks: [WorkTask]?
        public let conversations: [InboxConversation]?
    }
    public struct Budget: Decodable, Sendable { public let max_related_per_section: Int }
    public let editReadFields: ClientEditReadFields
    private enum CodingKeys: String,CodingKey {case business,client,details,related,payload_budget}
    public init(from decoder: any Decoder) throws {
        let c=try decoder.container(keyedBy:CodingKeys.self)
        business=try c.decode(Int.self,forKey:.business);client=try c.decode(ClientContact.self,forKey:.client);details=try c.decode(Fields.self,forKey:.details);related=try c.decode(Related.self,forKey:.related);payload_budget=try c.decode(Budget.self,forKey:.payload_budget)
        editReadFields=try c.decode(ClientEditReadFields.self,forKey:.client)
    }
    public let business: Int
    public let client: ClientContact
    public let details: Fields
    public let related: Related
    public let payload_budget: Budget
    public var historyCapped: Bool { related.appointments.count == payload_budget.max_related_per_section }
    public func valid(for scope: Int, id: Int) -> Bool {
        scope > 0 && id > 0 && business == scope && client.id == id && payload_budget.max_related_per_section > 0 && related.appointments.count <= payload_budget.max_related_per_section &&
        Set(related.appointments.map { $0.appointment.id }).count == related.appointments.count && related.appointments.allSatisfy {
            guard $0.clientID == id, $0.appointment.id > 0, let start = $0.appointment.start, let end = $0.appointment.end else { return false }; return end > start
        }
    }
}
