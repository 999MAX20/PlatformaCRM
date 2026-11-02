import Foundation
import CRMCore

func runTaskPriorityEditChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let fixture=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-priority-partial-outcome.json"))) as! [String:Any]
    try expect(TaskDraftValues.priorities==["low","normal","high","urgent"],"Priority vocabulary diverged from source")
    for row in fixture["input_cases"] as! [[String:Any]] {
        let value=TaskPriorityValue.parse(row["raw"] as! String)
        if row["expected_body"] is NSNull {try expect(value==nil,"Priority input trimmed/defaulted/coerced: \(row["name"]!)")}
        else {let body=try JSONSerialization.jsonObject(with:value!.body()!) as! NSDictionary;try expect(body==row["expected_body"] as! NSDictionary && body.count==1,"Priority body included untouched fields")}
    }
    let ctx=TaskCommentContext(business:101,task:1101,epoch:200),g=SyntheticTaskPriorityEditGrant(business:101,task:1101,actor:9001,update:true),auth=g.authorization(for:ctx)!
    func source(_ status:String="open",epoch:Int=200,revision:Int=1) throws -> TaskPriorityEditSource {
        let original=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-101-1101.json"))) as! [String:Any];var o=original["task"] as! [String:Any];o["status"]=status
        let task=try JSONDecoder().decode(WorkTask.self,from:JSONSerialization.data(withJSONObject:o));return TaskPriorityEditSource(read:TaskCommentRead(context:TaskCommentContext(business:101,task:1101,epoch:epoch),revision:revision),task:task)
    }
    for row in fixture["validation_cases"] as! [[String:Any]] {
        let review=TaskPriorityEditReview(source:try source(row["source_status"] as! String),visit:1,value:TaskPriorityValue.parse(row["selected"] as! String)!),confirmed=row["expected"] as! String=="confirmed"
        var ledger=TaskPriorityEditLedger();let attempt=ledger.begin(review,authorization:auth)!
        try expect(ledger.begin(review,authorization:auth)==nil,"Duplicate priority attempt")
        ledger.complete(attempt,outcome:.response(status:row["status"] as! Int,data:try JSONSerialization.data(withJSONObject:row["response"]!)));let record=ledger.visible(auth)!
        try expect(record.phase == (confirmed ? .confirmed:.unknown),"Priority result \(row["name"]!)")
        try expect(record.attempt.review==review && (!confirmed || record.result?.priority==review.value.raw),"Priority choice/source correlation lost")
        ledger.complete(attempt,outcome:.rejectedWithoutWrite);try expect(ledger.visible(auth)==record && ledger.acknowledge(auth)==confirmed,"Priority terminal overwritten/unknown acknowledged")
    }
    try expect(SyntheticTaskPriorityEditGrant(business:101,task:1101,actor:9001,update:false).authorization(for:ctx)==nil,"GET/CREATE inferred UPDATE")
    for status in ["done","cancelled","unknown",""] {let s=try source(status);var ledger=TaskPriorityEditLedger();try expect(!s.valid && ledger.begin(TaskPriorityEditReview(source:s,visit:1,value:TaskPriorityValue.parse("normal")!),authorization:auth)==nil,"Priority accepted terminal/unknown task")}
    let s=try source();var ledger=TaskPriorityEditLedger();let review=TaskPriorityEditReview(source:s,visit:1,value:TaskPriorityValue.parse("high")!),attempt=ledger.begin(review,authorization:auth)!;ledger.complete(attempt,outcome:.unknown)
    let newer=try source(epoch:201,revision:2),next=g.authorization(for:newer.read.context)!
    try expect(ledger.blocked(next.context) && ledger.visible(next)==nil && !ledger.acknowledge(next) && ledger.begin(TaskPriorityEditReview(source:newer,visit:2,value:review.value),authorization:next)==nil,"Matching new read/epoch inferred outcome")
    try expect(ledger.records[0].attempt.review==review,"Unknown priority lost immutable source/choice")
    return count
}
