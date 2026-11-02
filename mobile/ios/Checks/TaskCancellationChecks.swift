import Foundation
import CRMCore

func runTaskCancellationChecks(directory: URL) throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let context=TaskCommentContext(business:101,task:1101,epoch:1),read=TaskCommentRead(context:TaskCommentContext(business:101,task:1101,epoch:1),revision:1)
    let grant=SyntheticTaskCancelGrant(business:101,task:1101,actor:9001,update:true),auth=grant.authorization(for:context)!
    try expect(SyntheticTaskCancelGrant(business:101,task:1101,actor:9001,update:false).authorization(for:context)==nil && grant.authorization(for:TaskCommentContext(business:202,task:1101,epoch:1))==nil,"Read/foreign Business implied cancellation UPDATE")
    var session=TaskCancelReasonSession();session.begin(read);session.receive(verified:true,status:"open",expected:read);_=session.open(expected:read);let selection=session.selection!,raw="  Manual reason\n";session.update(raw,expected:selection);_=session.prepare(expected:selection);let review=session.review!
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-cancel-outcome.json"))) as! [String:Any]
    for row in catalog["validation_cases"] as! [[String:Any]] {
        var ledger=TaskCancelAttemptLedger();let attempt=ledger.begin(review:review,raw:raw,status:"open",authorization:auth)!
        try expect(attempt.raw==raw && attempt.review.text=="Manual reason" && attempt.fromStatus=="open","Cancel lost immutable reason/origin")
        try expect(ledger.begin(review:review,raw:raw,status:"open",authorization:auth)==nil && !ledger.acknowledge(auth),"Pending cancel repeated/cleared")
        let task=try? JSONDecoder().decode(WorkTask.self,from:JSONSerialization.data(withJSONObject:row["response"]!))
        ledger.complete(attempt,outcome:task.map {.response(status:row["status"] as! Int,task:$0)} ?? .unknown)
        let expected: TaskCancelAttemptPhase = row["expected"] as! String == "confirmed" ? .confirmed:.unknown
        try expect(ledger.visible(auth)?.phase==expected,"Unverified cancel action became success: \(row["name"]!)")
        ledger.complete(attempt,outcome:.rejectedWithoutWrite);try expect(ledger.records[0].phase==expected,"Late terminal completion rewrote cancel result")
        if expected == .unknown {try expect(!ledger.acknowledge(auth) && ledger.begin(review:review,raw:raw,status:"open",authorization:auth)==nil,"Unknown cancellation replayed")}
    }
    var ledger=TaskCancelAttemptLedger()
    for status in ["done","cancelled","future_status",""] {try expect(ledger.begin(review:review,raw:raw,status:status,authorization:auth)==nil,"Closed/unknown status enabled cancellation attempt")}
    try expect(ledger.begin(review:review,raw:"bad other text",status:"open",authorization:auth)==nil,"Changed reason bypassed immutable preview")
    let first=ledger.begin(review:review,raw:raw,status:"in_progress",authorization:auth)!,otherEpoch=grant.authorization(for:TaskCommentContext(business:101,task:1101,epoch:2))!
    try expect(ledger.visible(otherEpoch)==nil && ledger.blocked(otherEpoch.context),"New epoch saw old attempt/replayed same target")
    ledger.complete(first,outcome:.rejectedWithoutWrite);try expect(ledger.acknowledge(auth) && ledger.records[0].attempt.raw==raw,"No-write acknowledgement lost original reason")
    let second=ledger.begin(review:review,raw:raw,status:"open",authorization:auth)!;ledger.complete(second,outcome:.unknown)
    try expect(first.localID != second.localID && ledger.records.count==2 && !ledger.acknowledge(auth),"New explicit attempt reused identity/unknown was acknowledged")
    return count
}
