import Foundation
import CRMCore

func runTaskCreateReminderChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let f=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-create-reminder.json"))) as! [String:Any],ctx=TaskDraftContext(business:101,epoch:250),auth=SyntheticTaskCreateGrant(business:101,actor:9001,create:true).authorization(for:ctx)!
    func session(_ row:[String:Any])->TaskDraftSession {
        var s=TaskDraftSession();s.bind(ctx);_=s.open(expected:ctx);let c=s.selection!;s.update(.title,value:"Task",expected:c);s.update(.description,value:"Note",expected:c)
        s.chooseDue(.setDate,expected:c);s.update(.dueAt,value:row["due_raw"] as! String,expected:c);s.chooseDue(TaskDraftDueMode(rawValue:row["due_mode"] as! String)!,expected:c)
        s.chooseReminder(.setDate,expected:c);s.update(.reminderAt,value:row["reminder_raw"] as! String,expected:c);s.chooseReminder(TaskDraftDueMode(rawValue:row["reminder_mode"] as! String)!,expected:c);_=s.prepare(expected:c);return s
    }
    for row in f["input_cases"] as! [[String:Any]] {
        let s=session(row),valid=row["valid"] as! Bool
        try expect((s.phase == .review)==valid && s.values.dueDate.raw==row["due_raw"] as! String && s.values.reminderDate.raw==row["reminder_raw"] as! String,"Date modes/raw copied between fields or invalid reminder accepted")
        if valid {var ledger=TaskCreateAttemptLedger();let a=ledger.begin(review:s.review!,authorization:auth)!,body=try JSONSerialization.jsonObject(with:a.preparedBody()!) as! NSDictionary;try expect(body==row["expected_body"] as! NSDictionary,"Create dates body added null/default/mode/other fields")}
        else {try expect(s.issues.contains(where:{$0.problem == .date}),"Invalid selected date issue lost")}
    }
    for row in f["validation_cases"] as! [[String:Any]] {
        let s=session(row),review=s.review!;var ledger=TaskCreateAttemptLedger();let a=ledger.begin(review:review,authorization:auth)!,r=row["response"] as! [String:Any],data=try JSONSerialization.data(withJSONObject:r)
        let outcome:SyntheticTaskCreateOutcome
        if let task=try? JSONDecoder().decode(WorkTask.self,from:data) {outcome = .response(status:row["status"] as! Int,task:task,reminderAt:(row["include_evidence"] as! Bool) ? r["reminder_at"] as? String:nil)} else {outcome = .unknown}
        ledger.complete(a,outcome:outcome);let record=ledger.visible(auth)!,yes=row["expected"] as! String=="confirmed"
        try expect(record.phase == (yes ? .confirmed:.unknown),"Create reminder field evidence: \(row["name"]!)")
        try expect(record.attempt.review==review,"Reminder/due complete raw review lost")
        if yes && review.preview.reminderAt != nil {try expect(record.reminderAt==r["reminder_at"] as? String,"Selected returned reminder not retained")}
        else {try expect(record.reminderAt==nil,"Unselected/unknown reminder evidence promoted")}
        ledger.complete(a,outcome:.rejectedWithoutWrite);try expect(ledger.visible(auth)==record && ledger.acknowledge(auth)==yes,"Unknown acknowledged/terminal overwritten")
        if !yes {try expect(ledger.blocked(TaskDraftContext(business:101,epoch:251)),"New epoch recovered reminder create outcome")}
    }
    return count
}
