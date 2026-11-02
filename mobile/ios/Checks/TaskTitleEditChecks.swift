import Foundation
import CRMCore

func exactFixtureString(_ row:[String:Any],_ key:String)->String {
    try! JSONDecoder().decode(String.self,from:Data((row[key+"_json"] as! String).utf8))
}
func exactFixtureResponse(_ row:[String:Any])->Data {Data((row["response_json"] as! String).utf8)}
func runTaskTitleEditChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let fixture=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-title-partial-outcome.json"))) as! [String:Any]
    for row in fixture["input_cases"] as! [[String:Any]] {
        let value=TaskTitleValue.parse(exactFixtureString(row,"raw"))
        if row["expected_body"] is NSNull {try expect(value==nil,"Title input trimmed/defaulted/coerced: \(row["name"]!)")}
        else {let body=try JSONSerialization.jsonObject(with:value!.body()!) as! NSDictionary;try expect(body==row["expected_body"] as! NSDictionary && body.count==1,"Title body included untouched fields");let expected=try JSONDecoder().decode([String:String].self,from:Data((row["expected_body_json"] as! String).utf8))["title"]!;try expect(value!.raw.utf8.elementsEqual((exactFixtureString(row,"raw")).utf8) && value!.title.utf8.elementsEqual(expected.utf8),"Title scalar trim exact boundary \(row["name"]!) actual:\(value!.title.unicodeScalars.map {String($0.value,radix:16)}) expected:\(expected.unicodeScalars.map {String($0.value,radix:16)})")}
    }
    let ctx=TaskCommentContext(business:101,task:1101,epoch:200),g=SyntheticTaskTitleEditGrant(business:101,task:1101,actor:9001,update:true),auth=g.authorization(for:ctx)!
    func source(_ status:String="open",epoch:Int=200,revision:Int=1) throws -> TaskTitleEditSource {
        let original=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-101-1101.json"))) as! [String:Any];var o=original["task"] as! [String:Any];o["status"]=status
        let task=try JSONDecoder().decode(WorkTask.self,from:JSONSerialization.data(withJSONObject:o));return TaskTitleEditSource(read:TaskCommentRead(context:TaskCommentContext(business:101,task:1101,epoch:epoch),revision:revision),task:task)
    }
    for row in fixture["validation_cases"] as! [[String:Any]] {
        let review=TaskTitleEditReview(source:try source(row["source_status"] as! String),visit:1,value:TaskTitleValue.parse(exactFixtureString(row,"raw"))!),confirmed=row["expected"] as! String=="confirmed"
        var ledger=TaskTitleEditLedger();let attempt=ledger.begin(review,authorization:auth)!
        try expect(ledger.begin(review,authorization:auth)==nil,"Duplicate title attempt")
        ledger.complete(attempt,outcome:.response(status:row["status"] as! Int,data:exactFixtureResponse(row)));let record=ledger.visible(auth)!
        try expect(record.phase == (confirmed ? .confirmed:.unknown),"Title result \(row["name"]!)")
        try expect(record.attempt.review==review && (!confirmed || record.result?.title.utf8.elementsEqual(review.value.title.utf8)==true),"Title choice/source correlation lost")
        ledger.complete(attempt,outcome:.rejectedWithoutWrite);try expect(ledger.visible(auth)==record && ledger.acknowledge(auth)==confirmed,"Title terminal overwritten/unknown acknowledged")
    }
    try expect(SyntheticTaskTitleEditGrant(business:101,task:1101,actor:9001,update:false).authorization(for:ctx)==nil,"GET/CREATE inferred UPDATE")
    for status in ["done","cancelled","unknown",""] {let s=try source(status);var ledger=TaskTitleEditLedger();try expect(!s.valid && ledger.begin(TaskTitleEditReview(source:s,visit:1,value:TaskTitleValue.parse("Title")!),authorization:auth)==nil,"Title accepted terminal/unknown task")}
    let s=try source();var ledger=TaskTitleEditLedger();let review=TaskTitleEditReview(source:s,visit:1,value:TaskTitleValue.parse("  e\u{0301}  ")!),attempt=ledger.begin(review,authorization:auth)!;ledger.complete(attempt,outcome:.unknown)
    let newer=try source(epoch:201,revision:2),next=g.authorization(for:newer.read.context)!
    try expect(ledger.blocked(next.context) && ledger.visible(next)==nil && !ledger.acknowledge(next) && ledger.begin(TaskTitleEditReview(source:newer,visit:2,value:review.value),authorization:next)==nil,"Matching new read/epoch inferred outcome")
    try expect(ledger.records[0].attempt.review==review,"Unknown title lost immutable source/choice")
    return count
}
