import Foundation
import CRMCore

func runTaskCommentAuthorChecks(directory: URL) throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let template=try Data(contentsOf:directory.appendingPathComponent("task-101-1101.json")),original=try JSONDecoder().decode(TaskDetails.self,from:Data(contentsOf:directory.appendingPathComponent("task-101-1101.json")))
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-comment-author-read.json"))) as! [String:Any]
    for row in catalog["cases"] as! [[String:Any]] {
        var json=try JSONSerialization.jsonObject(with:template) as! [String:Any];var comments=json["comments"] as! [[String:Any]];comments[0].removeValue(forKey:"author");if let value=row["value"] {comments[0]["author"]=value};json["comments"]=comments
        let detail=try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:json)),read=detail.comments[0].authorRead
        let kind: String;switch read {case .notSet:kind="not_set";case .unknown:kind="unknown";case .person:kind="person"}
        try expect(kind==row["expected"] as! String,"Comment author null/type/person boundary changed: \(row["name"]!)")
        try expect(detail.valid(for:101,id:1101) && detail.comments.map(\.id)==original.comments.map(\.id) && detail.comments.map(\.text)==original.comments.map(\.text) && detail.comments.map(\.created_at)==original.comments.map(\.created_at),"Read author changed order/capped/identity/text/date")
        if case .person(let person)=read {try expect(person.displayName==(row["display"] as? String) && detail.comments[0].author==nil,"Read miniobject became numeric action identity")}
    }
    let action=Data("{\"id\":8801,\"task\":1101,\"author\":9001,\"author_name\":\"Synthetic employee\",\"author_email\":\"fixture@example.invalid\",\"text\":\"Manual comment\",\"created_at\":\"2026-10-30T12:00:00Z\"}".utf8)
    let decoded=try JSONDecoder().decode(TaskComment.self,from:action)
    try expect(decoded.author==9001 && decoded.authorRead == .unknown,"Numeric action FK was promoted to read person")
    count += try runMobileUserDisplayIdentity(directory:directory)
    return count
}

private func runMobileUserDisplayIdentity(directory:URL) throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("mobile-user-display-text-cases.json"))) as! [String:Any]
    func read(_ d:TaskDetails,_ context:String)->MobileUserRead {switch context {case "created_by":d.details.created_by;case "assignee":d.details.assignee;default:d.comments[0].authorRead}}
    for row in catalog["cases"] as! [[String:Any]] {
        let a=try TaskDetails.decodeSource(Data((row["before_json"] as! String).utf8)),b=try TaskDetails.decodeSource(Data((row["after_json"] as! String).utf8)),left=try JSONDecoder().decode(MobileUserItem.self,from:Data((row["before_user_json"] as! String).utf8)),right=try JSONDecoder().decode(MobileUserItem.self,from:Data((row["after_user_json"] as! String).utf8)),changed=row["changed"] as! Bool,context=row["context"] as! String
        try expect(left.id==right.id && left.valid && right.valid && (left != right)==changed,"Provided _user_item label identity collapsed or changed id/valid")
        try expect(SourceTextIdentity.same(left.displayName,row["before_display"] as? String) && SourceTextIdentity.same(right.displayName,row["after_display"] as? String),"User raw display or original blank fallback changed")
        try expect(read(a,context) == .person(left) && read(b,context) == .person(right) && (read(a,context) != read(b,context))==changed,"Nested user-read label identity changed or inferred another state")
        try expect((a != b)==changed && a.task==b.task && a.clientRead==b.clientRead && a.details.appointmentRead==b.details.appointmentRead && a.payload_budget==b.payload_budget,"Nested Task reference comparison missed raw label or changed non-user source")
        try expect(FixtureTaskCommentDraftSource.verified(b,reference:a) == !changed,"Changed user display bytes passed typed fixture reference")
        if context=="comment_author" {try expect(a.comments[0].author==nil && b.comments[0].author==nil,"Read person inferred numeric command actor")}
    }
    let a=try JSONDecoder().decode(MobileUserItem.self,from:JSONSerialization.data(withJSONObject:catalog["id_control_before"]!)),b=try JSONDecoder().decode(MobileUserItem.self,from:JSONSerialization.data(withJSONObject:catalog["id_control_other"]!)),invalid=try JSONDecoder().decode(MobileUserItem.self,from:JSONSerialization.data(withJSONObject:catalog["id_control_invalid"]!))
    try expect(a != b && !invalid.valid && a.valid && b.valid,"User id/invalid source semantics changed while fixing label equality")
    return count
}
