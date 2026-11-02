import Foundation
import CRMCore

func runAttentionQueueChecks(directory: URL) async throws -> Int {
    var count = 0
    func expect(_ value: Bool, _ message: String) throws { guard value else { throw CheckFailure(message: message) }; count += 1 }
    func variant(_ change: (inout [String: Any]) -> Void) throws -> AttentionPage {
        var json = try JSONSerialization.jsonObject(with: Data(contentsOf: directory.appendingPathComponent("actions-101.json"))) as! [String:Any]
        change(&json); return try JSONDecoder().decode(AttentionPage.self, from: JSONSerialization.data(withJSONObject: json))
    }
    func itemVariant(_ index: Int, _ change: (inout [String: Any]) -> Void) throws -> AttentionPage {
        try variant { json in var rows = json["items"] as! [[String:Any]]; change(&rows[index]); json["items"] = rows }
    }
    let source = RecordingTransport(FixtureTransport(directory: directory)); let repo = APIReadRepository(transport: source)
    let page = try await repo.actions(business: 101)
    try expect(page.valid(for: 101) && page.total == 5 && !page.windowCapped, "Queue source window changed")
    let requests = await source.requests
    try expect(requests == [ReadRequest(path:"/api/mobile/v1/actions/",query:["business":"101","limit":"20"])], "Queue invented route or command")
    try expect(page.items.map { $0.readTarget?.kind } == [nil,.task,.conversation,nil,.appointment], "Unsupported row gained a read target")
    try expect(page.items[0].entity.id == page.items[1].entity.id && page.items[0].id != page.items[1].id, "Composite queue identity collapsed across types")
    for href: String? in [nil,"https://example.invalid/app/calendar?appointment=511","//app/calendar?appointment=511","/app/calendar?appointment=512","/app/calendar?appointment=511&x=1","/app/calendar?appointment=511#x","/app/calendar?appointment=%35%31%31","/app/leads?lead=511"] {
        let malformed = try itemVariant(4) { row in var e = row["entity"] as! [String:Any]; e["href"] = href.map { $0 as Any } ?? NSNull(); row["entity"] = e }
        try expect(malformed.items[4].readTarget == nil, "Unsafe/mismatched href offered native target")
    }
    for kind in ["lead","deal","approval","future_kind"] {
        let unsupported = try itemVariant(4) { $0["type"] = kind }
        try expect(unsupported.items[4].readTarget == nil, "Legacy/unknown type mapped to Appointment")
    }
    let unknown = try itemVariant(4) { $0["key"] = "future_key" }
    try expect(unknown.items[4].readTarget == nil, "Unknown action key gained execution/navigation")
    let full = try variant { $0["limit"] = 5; $0["payload_budget"] = ["max_items":5] }
    try expect(full.valid(for:101) && full.windowCapped, "Full source window claimed global completeness")
    let wrongTotal = try variant { $0["total"] = 99 }
    try expect(!wrongTotal.valid(for:101), "Global total invented from truncated source")
    let badBudget = try variant { $0["payload_budget"] = ["max_items":0] }
    try expect(!badBudget.valid(for:101), "Invalid window accepted")
    let duplicate = try variant { json in var rows = json["items"] as! [[String:Any]]; rows.append(rows[0]); json["items"] = rows; json["total"] = rows.count }
    try expect(!duplicate.valid(for:101), "Duplicate queue identity accepted")
    let reverse = try variant { $0["items"] = Array(($0["items"] as! [[String:Any]]).reversed()) }
    try expect(reverse.items.map(\.priority) == [30,20,15,10,5] && reverse.valid(for:101), "Consumer re-sorted source priority")
    let empty = try variant { $0["items"] = []; $0["total"] = 0 }
    try expect(empty.valid(for:101) && !empty.windowCapped && empty.items.isEmpty, "Empty window differs from loaded empty")
    let hidden = try itemVariant(1) { row in var e = row["entity"] as! [String:Any]; e["title"] = NSNull(); e["future"] = true; row["entity"] = e }
    try expect(hidden.items[1].entity.title == nil && hidden.items[1].readTarget?.id == 1111, "Withheld title changed explicit target identity")
    let other = try await repo.actions(business:202)
    try expect(other.valid(for:202) && !page.valid(for:202), "Queue Business scope mixed")
    let task = try await repo.taskDetails(business:101,id:1111), thread = try await repo.thread(business:101,id:911), appointment = try await repo.appointment(business:101,id:511)
    try expect(AttentionDetail.task(task).valid(for:101,target:page.items[1].readTarget!), "Task target no longer independently readable")
    try expect(AttentionDetail.conversation(thread).valid(for:101,target:page.items[2].readTarget!), "Thread target no longer independently readable")
    try expect(AttentionDetail.appointment(appointment).valid(for:101,target:page.items[4].readTarget!), "Record target no longer independently readable")
    try expect(!AttentionDetail.task(task).valid(for:101,target:page.items[4].readTarget!) && !AttentionDetail.task(task).valid(for:202,target:page.items[1].readTarget!), "Target type or Business inferred from numeric ID")
    do { _ = try await repo.actions(business:0); throw CheckFailure(message:"Invalid queue scope contacted repository") }
    catch let error as ReadFailure { try expect(error == .invalidContext, "Wrong queue context error") }
    return count
}
