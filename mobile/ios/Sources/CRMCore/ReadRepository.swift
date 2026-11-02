import Foundation

public struct ReadRequest: Equatable, Sendable {
    public let path: String
    public let query: [String: String]
    public init(path: String, query: [String: String] = [:]) { self.path = path; self.query = query }
}
public struct ReadResponse: Sendable {
    public let status: Int
    public let data: Data
    public init(status: Int, data: Data) { self.status = status; self.data = data }
}
public protocol ReadTransport: Sendable { func get(_ request: ReadRequest) async throws -> ReadResponse }
public protocol AgendaRepository: Sendable {
    func bootstrap() async throws -> Bootstrap
    func appointments(business: Int, day: String) async throws -> AppointmentList
    func appointment(business: Int, id: Int) async throws -> AppointmentDetail
}
public protocol ClientRepository: Sendable { func clients(business: Int) async throws -> ClientList }
public protocol ClientSearchRepository: ClientProfileRepository {
    func searchClients(business: Int,search: String) async throws -> ClientList
}
public protocol InboxRepository: Sendable {
    func inbox(business: Int) async throws -> InboxList
    func thread(business: Int, id: Int) async throws -> InboxThread
}
public protocol TaskReadRepository: Sendable {
    func tasks(business: Int) async throws -> TaskPage
    func taskDetails(business: Int, id: Int) async throws -> TaskDetails
}
public protocol NotificationRepository: Sendable {
    func notifications(business: Int) async throws -> NotificationPage
    func appointment(business: Int, id: Int) async throws -> AppointmentDetail
}
public protocol ClientProfileRepository: Sendable { func clientProfile(business: Int, id: Int) async throws -> ClientProfile }
public protocol InboxClientRepository: InboxRepository, ClientProfileRepository {}
public protocol ClientWorkRepository: Sendable {
    func taskDetails(business: Int, id: Int) async throws -> TaskDetails
    func thread(business: Int, id: Int) async throws -> InboxThread
    func appointment(business: Int, id: Int) async throws -> AppointmentDetail
}
public protocol HomeTodayRepository: Sendable {
    func home(business: Int) async throws -> HomeSummary
    func today(business: Int, day: String) async throws -> TodaySummary
}
public protocol AttentionRepository: Sendable {
    func actions(business: Int) async throws -> AttentionPage
    func taskDetails(business: Int, id: Int) async throws -> TaskDetails
    func thread(business: Int, id: Int) async throws -> InboxThread
    func appointment(business: Int, id: Int) async throws -> AppointmentDetail
}
public protocol AppointmentRelatedRepository: ClientProfileRepository {
    func taskDetails(business: Int, id: Int) async throws -> TaskDetails
}
public struct APIReadRepository: AgendaRepository, ClientRepository, ClientSearchRepository, InboxRepository, InboxClientRepository, TaskQueryRepository, NotificationRepository, ClientProfileRepository, ClientWorkRepository, HomeTodayRepository, AttentionRepository, AppointmentRelatedRepository {
    private let transport: any ReadTransport
    public init(transport: any ReadTransport) { self.transport = transport }
    private func decode<T: Decodable>(_ type: T.Type, request: ReadRequest) async throws -> T {
        let response = try await transport.get(request)
        switch response.status {
        case 200: do {
            let decoder = type == TaskDetails.self ? TaskDetails.sourceDecoder(response.data):JSONDecoder()
            // Both original relation projections consume the same exact GET bytes; no extra read or fallback.
            return try decoder.decode(type,from:response.data)
        } catch { throw ReadFailure.invalidPayload }
        case 403: throw ReadFailure.denied
        case 404: throw ReadFailure.notFound
        default: throw ReadFailure.unavailable
        }
    }
    public func actions(business: Int) async throws -> AttentionPage {
        guard business > 0 else { throw ReadFailure.invalidContext }
        return try await decode(AttentionPage.self, request: ReadRequest(path: "/api/mobile/v1/actions/", query: ["business": String(business), "limit": "20"]))
    }
    public func home(business: Int) async throws -> HomeSummary {
        guard business > 0 else { throw ReadFailure.invalidContext }
        return try await decode(HomeSummary.self, request: ReadRequest(path: "/api/mobile/v1/home/", query: ["business": String(business), "limit": "5"]))
    }
    public func today(business: Int, day: String) async throws -> TodaySummary {
        guard business > 0, Day.isValid(day) else { throw ReadFailure.invalidContext }
        return try await decode(TodaySummary.self, request: ReadRequest(path: "/api/mobile/v1/today/", query: ["business": String(business), "date": day, "limit": "20"]))
    }
    public func bootstrap() async throws -> Bootstrap {
        try await decode(Bootstrap.self, request: ReadRequest(path: "/api/mobile/v1/bootstrap/"))
    }
    public func clientProfile(business: Int, id: Int) async throws -> ClientProfile {
        guard business > 0, id > 0 else { throw ReadFailure.invalidContext }
        return try await decode(ClientProfile.self, request: ReadRequest(path: "/api/mobile/v1/clients/\(id)/", query: ["business": String(business)]))
    }
    public func notifications(business: Int) async throws -> NotificationPage {
        guard business > 0 else { throw ReadFailure.invalidContext }
        return try await decode(NotificationPage.self, request: ReadRequest(path: "/api/mobile/v1/notifications/", query: ["business": String(business), "limit": "50"]))
    }
    public func tasks(business: Int) async throws -> TaskPage {
        try await tasks(business:business,filter:TaskQueryFilter())
    }
    public func tasks(business: Int,filter: TaskQueryFilter) async throws -> TaskPage {
        guard business > 0 else { throw ReadFailure.invalidContext }
        return try await decode(TaskPage.self, request:filter.request(business:business))
    }
    public func taskDetails(business: Int, id: Int) async throws -> TaskDetails {
        guard business > 0, id > 0 else { throw ReadFailure.invalidContext }
        return try await decode(TaskDetails.self, request: ReadRequest(path: "/api/mobile/v1/tasks/\(id)/", query: ["business": String(business)]))
    }
    public func inbox(business: Int) async throws -> InboxList {
        guard business > 0 else { throw ReadFailure.invalidContext }
        return try await decode(InboxList.self, request: ReadRequest(path: "/api/mobile/v1/inbox/", query: ["business": String(business), "limit": "50"]))
    }
    public func thread(business: Int, id: Int) async throws -> InboxThread {
        guard business > 0, id > 0 else { throw ReadFailure.invalidContext }
        return try await decode(InboxThread.self, request: ReadRequest(path: "/api/mobile/v1/inbox/\(id)/", query: ["business": String(business), "limit": "30"]))
    }
    public func searchClients(business: Int,search: String) async throws -> ClientList {
        guard business>0 else {throw ReadFailure.invalidContext}
        return try await decode(ClientList.self,request:ReadRequest(path:"/api/mobile/v1/clients/",query:["business":String(business),"limit":"50","search":SourceTextTrim.pythonStrip(search)]))
    }
    public func clients(business: Int) async throws -> ClientList {
        guard business > 0 else { throw ReadFailure.invalidContext }
        return try await decode(ClientList.self, request: ReadRequest(path: "/api/mobile/v1/clients/", query: ["business": String(business), "limit": "50"]))
    }
    public func appointments(business: Int, day: String) async throws -> AppointmentList {
        guard business > 0, Day.isValid(day) else { throw ReadFailure.invalidContext }
        return try await decode(AppointmentList.self, request: ReadRequest(path: "/api/mobile/v1/appointments/", query: ["business": String(business), "date": day, "limit": "50"]))
    }
    public func appointment(business: Int, id: Int) async throws -> AppointmentDetail {
        guard business > 0, id > 0 else { throw ReadFailure.invalidContext }
        return try await decode(AppointmentDetail.self, request: ReadRequest(path: "/api/mobile/v1/appointments/\(id)/", query: ["business": String(business)]))
    }
}
