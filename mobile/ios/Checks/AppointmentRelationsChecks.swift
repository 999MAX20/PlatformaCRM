import Foundation
import CRMCore

func runAppointmentRelationsChecks(directory: URL) async throws -> Int {
    var count = 0
    func expect(_ value: Bool,_ message: String) throws { guard value else { throw CheckFailure(message:message) }; count += 1 }
    func variant(_ change: (inout [String:Any])->Void) throws -> AppointmentDetail {
        var j = try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-101-501.json"))) as! [String:Any]
        change(&j); return try JSONDecoder().decode(AppointmentDetail.self,from:JSONSerialization.data(withJSONObject:j))
    }
    let source = RecordingTransport(FixtureTransport(directory:directory)); let repo = APIReadRepository(transport:source)
    let parent = try await repo.appointment(business:101,id:501)
    try expect(parent.appointment.client_id == 7001 && parent.details.client?.id == 7001 && parent.linkedClientID == 7001, "Client reference not agreed by both explicit IDs")
    try expect(parent.providedTasks?.map(\.id) == [1301,1302,1303,1304,1305] && parent.relatedTaskWindowCapped, "Provided related window/order changed")
    let conflict = try variant { j in var fields = j["details"] as! [String:Any]; fields["client"] = ["id":7002]; j["details"] = fields }
    try expect(conflict.linkedClientID == nil && conflict.clientLinkAmbiguous && conflict.providedTasks?.count == 5, "Client conflict ignored or blocked independent Tasks")
    let missing = try variant { j in var fields = j["details"] as! [String:Any]; fields["client"] = NSNull(); j["details"] = fields }
    try expect(missing.linkedClientID == nil && missing.clientLinkAmbiguous, "Missing nested reference guessed from outer Client ID")
    let noClient = try variant { j in var a = j["appointment"] as! [String:Any]; a["client_id"] = NSNull(); a["lead_id"] = 7001; j["appointment"] = a; var fields = j["details"] as! [String:Any]; fields["client"] = ["id":NSNull(),"title":"same title"]; j["details"] = fields }
    try expect(noClient.linkedClientID == nil && !noClient.clientLinkAmbiguous, "Lead/name rebound as Client")
    let absent = try variant { $0.removeValue(forKey:"related"); $0.removeValue(forKey:"payload_budget") }
    try expect(absent.providedTasks == nil, "Unknown related window became known empty")
    let budget = try variant { $0["payload_budget"] = ["max_related_per_section":0] }
    try expect(budget.providedTasks == nil && budget.linkedClientID == 7001, "Bad Task window granted targets or blocked Client")
    let tooSmall = try variant { $0["payload_budget"] = ["max_related_per_section":4] }
    try expect(tooSmall.providedTasks == nil, "Related window overrun accepted")
    let duplicate = try variant { j in var related = j["related"] as! [String:Any]; let rows = related["tasks"] as! [[String:Any]]; related["tasks"] = [rows[0],rows[0]]; j["related"] = related }
    try expect(duplicate.providedTasks == nil, "Duplicate provided Task IDs accepted")
    let empty = try await repo.appointment(business:101,id:502)
    try expect(empty.providedTasks?.isEmpty == true && !empty.relatedTaskWindowCapped, "Empty provided window changed into unavailable/full history")
    let client = try await repo.clientProfile(business:101,id:parent.linkedClientID!)
    try expect(client.valid(for:101,id:7001) && client.client.email == "appointment-7001@example.invalid", "Client target did not independently load its own contacts")
    for task in parent.providedTasks! {
        let result = try await repo.taskDetails(business:101,id:task.id)
        try expect(result.valid(for:101,id:task.id) && result.details.appointment_id == 501, "Task independent identity/Business/backlink missing")
    }
    let requests = await source.requests
    try expect(requests.contains(ReadRequest(path:"/api/mobile/v1/clients/7001/",query:["business":"101"])), "Client target invented lookup/route")
    try expect(requests.filter { $0.path.hasPrefix("/api/mobile/v1/tasks/") }.map(\.path) == (1301...1305).map { "/api/mobile/v1/tasks/\($0)/" }, "Related Tasks not read by explicit provided IDs")
    let other = try await repo.appointment(business:202,id:601); let otherClient = try await repo.clientProfile(business:202,id:other.linkedClientID!)
    try expect(otherClient.valid(for:202,id:7003) && !otherClient.valid(for:101,id:7003), "Client target scopes were joined")
    return count
}
