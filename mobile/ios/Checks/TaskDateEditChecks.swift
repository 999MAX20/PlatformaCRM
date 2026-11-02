import Foundation
import CRMCore

func runTaskDateEditChecks(directory:URL) throws -> Int {
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-date-partial-outcome.json"))) as! [String:Any]
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    for row in catalog["input_cases"] as! [[String:Any]] {
        let change=TaskDateChange(field:TaskDateField(rawValue:row["field"] as! String)!,mode:TaskDateMode(rawValue:row["mode"] as! String)!,raw:row["raw"] as! String)
        if row["expected_body"] is NSNull {try expect(change.body()==nil && !change.valid,"Invalid set became implicit clear/default")}
        else {let body=try JSONSerialization.jsonObject(with:change.body()!) as! NSDictionary,expected=row["expected_body"] as! NSDictionary;try expect(body==expected && body.count==1,"Date body resubmitted other fields: \(row["name"]!)");try expect(!body.allKeys.contains(where:{($0 as? String)=="description"}),"Date body resubmitted bounded description")}
    }
    var draft=TaskDateDraft();try expect(draft.field==nil && draft.mode==nil && draft.change==nil,"Date field/mode defaulted")
    draft.select(.dueAt);try expect(draft.change==nil,"Field selection defaulted mode")
    draft.choose(.setDate);draft.update("2026-10-30T12:00:00Z");let due=draft.change!
    draft.select(.reminderAt);try expect(draft.raw.isEmpty && draft.mode==nil,"Another date defaulted from prior field")
    draft.choose(.clearDate);draft.update("kept unused raw");try expect(draft.change?.mode == .clearDate,"Explicit null intent lost")
    draft.select(.dueAt);try expect(draft.change==due,"Field switch lost original set/raw")
    let original=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-101-1101.json"))) as! [String:Any],ctx=TaskCommentContext(business:101,task:1101,epoch:190),grant=SyntheticTaskDateEditGrant(business:101,task:1101,actor:9001,update:true),auth=grant.authorization(for:ctx)!
    func source(_ status:String="open",epoch:Int=190,revision:Int=1) throws -> TaskDateEditSource {
        var o=original,t=o["task"] as! [String:Any];t["status"]=status;o["task"]=t
        let d=try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:o))
        return TaskDateEditSource(read:TaskCommentRead(context:TaskCommentContext(business:101,task:1101,epoch:epoch),revision:revision),task:d.task)
    }
    for row in catalog["validation_cases"] as! [[String:Any]] {
        let s=try source(row["source_status"] as! String),change=TaskDateChange(field:TaskDateField(rawValue:row["field"] as! String)!,mode:TaskDateMode(rawValue:row["mode"] as! String)!,raw:row["raw"] as! String),review=TaskDateEditReview(source:s,visit:1,change:change)
        var ledger=TaskDateEditLedger();let a=ledger.begin(review,authorization:auth)!
        try expect(ledger.begin(review,authorization:auth)==nil,"Duplicate date attempt accepted")
        ledger.complete(a,outcome:.response(status:row["status"] as! Int,data:try JSONSerialization.data(withJSONObject:row["response"]!)));let record=ledger.visible(auth)!,confirmed=row["expected"] as! String=="confirmed"
        try expect(record.phase == (confirmed ? .confirmed:.unknown),"Selected date result \(row["name"]!)")
        try expect(record.attempt.review==review,"Date field/mode/raw/source lost")
        if confirmed {try expect(record.result?.field==change.field && record.result?.matches(change)==true,"Date lens correlated another field")}
        ledger.complete(a,outcome:.rejectedWithoutWrite);try expect(ledger.visible(auth)==record && ledger.acknowledge(auth)==confirmed,"Date terminal overwritten or unknown acknowledged")
    }
    for status in ["done","cancelled","unknown",""] {let bad=try source(status);var ledger=TaskDateEditLedger();try expect(bad.identityValid && !bad.valid && ledger.begin(TaskDateEditReview(source:bad,visit:1,change:due),authorization:auth)==nil,"Date accepted terminal/unknown source status")}
    try expect(SyntheticTaskDateEditGrant(business:101,task:1101,actor:9001,update:false).authorization(for:ctx)==nil,"GET became date UPDATE")
    var ledger=TaskDateEditLedger();let initial=try source(),a=ledger.begin(TaskDateEditReview(source:initial,visit:1,change:due),authorization:auth)!;ledger.complete(a,outcome:.unknown)
    let newer=try source(epoch:191,revision:2),newAuth=grant.authorization(for:newer.read.context)!
    try expect(ledger.blocked(newer.read.context) && ledger.visible(newAuth)==nil && !ledger.acknowledge(newAuth),"Date new read/epoch proved outcome")
    try expect(ledger.records[0].attempt.review.change==due,"Unknown date intent lost")
    return count
}
