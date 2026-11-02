import Foundation
import CRMCore

func runBootstrapChecks(directory: URL) throws -> Int {
    let data = try Data(contentsOf: directory.appendingPathComponent("bootstrap.json"))
    let bootstrap = try JSONDecoder().decode(Bootstrap.self, from: data)
    var session = AgendaSession(); try session.install(bootstrap)
    let scope = try session.begin(businessID: 101, day: "2026-10-28")
    let page = try JSONDecoder().decode(AppointmentList.self, from: Data(contentsOf: directory.appendingPathComponent("appointments-101.json")))
    try session.receive(page, for: scope)
    var count = 0
    for timezone in ["UTC", "Invalid/Zone"] {
        var json = try JSONSerialization.jsonObject(with: data) as! [String: Any]
        var active = json["active_business"] as! [String: Any]; active["timezone"] = timezone; json["active_business"] = active
        let inconsistent = try JSONDecoder().decode(Bootstrap.self, from: JSONSerialization.data(withJSONObject: json))
        do { try session.install(inconsistent); throw CheckFailure(message: "Inconsistent active Business timezone accepted") }
        catch let error as ReadFailure {
            guard error == .invalidPayload else { throw CheckFailure(message: "Wrong bootstrap consistency failure") }; count += 1
        }
        guard session.selection == scope, session.items.map(\.id) == [501, 502] else { throw CheckFailure(message: "Rejected bootstrap erased current context") }
        count += 1
    }
    return count
}
