import Foundation

// Explicit test/debug adapter. Never used as an automatic fallback for live errors.
public struct FixtureTransport: ReadTransport {
    private let directory: URL
    private let taskQueries: Bool
    public init(directory: URL,taskQueries: Bool=false) { self.directory = directory;self.taskQueries=taskQueries }
    public func get(_ request: ReadRequest) async throws -> ReadResponse {
        let file: String
        if request.query.isEmpty,let id=request.path.split(separator:"/").last.flatMap({Int($0)}),id>0,let kind=AppointmentReferenceKind.allCases.first(where:{$0.request(id:id)?.path==request.path}) {file="\(kind.rawValue)-reference-\(id)"}
        else if request.path == "/api/mobile/v1/bootstrap/" { file = "bootstrap" }
        else if request.path == "/api/mobile/v1/actions/", let business = request.query["business"], ["101", "202"].contains(business) { file = "actions-\(business)" }
        else if request.path == "/api/mobile/v1/home/", let business = request.query["business"], ["101", "202"].contains(business) { file = "home-\(business)" }
        else if request.path == "/api/mobile/v1/today/", let business = request.query["business"], ["101", "202"].contains(business), request.query["date"] == "2026-10-28" { file = "today-\(business)" }
        else if request.path == "/api/mobile/v1/notifications/", let business = request.query["business"], ["101", "202"].contains(business) { file = "notifications-\(business)" }
        else if request.path == "/api/mobile/v1/tasks/", let business = request.query["business"], ["101", "202"].contains(business) {
            if taskQueries {return try FixtureTaskQueries.response(Data(contentsOf:directory.appendingPathComponent("task-query-source-\(business).json")),business:Int(business)!,query:request.query)}
            guard request.query["status"]==nil,request.query["due"]==nil else {return ReadResponse(status:400,data:Data())}
            file = "tasks-\(business)"
        }
        else if request.path.hasPrefix("/api/mobile/v1/tasks/"), let business = request.query["business"], let businessID = Int(business), businessID > 0, let id = request.path.split(separator: "/").last, let parsedID = Int(id), parsedID > 0 {
            if taskQueries,[101,202].contains(businessID) {return try FixtureTaskQueries.response(Data(contentsOf:directory.appendingPathComponent("task-query-source-\(business).json")),business:businessID,query:request.query,id:parsedID)}
            file = "task-\(businessID)-\(parsedID)"
        }
        else if request.path == "/api/mobile/v1/inbox/", let business = request.query["business"], ["101", "202"].contains(business) { file = "inbox-\(business)" }
        else if request.path.hasPrefix("/api/mobile/v1/inbox/"), let business = request.query["business"], let businessID = Int(business), businessID > 0, let id = request.path.split(separator: "/").last, let parsedID = Int(id), parsedID > 0 { file = "inbox-\(businessID)-\(parsedID)" }
        else if request.path == "/api/mobile/v1/clients/", let business = request.query["business"], ["101", "202"].contains(business) {
            if let search=request.query["search"],let id=Int(business) {
                let data=try Data(contentsOf:directory.appendingPathComponent("client-search-catalogue-\(business).json"))
                return try FixtureClientSearch.list(data,business:id,search:search)
            }
            file = "clients-\(business)"
        }
        else if request.path.hasPrefix("/api/mobile/v1/clients/"), let business = request.query["business"], let businessID = Int(business), businessID > 0, let id = request.path.split(separator: "/").last, let parsedID = Int(id), parsedID > 0 {
            if FixtureClientSearch.isCatalogueID(parsedID),[101,202].contains(businessID) {
                return try FixtureClientSearch.profile(Data(contentsOf:directory.appendingPathComponent("client-search-catalogue-\(businessID).json")),business:businessID,id:parsedID)
            }
            file = "client-\(businessID)-\(parsedID)"
        }
        else if request.path == "/api/mobile/v1/appointments/", let business = request.query["business"] {
            guard ["101", "202"].contains(business), let day = request.query["date"], Day.isValid(day) else { return ReadResponse(status: 404, data: Data()) }
            if day == "2026-10-29" && business == "101" {
                return ReadResponse(status: 200, data: try Data(contentsOf: directory.appendingPathComponent("appointments-agenda-edge-101.json")))
            }
            if day != "2026-10-28" && day != "2026-10-27" {
                let empty: [String: Any] = ["business": Int(business)!, "date": day, "items": [], "summary": ["total": 0]]
                return ReadResponse(status: 200, data: try JSONSerialization.data(withJSONObject: empty))
            }
            file = day == "2026-10-27" ? "appointments-history-\(business)" : "appointments-\(business)"
        } else if request.path.hasPrefix("/api/mobile/v1/appointments/"), let businessValue = request.query["business"], let businessID = Int(businessValue), businessID > 0, let id = request.path.split(separator: "/").last, let parsedID = Int(id), parsedID > 0 {
            file = "appointment-\(businessID)-\(parsedID)"
        } else { return ReadResponse(status: 404, data: Data()) }
        let url = directory.appendingPathComponent(file).appendingPathExtension("json")
        guard FileManager.default.fileExists(atPath: url.path) else { return ReadResponse(status: 404, data: Data()) }
        return ReadResponse(status: 200, data: try Data(contentsOf: url))
    }
}
