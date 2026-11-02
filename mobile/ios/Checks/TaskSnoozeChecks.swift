import Foundation
import CRMCore

func runTaskSnoozeChecks(directory:URL) throws -> Int {
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-snooze-outcome.json"))) as! [String:Any]
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    for row in catalog["input_cases"] as! [[String:Any]] {
        let raw=row["raw"] as! String,value=TaskSnoozeValue.parse(raw)
        let expected=(row["microseconds"] as? NSNumber)?.int64Value
        try expect(value?.microseconds==expected,"Snooze exact input \(row["name"]!)")
        try expect(value==nil || value?.raw==raw,"Snooze changed raw input")
    }
    let original=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-101-1101.json"))) as! [String:Any]
    let ctx=TaskCommentContext(business:101,task:1101,epoch:170),grant=SyntheticTaskSnoozeGrant(business:101,task:1101,actor:9001,update:true),auth=grant.authorization(for:ctx)!
    func source(status:String="open",reminder:TaskScheduleValue = .notSet,epoch:Int=170,revision:Int=1) throws -> TaskSnoozeSource {
        var payload=original,t=original["task"] as! [String:Any];t["status"]=status;payload["task"]=t
        let detail=try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:payload))
        return TaskSnoozeSource(read:TaskCommentRead(context:TaskCommentContext(business:101,task:1101,epoch:epoch),revision:revision),task:detail.task,reminder:reminder)
    }
    for row in catalog["validation_cases"] as! [[String:Any]] {
        let reminder:TaskScheduleValue
        if let raw=row["source_reminder"] as? String {reminder = .instant(raw)} else if row["source_reminder"] is NSNull {reminder = .notSet} else {reminder = .unknown}
        let s=try source(status:row["source_status"] as! String,reminder:reminder),value=TaskSnoozeValue.parse(row["input"] as! String)!,review=TaskSnoozeReview(source:s,visit:1,value:value)
        var ledger=TaskSnoozeLedger();let a=ledger.begin(review,authorization:auth)!
        try expect(ledger.begin(review,authorization:auth)==nil,"Duplicate pending snooze")
        ledger.complete(a,outcome:.response(status:row["status"] as! Int,data:try JSONSerialization.data(withJSONObject:row["response"]!)));let record=ledger.visible(auth)!
        let confirmed=row["expected"] as! String=="confirmed"
        try expect(record.phase == (confirmed ? .confirmed:.unknown),"Snooze result scope/instant/unchanged fields \(row["name"]!)")
        try expect(record.attempt.review==review && record.attempt.review.value.raw==value.raw,"Snooze lost exact source/input")
        ledger.complete(a,outcome:.rejectedWithoutWrite);try expect(ledger.visible(auth)==record,"Late snooze replaced terminal result")
        try expect(ledger.acknowledge(auth)==confirmed,"Snooze unknown acknowledged")
    }
    for status in ["done","cancelled","unknown",""] {
        let s=try source(status:status);var ledger=TaskSnoozeLedger()
        try expect(s.identityValid && !s.valid && ledger.begin(TaskSnoozeReview(source:s,visit:1,value:TaskSnoozeValue.parse("2026-10-30T12:00:00Z")!),authorization:auth)==nil,"Snooze accepted terminal/unknown status")
    }
    try expect(SyntheticTaskSnoozeGrant(business:101,task:1101,actor:9001,update:false).authorization(for:ctx)==nil,"Snooze GET became UPDATE")
    try expect(grant.authorization(for:TaskCommentContext(business:202,task:1101,epoch:170))==nil,"Snooze crossed Business")
    let s=try source(),r=TaskSnoozeReview(source:s,visit:1,value:TaskSnoozeValue.parse("2000-02-29T00:00:00Z")!)
    var ledger=TaskSnoozeLedger();let a=ledger.begin(r,authorization:auth)!;ledger.complete(a,outcome:.unknown)
    let newer=try source(epoch:171,revision:2),nextAuth=grant.authorization(for:newer.read.context)!
    try expect(ledger.blocked(newer.read.context) && ledger.visible(nextAuth)==nil && !ledger.acknowledge(nextAuth),"Snooze new read/epoch became outcome proof")
    try expect(ledger.records[0].attempt.review.value.raw==r.value.raw,"Unknown snooze raw lost across owner")
    return count
}
