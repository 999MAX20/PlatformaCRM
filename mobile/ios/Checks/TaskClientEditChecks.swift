import Foundation
import CRMCore

private actor ClientEditRawRead:ReadTransport {
    let data:Data;private var sent:[ReadRequest]=[]
    init(_ data:Data) {self.data=data}
    func get(_ request:ReadRequest) async throws -> ReadResponse {sent.append(request);return ReadResponse(status:200,data:data)}
    func requests()->[ReadRequest] {sent}
}
func runTaskClientEditChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let data=try Data(contentsOf:directory.appendingPathComponent("task-client-partial-cases.json")),catalog=try JSONSerialization.jsonObject(with:data) as! [String:Any]
    for row in catalog["original_cases"] as! [[String:Any]] {
        let raw=Data((row["payload_json"] as! String).utf8),kind=row["kind"] as! String,expected:TaskClientOriginal=kind=="client" ? .client(row["id"] as! Int):kind=="notSet" ? .notSet:.unknown
        try expect(TaskClientOriginal.decode(raw)==expected,"Original GET relation was coerced/defaulted/aliased: \(row["name"]!)")
        let before=try? JSONDecoder().decode(TaskDetails.self,from:raw),transport=ClientEditRawRead(raw),repo=APIReadRepository(transport:transport)
        do {let detail=try await repo.taskDetails(business:101,id:1101);try expect(before != nil && detail.clientRead==expected && detail.clientSameLegacyFields(as:before!),"Same GET bytes strict original projection altered legacy payload acceptance")}
        catch {try expect(before==nil && error as? ReadFailure == .invalidPayload,"Malformed original relaxed an existing payload failure")}
        try expect(await transport.requests()==[ReadRequest(path:"/api/mobile/v1/tasks/1101/",query:["business":"101"])],"Original relation issued extra/changed GET")
    }
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),detail=try await repo.taskDetails(business:101,id:1101),context=TaskCommentContext(business:101,task:1101,epoch:1),read=TaskCommentRead(context:context,revision:1),source=TaskClientEditSource(read:read,task:detail.task,original:detail.clientRead),grant=SyntheticTaskClientEditGrant(business:101,task:1101,actor:9001,update:true),auth=grant.authorization(for:context)!,choice=TaskDraftClientChoice(profile:try await repo.clientProfile(business:101,id:1754),business:101,id:1754)!,foreign=TaskDraftClientChoice(profile:try await repo.clientProfile(business:202,id:801),business:202,id:801)!
    func draft(_ mode:TaskClientEditMode)->TaskClientEditDraft {var d=TaskClientEditDraft();d.mode=mode;d.query="  Client query  ";d.choice=choice;d.choiceRead=read;return d}
    try expect(SyntheticTaskClientEditGrant(business:101,task:1101,actor:9001,update:false).authorization(for:context)==nil && grant.authorization(for:TaskCommentContext(business:202,task:1101,epoch:1))==nil,"GET/foreign context granted UPDATE")
    try expect(TaskClientEditDraft().change(for:source)==nil,"Unset mode defaulted a set/null change")
    var invalid=draft(.set);invalid.choice=nil;try expect(invalid.change(for:source)==nil,"Missing Client choice defaulted a relation")
    invalid=draft(.set);invalid.choice=foreign;try expect(invalid.change(for:source)==nil,"Foreign Client choice changed Task relation")
    invalid=draft(.set);invalid.choiceRead=TaskCommentRead(context:context,revision:2);try expect(invalid.change(for:source)==nil,"Old/future read adopted selected Client")
    for original in [TaskClientOriginal.unknown,.client(0),.client(Int(Int32.max)+1)] {let s=TaskClientEditSource(read:read,task:detail.task,original:original);try expect(!s.valid && draft(.clear).change(for:s)==nil,"Unknown original became an explicit-null edit")}
    for status in ["open","in_progress","done","cancelled","future-status"] {
        let task=WorkTask(id:1101,title:"Original",status:status,priority:"normal",due_at:nil,business:101),s=TaskClientEditSource(read:read,task:task,original:.notSet)
        try expect(s.valid==["open","in_progress"].contains(status),"Source update-details status gate drifted")
    }
    for row in catalog["result_cases"] as! [[String:Any]] {
        let mode:TaskClientEditMode=row["mode"] as! String=="clear" ? .clear:.set,d=draft(mode),review=TaskClientEditReview(source:source,visit:1,draft:d);var ledger=TaskClientEditLedger();let a=ledger.begin(review,authorization:auth)!,body=a.preparedBody()!,fields=try JSONSerialization.jsonObject(with:body) as! [String:Any]
        try expect(Set(fields.keys)==["client"] && (mode == .clear ? fields["client"] is NSNull:fields["client"] as? Int==1754),"Relation edit serialized another field/default/alias")
        try expect(ledger.begin(review,authorization:auth)==nil && !ledger.acknowledge(auth),"Pending relation edit repeated/cleared")
        ledger.complete(a,outcome:.response(status:row["status"] as! Int,data:Data((row["response_json"] as! String).utf8)));let record=ledger.visible(auth)!,yes=row["accepted"] as! Bool
        try expect((record.phase == .confirmed)==yes,"Unverified selected Client result became fake confirmation: \(row["name"]!)")
        try expect(record.attempt.review==review && record.attempt.preparedBody()==body,"Result lost exact original/mode/candidate/day/body/attempt")
        ledger.complete(a,outcome:.rejectedWithoutWrite);try expect(ledger.visible(auth)?.phase==record.phase,"Duplicate terminal reply rewrote relation outcome")
        if !yes {
            let fresh=TaskCommentContext(business:101,task:1101,epoch:2),a2=grant.authorization(for:fresh)!
            try expect(ledger.blocked(fresh) && ledger.visible(a2)==nil && !ledger.acknowledge(auth) && ledger.begin(review,authorization:auth)==nil,"Unknown cleared/rekeyed/replayed through fresh Task epoch")
        }
    }
    for mode in [TaskClientEditMode.set,.clear] {var ledger=TaskClientEditLedger();let r=TaskClientEditReview(source:source,visit:1,draft:draft(mode)),a=ledger.begin(r,authorization:auth)!;ledger.complete(a,outcome:try await FixtureTaskClientEditPort(directory:directory).execute(a));try expect(ledger.visible(auth)?.phase == .confirmed && ledger.visible(auth)?.result?.value==(mode == .clear ? nil:1754),"Explicit separate synthetic UPDATE selected-FK producer failed")}
    let raw=try Data(contentsOf:directory.appendingPathComponent("task-101-1101.json")),same=try TaskDetails.decodeSource(raw)
    let fixtureMatches=await FixtureTaskCommentDraftSource(directory:directory).matchesFixture(detail);try expect(same==detail && fixtureMatches,"Shared source decoder lost existing fixture context equality")
    try expect(same.details.appointmentRead==detail.details.appointmentRead && same.task==detail.task,"Client original lens changed Appointment/header")
    return count
}
private extension TaskDetails {
    func clientSameLegacyFields(as other:TaskDetails)->Bool {business==other.business && task==other.task && task.client_id==other.task.client_id && details.description==other.details.description && details.reminder_at==other.details.reminder_at && comments==other.comments && payload_budget.max_comments==other.payload_budget.max_comments}
}
