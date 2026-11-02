import Foundation
import CRMCore

func runTaskAssignChecks(directory:URL) throws -> Int {
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-assign-outcome.json"))) as! [String:Any]
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    for row in catalog["input_cases"] as! [[String:Any]] {
        let raw=row["raw"] as! String,value=TaskAssignValue.parse(raw),expected=(row["user_id"] as? NSNumber)?.int64Value
        try expect(value?.userID==expected,"Assignment input \(row["name"]!)")
        try expect(value==nil || value?.raw==raw,"Assignment normalized raw target")
    }
    let rawProfile=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-101-1101.json"))) as! [String:Any],ctx=TaskCommentContext(business:101,task:1101,epoch:180)
    func source(_ status:String="open",epoch:Int=180,revision:Int=1) throws -> TaskAssignSource {
        var o=rawProfile,t=o["task"] as! [String:Any];t["status"]=status;o["task"]=t
        let d=try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:o))
        return TaskAssignSource(read:TaskCommentRead(context:TaskCommentContext(business:101,task:1101,epoch:epoch),revision:revision),task:d.task)
    }
    for row in catalog["validation_cases"] as! [[String:Any]] {
        let members=(row["eligible_members"] as! [NSNumber]).map(\.int64Value),grant=SyntheticTaskAssignGrant(business:101,task:1101,actor:9001,update:true,eligibleMembers:members),auth=grant.authorization(for:ctx)!,s=try source(row["source_status"] as! String),review=TaskAssignReview(source:s,visit:1,value:TaskAssignValue.parse(row["input"] as! String)!)
        var ledger=TaskAssignLedger();let attempt=ledger.begin(review,authorization:auth)!
        try expect(ledger.begin(review,authorization:auth)==nil,"Duplicate assignment attempt")
        ledger.complete(attempt,outcome:.response(status:row["status"] as! Int,data:try JSONSerialization.data(withJSONObject:row["response"]!)));let record=ledger.visible(auth)!,confirmed=row["expected"] as! String=="confirmed"
        try expect(record.phase == (confirmed ? .confirmed:.unknown),"Assignment result \(row["name"]!)")
        try expect(record.attempt.review==review,"Assignment source/raw target was lost")
        if confirmed {try expect(record.result?.assignee==review.value.userID && record.result?.status==s.task.status,"Assignment defaulted actor or changed source status")}
        ledger.complete(attempt,outcome:.rejectedWithoutWrite);try expect(ledger.visible(auth)==record,"Late assignment replaced terminal result")
        try expect(ledger.acknowledge(auth)==confirmed,"Unknown assignment acknowledged")
    }
    let s=try source(),grant=SyntheticTaskAssignGrant(business:101,task:1101,actor:9001,update:true,eligibleMembers:[9003,9001]),auth=grant.authorization(for:ctx)!
    let invalidMembers:[[Int64]]=[[],[0],[-1],[9003,9003]]
    for members in invalidMembers {try expect(SyntheticTaskAssignGrant(business:101,task:1101,actor:9001,update:true,eligibleMembers:members).authorization(for:ctx)==nil,"Invalid synthetic member context accepted")}
    try expect(SyntheticTaskAssignGrant(business:101,task:1101,actor:9001,update:false,eligibleMembers:[9003]).authorization(for:ctx)==nil,"GET member granted UPDATE")
    try expect(grant.authorization(for:TaskCommentContext(business:202,task:1101,epoch:180))==nil,"Assignment context crossed Business")
    var ledger=TaskAssignLedger();try expect(ledger.begin(TaskAssignReview(source:s,visit:1,value:TaskAssignValue.parse("9999")!),authorization:auth)==nil,"Unconfigured synthetic target accepted")
    for status in ["done","cancelled","unknown",""] {let bad=try source(status);try expect(bad.identityValid && !bad.valid && ledger.begin(TaskAssignReview(source:bad,visit:1,value:TaskAssignValue.parse("9003")!),authorization:auth)==nil,"Assignment accepted terminal/unknown status")}
    let attempt=ledger.begin(TaskAssignReview(source:s,visit:1,value:TaskAssignValue.parse("9003")!),authorization:auth)!;ledger.complete(attempt,outcome:.unknown)
    let newer=try source(epoch:181,revision:2),newAuth=grant.authorization(for:newer.read.context)!
    try expect(ledger.blocked(newer.read.context) && ledger.visible(newAuth)==nil && !ledger.acknowledge(newAuth),"Assignment new epoch/reread proved result")
    try expect(ledger.records[0].attempt.review.value.raw=="9003","Unknown assignment lost exact target")
    return count
}
