import Foundation
import CRMCore

func runTaskCreateDueChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let f=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-create-due-at.json"))) as! [String:Any],ctx=TaskDraftContext(business:101,epoch:240),auth=SyntheticTaskCreateGrant(business:101,actor:9001,create:true).authorization(for:ctx)!
    func session(mode:String,raw:String)->TaskDraftSession {
        var s=TaskDraftSession();s.bind(ctx);_=s.open(expected:ctx);let c=s.selection!;s.update(.title,value:"Task",expected:c);s.update(.description,value:"Note",expected:c);s.chooseDue(.setDate,expected:c);s.update(.dueAt,value:raw,expected:c);s.chooseDue(TaskDraftDueMode(rawValue:mode)!,expected:c);_=s.prepare(expected:c);return s
    }
    for row in f["input_cases"] as! [[String:Any]] {
        let s=session(mode:row["mode"] as! String,raw:row["raw"] as! String),valid=row["valid"] as! Bool
        try expect((s.phase == .review)==valid && s.values.dueDate.raw==row["raw"] as! String,"Date validation changed raw or accepted invalid input")
        if valid {var ledger=TaskCreateAttemptLedger();let a=ledger.begin(review:s.review!,authorization:auth)!,body=try JSONSerialization.jsonObject(with:a.preparedBody()!) as! NSDictionary;try expect(body==row["expected_body"] as! NSDictionary,"Date create body added null/default/mode/other fields")}
        else {try expect(s.issues.contains(where:{$0.field == .dueAt && $0.problem == .date}),"Invalid date issue was not field-owned")}
    }
    for row in f["validation_cases"] as! [[String:Any]] {
        let s=session(mode:row["mode"] as! String,raw:row["raw"] as! String),review=s.review!;var ledger=TaskCreateAttemptLedger();let a=ledger.begin(review:review,authorization:auth)!,data=try JSONSerialization.data(withJSONObject:row["response"]!)
        let outcome:SyntheticTaskCreateOutcome
        if let task=try? JSONDecoder().decode(WorkTask.self,from:data) {outcome = .response(status:row["status"] as! Int,task:task)} else {outcome = .unknown}
        ledger.complete(a,outcome:outcome);let r=ledger.visible(auth)!,yes=row["expected"] as! String=="confirmed"
        try expect(r.phase == (yes ? .confirmed:.unknown),"Selected create due_at: \(row["name"]!)")
        try expect(r.attempt.review==review,"Date raw/mode/whole form attempt lost")
        ledger.complete(a,outcome:.rejectedWithoutWrite);try expect(ledger.visible(auth)==r && ledger.acknowledge(auth)==yes,"Unknown date acknowledged/terminal overwritten")
        if !yes {let next=TaskDraftContext(business:101,epoch:241);try expect(ledger.blocked(next),"Date reread/epoch recovered create")}
    }
    return count
}
