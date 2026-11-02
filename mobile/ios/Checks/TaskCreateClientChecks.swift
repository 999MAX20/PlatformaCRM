import Foundation
import CRMCore

func runTaskCreateClientChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let data=try Data(contentsOf:directory.appendingPathComponent("task-create-client-cases.json")),catalog=try JSONSerialization.jsonObject(with:data) as! [String:Any],fixed=APIReadRepository(transport:FixtureTransport(directory:directory)),profile=try await fixed.clientProfile(business:101,id:701),selected=TaskDraftClientChoice(profile:profile,business:101,id:701)!,other=TaskDraftClientChoice(profile:try await fixed.clientProfile(business:202,id:801),business:202,id:801)!
    for row in catalog["choice_cases"] as! [[String:Any]] {
        let profile=try JSONDecoder().decode(ClientProfile.self,from:Data((row["profile_json"] as! String).utf8)),choice=TaskDraftClientChoice(profile:profile,business:row["business"] as! Int,id:row["id"] as! Int)
        try expect((choice != nil)==row["valid"] as! Bool,"Client relation profile scope \(row["name"]!)")
        if let choice {let title=try JSONDecoder().decode(String?.self,from:Data((row["title_json"] as! String).utf8));try expect(choice.id==row["id"] as! Int && choice.business==row["business"] as! Int && choice.title.map({Data($0.utf8)})==title.map({Data($0.utf8)}),"Client relation title/id was defaulted/normalized")}
    }
    let context=TaskDraftContext(business:101,epoch:1),auth=SyntheticTaskCreateGrant(business:101,actor:9001,create:true).authorization(for:context)!
    func editor(_ choice:TaskDraftClientChoice?) -> TaskDraftSession {
        var s=TaskDraftSession();s.bind(context);_=s.open(expected:context);let q=s.selection!;s.update(.title,value:catalog["raw_title"] as! String,expected:q);s.update(.description,value:catalog["raw_description"] as! String,expected:q);s.chooseDue(.setDate,expected:q);s.update(.dueAt,value:catalog["due_raw"] as! String,expected:q);s.chooseReminder(.setDate,expected:q);s.update(.reminderAt,value:catalog["reminder_raw"] as! String,expected:q);s.chooseClient(choice,expected:q);return s
    }
    var s=editor(selected);let original=s.values;s.chooseClient(other,expected:s.selection!);try expect(s.values==original,"Foreign Client changed independently owned draft/raw input")
    s.chooseClient(nil,expected:s.selection!);try expect(s.values.client==nil && s.values.title==original.title && s.values.description==original.description && s.values.dueDate==original.dueDate && s.values.reminderDate==original.reminderDate,"Removing unsent Client changed raw text/dates")
    for row in catalog["receipt_cases"] as! [[String:Any]] {
        var s=editor(row["selected"] is NSNull ? nil:selected);let q=s.selection!;_=s.prepare(expected:q);let review=s.review!;var ledger=TaskCreateAttemptLedger();let attempt=ledger.begin(review:review,authorization:auth)!,body=try JSONSerialization.jsonObject(with:attempt.preparedBody()!) as! [String:Any],client=review.preview.clientID
        try expect(body["client_id"]==nil && (body["client"] as? Int)==client && body["due_at"] as? String==catalog["due_raw"] as? String && body["reminder_at"] as? String==catalog["reminder_raw"] as? String,"Create Client/date field renamed/defaulted/null-cleared")
        try expect(review.values.title==catalog["raw_title"] as! String && review.values.description==catalog["raw_description"] as! String && review.values.client?.id==client,"Raw Client/text snapshot not immutable")
        let read=TaskCreateClientRead.decode(Data((row["body_json"] as! String).utf8)),kind=row["kind"] as! String
        let expectedRead:TaskCreateClientRead=kind=="client" ? .client(row["id"] as! Int):kind=="notSet" ? .notSet:.unknown
        try expect(read==expectedRead,"Generic client field was aliased from GET/string/float/default")
        let v=review.preview,task=WorkTask(id:88001,title:v.title,status:"open",priority:v.priority,due_at:v.dueAt,client_id:999,business:101,updated_at:"2026-10-30T12:00:00Z",description:v.description,created_by:9001,created_at:"2026-10-30T12:00:00Z")
        ledger.complete(attempt,outcome:.response(status:row["status"] as! Int,task:task,reminderAt:v.reminderAt,clientRead:read));let record=ledger.visible(auth)!,yes=row["accepted"] as! Bool
        try expect((record.phase == .confirmed)==yes,"Unverified/mismatched Client receipt became synthetic success: \(row["name"]!)")
        try expect(record.clientID==(yes ? client:nil),"Unselected/unknown generic Client was promoted into accepted relationship")
        if !yes {
            let saved=record.attempt.preparedBody();s.back(expected:q);s.chooseClient(nil,expected:q);_=s.prepare(expected:q)
            try expect(ledger.blocked(context) && !ledger.acknowledge(auth) && ledger.begin(review:s.review!,authorization:auth)==nil && ledger.records[0].attempt.preparedBody()==saved && ledger.records[0].attempt.review==review,"Unknown Client input/body guard: \(row["name"]!)")
        }
    }
    var local=editor(selected);_=local.prepare(expected:local.selection!);var ledger=TaskCreateAttemptLedger();let a=ledger.begin(review:local.review!,authorization:auth)!;let outcome=try await FixtureTaskCreatePort(directory:directory).execute(a);ledger.complete(a,outcome:outcome)
    try expect(ledger.visible(auth)?.phase == .confirmed && ledger.visible(auth)?.clientID==701,"Explicit fake producer failed selected generic client receipt")
    return count
}
