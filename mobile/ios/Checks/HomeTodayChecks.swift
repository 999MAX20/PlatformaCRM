import Foundation
import CRMCore

func runHomeTodayChecks(directory: URL) async throws -> Int {
    var count = 0
    func expect(_ value: Bool, _ message: String) throws { guard value else { throw CheckFailure(message: message) }; count += 1 }
    func variant<T: Decodable>(_ name: String, as type: T.Type, _ change: (inout [String: Any]) -> Void) throws -> T {
        var json = try JSONSerialization.jsonObject(with: Data(contentsOf: directory.appendingPathComponent(name + ".json"))) as! [String: Any]
        change(&json); return try JSONDecoder().decode(type, from: JSONSerialization.data(withJSONObject: json))
    }
    let source = RecordingTransport(FixtureTransport(directory: directory)); let repo = APIReadRepository(transport: source)
    let home = try await repo.home(business: 101); let today = try await repo.today(business: 101, day: "2026-10-28")
    try expect(home.valid(for: 101) && home.sections.tasks?.open == 2, "Home source counts changed")
    try expect(today.valid(for: 101, day: "2026-10-28") && today.sections.tasks?.items.map(\.id) == [1101], "Today source subset changed")
    let requests = await source.requests
    try expect(requests == [ReadRequest(path: "/api/mobile/v1/home/", query: ["business":"101","limit":"5"]),ReadRequest(path: "/api/mobile/v1/today/", query: ["business":"101","date":"2026-10-28","limit":"20"])], "Home/Today invented route or query")
    let emptyHome = try variant("home-101", as: HomeSummary.self) { $0["sections"] = [:] }
    try expect(emptyHome.valid(for: 101) && emptyHome.sections.tasks == nil && emptyHome.sections.appointments == nil, "Withheld sections became zero")
    let sourceCount = try variant("home-101", as: HomeSummary.self) { $0["sections"] = ["tasks":["open":73]] }
    try expect(sourceCount.sections.tasks?.open == 73, "Home counter was recomputed from another list")
    let negative = try variant("home-101", as: HomeSummary.self) { $0["sections"] = ["tasks":["open":-1]] }
    try expect(!negative.valid(for: 101) && !home.valid(for: 202), "Invalid count/scope accepted")
    let impossibleUnread = try variant("home-101", as: HomeSummary.self) { $0["sections"] = ["conversations":["open":0,"unread":1]] }
    try expect(!impossibleUnread.valid(for: 101), "Unread conversation count exceeds open")
    let duplicate = try variant("today-101", as: TodaySummary.self) { json in
        var sections = json["sections"] as! [String:Any]; var a = sections["appointments"] as! [String:Any]; let rows = a["items"] as! [[String:Any]]; a["items"] = [rows[0],rows[0]]; sections["appointments"] = a; json["sections"] = sections
    }
    try expect(!duplicate.valid(for: 101, day: today.date), "Duplicate Today record accepted")
    let partial = try variant("today-101", as: TodaySummary.self) { $0["sections"] = ["appointments":["date":"2026-10-28","total":8,"items":[]]] }
    try expect(partial.valid(for: 101, day: today.date) && partial.sections.appointments?.partial == true, "Capped empty window became complete empty")
    let empty = try variant("today-101", as: TodaySummary.self) { $0["sections"] = ["appointments":["date":"2026-10-28","total":0,"items":[]]] }
    try expect(empty.sections.appointments?.partial == false && empty.sections.tasks == nil && empty.valid(for: 101, day: today.date), "Empty/missing conflated")
    let wrongDay = try variant("today-101", as: TodaySummary.self) { $0["sections"] = ["tasks":["date":"2026-10-27","total":0,"overdue":0,"items":[]]] }
    try expect(!wrongDay.valid(for: 101, day: today.date) && !today.valid(for: 101, day: "2026-10-29"), "Wrong day accepted")
    let wrongWindow = try variant("today-101", as: TodaySummary.self) { $0["payload_budget"] = ["max_items_per_section":0] }
    try expect(!wrongWindow.valid(for: 101, day: today.date), "Invalid source window accepted")
    let other = try await repo.today(business: 202, day: "2026-10-28")
    try expect(other.valid(for: 202, day: today.date) && other.sections.appointments?.items.map(\.id) == [601], "Business fixtures mixed")
    do { _ = try await repo.today(business: 101, day: "2026-02-30"); throw CheckFailure(message: "Invalid date requested") }
    catch let error as ReadFailure { try expect(error == .invalidContext, "Wrong invalid date error") }
    let denied = APIReadRepository(transport: FixedTransport(response: ReadResponse(status:403,data:Data())))
    do { _ = try await denied.home(business:101); throw CheckFailure(message:"Denied summary granted access") }
    catch let error as ReadFailure { try expect(error == .denied, "Wrong Home denial") }
    try expect(HomeDestination.allCases.map(\.tabIndex) == [1,2,3,4], "Home route mapped to wrong native section")
    return count
}
