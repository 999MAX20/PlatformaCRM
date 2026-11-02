import Foundation
import CRMCore

func runClientWorkChecks(directory: URL) async throws -> Int {
    var count = 0
    func expect(_ value: Bool, _ message: String) throws { guard value else { throw CheckFailure(message: message) }; count += 1 }
    func profile(_ change: (inout [String:Any]) -> Void) throws -> ClientProfile {
        var object = try JSONSerialization.jsonObject(with: Data(contentsOf: directory.appendingPathComponent("client-101-701.json"))) as! [String:Any]
        change(&object)
        return try JSONDecoder().decode(ClientProfile.self, from: JSONSerialization.data(withJSONObject: object))
    }
    func related(_ key: String, _ value: Any?) throws -> ClientProfile {
        try profile { object in var rows = object["related"] as! [String:Any]; rows[key] = value; object["related"] = rows }
    }
    let repo = APIReadRepository(transport: FixtureTransport(directory: directory))
    let p = try await repo.clientProfile(business: 101, id: 701)
    try expect(p.providedTasks?.map(\.id) == Array(1401...1405) && p.providedConversations?.map(\.id) == [931,932], "Client windows lost source order or identity")
    try expect(p.providedAppointments?.map(\.id) == [5101], "Provided historical Appointment window lost identity")
    try expect(try profile { $0["payload_budget"] = ["max_related_per_section":6] }.providedAppointments == nil, "Unsupported historical window accepted")
    try expect(try related("tasks", nil).providedTasks == nil, "Missing task window became an empty success")
    try expect(try related("tasks", NSNull()).providedTasks == nil, "Null task window became an empty success")
    try expect(try related("conversations", nil).providedConversations == nil, "Missing thread window became an empty success")
    try expect(try related("conversations", []).providedConversations?.isEmpty == true, "Provided empty thread window unavailable")
    let data = try JSONSerialization.jsonObject(with: Data(contentsOf: directory.appendingPathComponent("client-101-701.json"))) as! [String:Any]
    let rows = data["related"] as! [String:Any]
    let tasks = rows["tasks"] as! [[String:Any]], threads = rows["conversations"] as! [[String:Any]]
    for bad in [0,4,6] {
        let variant = try profile { $0["payload_budget"] = ["max_related_per_section":bad] }
        try expect(variant.providedTasks == nil, "Unsupported/overflowing task window accepted")
    }
    try expect(try related("tasks", [tasks[0],tasks[0]]).providedTasks == nil, "Duplicate task IDs accepted")
    var wrong = tasks[0]; wrong["client_id"] = 702
    let detached = try related("tasks", [wrong])
    try expect(detached.valid(for: 101,id: 701) && detached.providedTasks == nil && detached.providedConversations != nil, "Invalid task relation broke independent parent/thread reads")
    wrong["client_id"] = NSNull()
    try expect(try related("tasks", [wrong]).providedTasks == nil, "Unknown task Client was inferred")
    try expect(try related("conversations", [threads[0],threads[0]]).providedConversations == nil, "Duplicate thread IDs accepted")
    var badThread = threads[0]; badThread["unread_count"] = -1
    try expect(try related("conversations", [badThread]).providedConversations == nil, "Negative unread count accepted")
    for (business,id) in [(101,701),(202,801)] {
        let parent = try await repo.clientProfile(business: business,id: id)
        for row in parent.providedTasks! {
            let target = try await repo.taskDetails(business: business,id: row.id)
            try expect(target.valid(for: business,id: row.id) && target.task.client_id == id, "Independent Task fixture changed Client/Business")
        }
        for row in parent.providedConversations! {
            let target = try await repo.thread(business: business,id: row.id)
            try expect(target.valid(for: business,id: row.id) && target.clientReferenceID == id, "Independent thread fixture changed Client/Business")
        }
    }
    return count
}
