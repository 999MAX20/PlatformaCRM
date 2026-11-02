import Foundation
import CRMCore

func runTaskCommentSubmissionChecks(directory: URL) throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let context=TaskCommentContext(business:101,task:1101,epoch:1),read=TaskCommentRead(context:TaskCommentContext(business:101,task:1101,epoch:1),revision:1)
    let grant=SyntheticTaskCommentGrant(business:101,task:1101,actor:9001,update:true),auth=grant.authorization(for:context)!
    try expect(SyntheticTaskCommentGrant(business:101,task:1101,actor:9001,update:false).authorization(for:context)==nil,"VIEW implied UPDATE")
    try expect(grant.authorization(for:TaskCommentContext(business:202,task:1101,epoch:1))==nil && grant.authorization(for:TaskCommentContext(business:101,task:1101,epoch:0))==nil,"Invalid scope/epoch acquired synthetic UPDATE")
    var draft=TaskCommentSession();draft.begin(read);draft.receive(verified:true,expected:read);_=draft.open(expected:read);let selection=draft.selection!
    let raw="  Manual comment\n";draft.update(raw,expected:selection);_=draft.prepare(expected:selection);let review=draft.review!
    let root=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-comment-submit.json"))) as! [String:Any]
    for row in root["validation_cases"] as! [[String:Any]] {
        var ledger=TaskCommentAttemptLedger();let attempt=ledger.begin(review:review,raw:raw,authorization:auth)!
        try expect(attempt.raw==raw && attempt.text=="Manual comment" && ledger.records[0].phase == .pending,"Attempt did not retain immutable exact input")
        try expect(ledger.begin(review:review,raw:raw,authorization:auth)==nil,"Double-click created second attempt")
        let comment=try? JSONDecoder().decode(TaskComment.self,from:JSONSerialization.data(withJSONObject:row["response"]!))
        let outcome=comment.map {SyntheticTaskCommentOutcome.response(status:row["status"] as! Int,comment:$0)} ?? .unknown
        ledger.complete(attempt,outcome:outcome)
        let expected: TaskCommentAttemptPhase = row["expected"] as! String == "confirmed" ? .confirmed : .unknown
        try expect(ledger.visible(auth)?.phase==expected,"Mismatched action payload became success: \(row["name"]!)")
        ledger.complete(attempt,outcome:.rejectedWithoutWrite)
        try expect(ledger.records[0].phase==expected,"Duplicate completion rewrote a terminal result")
        if expected == .unknown {try expect(!ledger.acknowledge(auth) && ledger.begin(review:review,raw:raw,authorization:auth)==nil,"Unknown attempt released for blind replay")}
    }
    var ledger=TaskCommentAttemptLedger();try expect(ledger.begin(review:review,raw:"different",authorization:auth)==nil,"Review/raw mismatch submitted")
    let attempt=ledger.begin(review:review,raw:raw,authorization:auth)!
    try expect(!ledger.acknowledge(auth),"Pending attempt cleared")
    let otherEpoch=grant.authorization(for:TaskCommentContext(business:101,task:1101,epoch:2))!
    try expect(ledger.visible(otherEpoch)==nil && ledger.blocked(otherEpoch.context),"New epoch inherited result or enabled blind replay")
    ledger.complete(attempt,outcome:.rejectedWithoutWrite)
    try expect(ledger.acknowledge(auth) && ledger.records[0].attempt.raw==raw,"Definitive no-write recovery erased audit input")
    let second=ledger.begin(review:review,raw:raw,authorization:auth)!
    try expect(second.localID != attempt.localID && ledger.records.count==2,"New explicit attempt reused old correlation identity")
    ledger.complete(second,outcome:.unknown)
    try expect(ledger.blocked(context) && ledger.records.allSatisfy {$0.attempt.raw==raw},"Unknown lost earlier attempts/raw")
    // A bounded reread with matching text has no method that can acknowledge this ledger.
    let detail=try JSONDecoder().decode(TaskDetails.self,from:Data(contentsOf:directory.appendingPathComponent("task-101-1101.json")))
    try expect(detail.valid(for:101,id:1101) && ledger.visible(auth)?.phase == .unknown,"Read projection changed command outcome")
    count += try runTaskCommentExactTextChecks(directory:directory)
    return count
}

private func runTaskCommentExactTextChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let read=TaskCommentRead(context:TaskCommentContext(business:101,task:1101,epoch:1),revision:1),grant=SyntheticTaskCommentGrant(business:101,task:1101,actor:9001,update:true)
    let auth=grant.authorization(for:read.context)!,cases=(try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-comment-exact-text-cases.json"))) as! [String:Any])["cases"] as! [[String:Any]]
    func reviewed(_ raw:String)->TaskCommentReview {var d=TaskCommentSession();d.begin(read);d.receive(verified:true,expected:read);_=d.open(expected:read);d.update(raw,expected:d.selection!);_=d.prepare(expected:d.selection!);return d.review!}
    for row in cases {
        let before=row["before"] as! String,after=row["after"] as! String,changed=row["changed"] as! Bool,a=reviewed(before),b=reviewed(after)
        try expect(a.text.utf8.elementsEqual((row["before_preview"] as! String).utf8) && b.text.utf8.elementsEqual((row["after_preview"] as! String).utf8),"Task comment source trim changed or normalized raw text")
        try expect((a != b)==changed && a.selection==b.selection,"Review equated byte-different comment text")
        var mismatch=TaskCommentAttemptLedger();try expect((mismatch.begin(review:a,raw:after,authorization:auth)==nil)==changed,"Canonical raw/review mismatch began comment attempt")
        var ledger=TaskCommentAttemptLedger(),other=TaskCommentAttemptLedger();let attempt=ledger.begin(review:a,raw:before,authorization:auth)!,alternate=other.begin(review:b,raw:after,authorization:auth)!
        try expect((attempt != alternate)==changed && attempt.raw.utf8.elementsEqual(before.utf8),"Retained attempt identity lost exact raw/text")
        let echo=try JSONDecoder().decode(TaskComment.self,from:Data((row["after_response_json"] as! String).utf8)),exact=try JSONDecoder().decode(TaskComment.self,from:Data((row["before_response_json"] as! String).utf8))
        ledger.complete(attempt,outcome:.response(status:201,comment:echo));let phase:TaskCommentAttemptPhase=changed ? .unknown:.confirmed
        try expect(ledger.visible(auth)?.phase==phase && ledger.records[0].attempt==attempt,"Byte-different typed201 echo confirmed or lost retained attempt")
        if changed {
            try expect(!ledger.acknowledge(auth) && ledger.begin(review:a,raw:before,authorization:auth)==nil,"Unknown text mismatch released acknowledge/replay")
            ledger.complete(attempt,outcome:.response(status:201,comment:exact));try expect(ledger.visible(auth)?.phase == .unknown,"Later exact text changed terminal unknown outcome")
            var source=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-101-1101.json"))) as! [String:Any],comments=source["comments"] as! [[String:Any]];comments[0]["text"]=a.text;source["comments"]=comments
            let reread=try TaskDetails.decodeSource(JSONSerialization.data(withJSONObject:source));try expect(reread.valid(for:101,id:1101) && reread.comments.first?.text?.utf8.elementsEqual(a.text.utf8)==true && ledger.visible(auth)?.phase == .unknown,"Matching bounded GET text was promoted to comment outcome proof")
        }
        var positive=TaskCommentAttemptLedger();let exactAttempt=positive.begin(review:a,raw:before,authorization:auth)!;positive.complete(exactAttempt,outcome:.response(status:201,comment:exact))
        try expect(positive.visible(auth)?.phase == .confirmed && positive.visible(auth)?.comment?.text?.utf8.elementsEqual(a.text.utf8)==true,"Exact typed201 positive receipt failed existing field/actor/status guards")
        try expect(positive.acknowledge(auth) && positive.records[0].attempt.raw.utf8.elementsEqual(before.utf8),"Explicit positive acknowledge lost retained exact input")
    }
    return count
}
