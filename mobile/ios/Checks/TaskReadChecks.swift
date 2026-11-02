import Foundation
import CRMCore

func runTaskReadChecks(directory: URL) async throws -> Int {
    var count = 0
    func expect(_ condition: Bool, _ message: String) throws { guard condition else { throw CheckFailure(message: message) }; count += 1 }
    func variant(_ change: (inout [String: Any]) -> Void) throws -> TaskDetails {
        var json = try JSONSerialization.jsonObject(with: Data(contentsOf: directory.appendingPathComponent("task-101-1101.json"))) as! [String: Any]
        change(&json); return try JSONDecoder().decode(TaskDetails.self, from: JSONSerialization.data(withJSONObject: json))
    }
    let source = RecordingTransport(FixtureTransport(directory: directory))
    let repo = APIReadRepository(transport: source)
    let page = try await repo.tasks(business: 101), detail = try await repo.taskDetails(business: 101, id: 1101)
    try expect(page.valid(for: 101) && page.items.map(\.id) == [1101, 1103, 1102], "Task list order or identity changed")
    try expect(page.items.last?.due_at == nil && detail.task.priority == "high", "Null deadline/string priority changed")
    try expect(detail.valid(for: 101, id: 1101) && detail.comments.map(\.id) == [11012, 11011], "Task detail/comment order changed")
    let requests = await source.requests
    try expect(requests == [ReadRequest(path: "/api/mobile/v1/tasks/", query: ["business":"101", "limit":"50"]), ReadRequest(path: "/api/mobile/v1/tasks/1101/", query: ["business":"101"])], "Task read invented route or query")
    do { _ = try await repo.taskDetails(business: 101, id: 0); throw CheckFailure(message: "Invalid task ID reached transport") }
    catch let error as ReadFailure { try expect(error == .invalidContext, "Wrong task context error") }
    let afterInvalid = await source.requests
    try expect(afterInvalid.count == 2, "Invalid task ID issued a read")
    let foreign = try variant { $0["business"] = 202 }
    try expect(!foreign.valid(for: 101, id: 1101), "Foreign Business task detail accepted")
    let duplicate = try variant { json in let comments = json["comments"] as! [[String: Any]]; json["comments"] = [comments[0], comments[0]] }
    try expect(!duplicate.valid(for: 101, id: 1101), "Duplicate comment identity accepted")
    let capped = try variant { $0["payload_budget"] = ["max_comments": 2] }
    try expect(capped.valid(for: 101, id: 1101) && capped.commentsCapped, "Comment preview looked exhaustive")
    let unknown = try variant { json in
        var task = json["task"] as! [String: Any]; task["status"] = "future_status"; task["priority"] = "future_priority"; task["title"] = NSNull(); task["due_at"] = NSNull(); json["task"] = task
        json["details"] = ["description": NSNull()]
    }
    try expect(unknown.task.status == "future_status" && unknown.task.priority == "future_priority" && unknown.task.title == nil && unknown.details.description == nil, "Unknown or withheld task data was reinterpreted")
    let malformed = APIReadRepository(transport: FixedTransport(response: ReadResponse(status: 200, data: Data("{\"business\":\"101\",\"items\":[],\"summary\":{\"total\":0}}".utf8))))
    do { _ = try await malformed.tasks(business: 101); throw CheckFailure(message: "String task Business ID coerced") }
    catch let error as ReadFailure { try expect(error == .invalidPayload, "Wrong task malformed-payload error") }
    let denied = APIReadRepository(transport: FixedTransport(response: ReadResponse(status: 403, data: Data())))
    do { _ = try await denied.taskDetails(business: 101, id: 1101); throw CheckFailure(message: "Denied task detail accepted") }
    catch let error as ReadFailure { try expect(error == .denied, "Wrong task denied error") }
    count += try runTaskReadTextIdentity(directory:directory)
    return count
}

private func runTaskReadTextIdentity(directory:URL) throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let fixture=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-read-text-identity-cases.json"))) as! [String:Any]
    for row in fixture["cases"] as! [[String:Any]] {
        let aData=Data((row["before_json"] as! String).utf8),bData=Data((row["after_json"] as! String).utf8),changed=row["changed"] as! Bool,field=row["field"] as! String
        if row["kind"] as! String == "bounded" {
            let a=try TaskDetails.decodeSource(aData),b=try TaskDetails.decodeSource(bData)
            try expect(a.valid(for:101,id:1101) && b.valid(for:101,id:1101) && (a != b)==changed,"Task decoded free text identity collapsed or invalidated scoped source")
            let left:String?,right:String?
            switch field {
            case "task.title":left=a.task.title;right=b.task.title;try expect((a.task != b.task)==changed && a.details==b.details && a.comments==b.comments,"Title equality changed unrelated Task source fields")
            case "details.description":left=a.details.description;right=b.details.description;try expect(a.task==b.task && (a.details != b.details)==changed && a.comments==b.comments,"Description equality changed unrelated Task source fields")
            default:left=a.comments[0].text;right=b.comments[0].text;try expect(a.task==b.task && a.details==b.details && (a.comments != b.comments)==changed,"Comment equality changed unrelated Task source fields")
            }
            try expect(SourceTextIdentity.same(left,row["before"] as? String) && SourceTextIdentity.same(right,row["after"] as? String),"Decoded Task free text was trimmed/normalized")
            try expect(a.clientRead==b.clientRead && a.details.appointmentRead==b.details.appointmentRead && a.commentsCapped==b.commentsCapped && a.payload_budget==b.payload_budget,"Text identity changed original metadata/count/cap")
            try expect(FixtureTaskCommentDraftSource.verified(b,reference:a) == !changed,"Typed reference verification accepted changed Task free text")
            let read=TaskCommentRead(context:TaskCommentContext(business:101,task:1101,epoch:4200),revision:1)
            let ca=TaskClientEditSource(read:read,task:a.task,original:a.clientRead),cb=TaskClientEditSource(read:read,task:b.task,original:b.clientRead),aa=TaskAppointmentEditSource(read:read,task:a.task,original:a.details.appointmentRead),ab=TaskAppointmentEditSource(read:read,task:b.task,original:b.details.appointmentRead)
            try expect((ca != cb)==(a.task != b.task) && (aa != ab)==(a.task != b.task) && ca.valid==cb.valid && aa.valid==ab.valid,"Typed Task text source comparison lost relation identity/eligibility guard")
        } else {
            let a=try JSONDecoder().decode(WorkTask.self,from:aData),b=try JSONDecoder().decode(WorkTask.self,from:bData)
            try expect((a != b)==changed && a.valid==b.valid,"Existing WorkTask action field identity collapsed or changed validity")
            let left=field=="action.description" ? a.description:a.cancel_reason,right=field=="action.description" ? b.description:b.cancel_reason
            try expect(SourceTextIdentity.same(left,row["before"] as? String) && SourceTextIdentity.same(right,row["after"] as? String),"Action read text was normalized or inherited bounded original")
        }
    }
    for row in fixture["nontext_cases"] as! [[String:Any]] {
        let a=Data((row["before_json"] as! String).utf8),b=Data((row["after_json"] as! String).utf8)
        switch row["kind"] as! String {
        case "work":try expect(try JSONDecoder().decode(WorkTask.self,from:a) != JSONDecoder().decode(WorkTask.self,from:b),"WorkTask non-text comparator dropped: \(row["field"]!)")
        case "comment":try expect(try JSONDecoder().decode(TaskComment.self,from:a) != JSONDecoder().decode(TaskComment.self,from:b),"TaskComment metadata comparator dropped: \(row["field"]!)")
        default:try expect(try TaskDetails.decodeSource(a) != TaskDetails.decodeSource(b),"Task original/presence comparator dropped: \(row["field"]!)")
        }
    }
    try expect(SourceTextIdentity.same(nil,nil) && !SourceTextIdentity.same(nil,"") && !SourceTextIdentity.same("",nil),"Typed Task nil and empty collapsed")
    return count
}
