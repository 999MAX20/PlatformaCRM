import Foundation
import CRMCore

func runTaskCreationChecks(directory: URL) throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let context=TaskDraftContext(business:101,epoch:1),grant=SyntheticTaskCreateGrant(business:101,actor:9001,create:true)
    func review(_ context: TaskDraftContext) -> TaskDraftReview {var s=TaskDraftSession();s.bind(context);_=s.open(expected:context);let selection=s.selection!;s.update(.title,value:"  Manual task\n",expected:selection);s.update(.description,value:"  Manual description\n",expected:selection);s.update(.priority,value:"high",expected:selection);_=s.prepare(expected:selection);return s.review!}
    let authorization=grant.authorization(for:context)!,r=review(context)
    try expect(SyntheticTaskCreateGrant(business:101,actor:9001,create:false).authorization(for:context)==nil && grant.authorization(for:TaskDraftContext(business:202,epoch:1))==nil && grant.authorization(for:TaskDraftContext(business:101,epoch:0))==nil,"VIEW/UPDATE/foreign/invalid context granted CREATE")
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-create-outcome.json"))) as! [String:Any]
    for row in catalog["validation_cases"] as! [[String:Any]] {
        var ledger=TaskCreateAttemptLedger();let a=ledger.begin(review:r,authorization:authorization)!
        try expect(a.review.values.title=="  Manual task\n" && a.review.preview.title=="Manual task","Creation attempt lost raw vs normalized snapshot")
        try expect(ledger.begin(review:r,authorization:authorization)==nil && !ledger.acknowledge(authorization),"Pending create repeated or cleared")
        let task=try? JSONDecoder().decode(WorkTask.self,from:JSONSerialization.data(withJSONObject:row["response"]!))
        ledger.complete(a,outcome:task.map {.response(status:row["status"] as! Int,task:$0)} ?? .unknown)
        let expected:TaskCreateAttemptPhase = row["expected"] as! String == "confirmed" ? .confirmed:.unknown
        try expect(ledger.visible(authorization)?.phase==expected,"Unverified CREATE response became synthetic success: \(row["name"]!)")
        ledger.complete(a,outcome:.rejectedWithoutWrite);try expect(ledger.records[0].phase==expected,"Duplicate terminal create completion rewrote result")
        if expected == .unknown {try expect(!ledger.acknowledge(authorization) && ledger.begin(review:r,authorization:authorization)==nil,"Unknown create permitted blind replay")}
    }
    var ledger=TaskCreateAttemptLedger();let first=ledger.begin(review:r,authorization:authorization)!
    let otherEpoch=grant.authorization(for:TaskDraftContext(business:101,epoch:2))!
    try expect(ledger.visible(otherEpoch)==nil && ledger.blocked(otherEpoch.context),"New epoch exposed/replayed old creation")
    ledger.complete(first,outcome:.rejectedWithoutWrite);try expect(ledger.acknowledge(authorization) && ledger.records[0].attempt.review.values==r.values,"Definitive no-write result lost original input")
    let second=ledger.begin(review:r,authorization:authorization)!;ledger.complete(second,outcome:.unknown)
    let otherContext=TaskDraftContext(business:202,epoch:2),otherAuth=SyntheticTaskCreateGrant(business:202,actor:9002,create:true).authorization(for:TaskDraftContext(business:202,epoch:2))!
    try expect(ledger.begin(review:review(otherContext),authorization:otherAuth) != nil && first.localID != second.localID && ledger.records.count==3,"One Business unknown globally blocked independent Business creation or reused identity")
    return count
}
