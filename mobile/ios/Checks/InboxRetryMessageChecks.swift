import Foundation
import CRMCore

func runInboxRetryMessageChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("inbox-retry-message.json"))) as! [String:Any]
    func context(_ c:[String:Int])->InboxMessageFilesContext {InboxMessageFilesContext(business:c["business"]!,conversation:c["conversation"]!,message:c["message"]!,epoch:c["epoch"]!,revision:c["revision"]!,limit:c["limit"]!)}
    for row in catalog["source_cases"] as! [[String:Any]] {
        let c=context(row["context"] as! [String:Int]),s=InboxRetryMessageSource.decode(Data((row["response_json"] as! String).utf8),context:c)
        try expect((s != nil)==row["valid"] as! Bool,"Retry source strict generic shape: \(row["name"]!)")
        if let s {try expect(s.valid && s.context==c && s.eligible==row["eligible"] as! Bool,"Retry source eligibility/default/non-sent policy changed");try expect(Mirror(reflecting:s).children.count==5,"Retry source retained provider/payload/URL state")}
    }
    let c=context(catalog["context"] as! [String:Int]),source=InboxRetryMessageSource.decode(Data((catalog["source_json"] as! String).utf8),context:c)!,port=FixtureInboxRetryPort(directory:directory),owner=InboxRetryOwner(business:101,conversation:901,epoch:1),auth=port.grants.first!.authorization(for:owner)!,review=InboxRetryReview(source:source,authorization:auth,visit:1)
    for row in catalog["receipt_cases"] as! [[String:Any]] {
        let s=InboxRetryMessageSource.decode(Data((row["source_json"] as! String).utf8),context:c)!,result=InboxRetryReceipt.decode(Data((row["response_json"] as! String).utf8),source:s)
        try expect((result != nil)==row["valid"] as! Bool,"Plain generic201 retry receipt scope/raw/link: \(row["name"]!)")
        if let result {try expect(result.id != s.context.message && result.retryOf==s.context.message && result.conversation==s.context.conversation && result.text.utf8.elementsEqual(s.text.utf8),"Receipt changed original/raw relation");try expect(Mirror(reflecting:result).children.count==8,"Receipt retained provider/error/payload extras")}
    }
    var ledger=InboxRetryLedger();let attempt=ledger.begin(review)!
    let body=try JSONSerialization.jsonObject(with:attempt.preparedBody()) as! [String:Int]
    try expect(body==["message_id":9012] && attempt.headers.isEmpty && attempt.query.isEmpty && attempt.path=="/api/inbox/conversations/901/retry-message/","Retry invented business/header/key/envelope or changed exact body")
    try expect(ledger.records.count==1 && ledger.records[0].phase == .pending && ledger.begin(review)==nil,"Pending retry repeated or failed to retain original attempt")
    let pending=ledger.visible(auth)!;try expect(!ledger.acknowledge(auth,record:pending),"Pending retry acknowledged")
    let outcome=try await port.execute(attempt);ledger.complete(attempt,outcome:outcome);let response=ledger.visible(auth)!
    try expect(response.phase == .response && response.result?.id==9901 && response.attempt==attempt,"Fixture201 not retained as explicit synthetic response")
    ledger.complete(attempt,outcome:.unknown);try expect(ledger.visible(auth)==response,"Late duplicate completion rewrote known retry result")
    try expect(ledger.acknowledge(auth,record:response) && !ledger.blocked(business:101,conversation:901) && ledger.records.count==1,"Known local acknowledgement lost history or retained active barrier")
    let second=ledger.begin(review)!;try expect(second.localID != attempt.localID && second.preparedBody()==attempt.preparedBody(),"Fresh explicit review invented wire key or lost exact original selector")
    ledger.complete(second,outcome:.unknown);let unknown=ledger.visible(auth)!;try expect(!ledger.acknowledge(auth,record:unknown) && ledger.begin(review)==nil && unknown.attempt.review.source==source,"Unknown retry released/repeated or lost original selection/input")
    let nextOwner=InboxRetryOwner(business:101,conversation:901,epoch:2),nextAuth=port.grants.first!.authorization(for:nextOwner)!,nextContext=InboxMessageFilesContext(business:101,conversation:901,message:9012,epoch:2,revision:2,limit:30),reread=InboxRetryMessageSource.decode(Data((catalog["source_json"] as! String).utf8),context:nextContext)!,nextReview=InboxRetryReview(source:reread,authorization:nextAuth,visit:2)
    try expect(ledger.visible(nextAuth)==unknown && ledger.begin(nextReview)==nil && ledger.records[1].attempt==second,"Owner visit/matching reread proved own unknown retry outcome or rebound frozen source")
    let actor=SyntheticInboxRetryGrant(business:101,conversation:901,actor:6002,update:true).authorization(for:nextOwner)!
    try expect(ledger.visible(actor)==nil && ledger.blocked(business:101,conversation:901) && ledger.begin(InboxRetryReview(source:reread,authorization:actor,visit:3))==nil,"Changing actor revealed original input or bypassed active unknown")
    var otherObject=try JSONSerialization.jsonObject(with:Data((catalog["source_json"] as! String).utf8)) as! [String:Any];otherObject["id"]=9011
    let otherContext=InboxMessageFilesContext(business:101,conversation:901,message:9011,epoch:2,revision:2,limit:30),other=InboxRetryMessageSource.decode(try JSONSerialization.data(withJSONObject:otherObject),context:otherContext)!
    try expect(ledger.begin(InboxRetryReview(source:other,authorization:nextAuth,visit:4))==nil,"Another selected message bypassed conversation unknown barrier")
    try expect(!ledger.blocked(business:202,conversation:951) && ledger.records[1].attempt.preparedBody()==second.preparedBody(),"Unknown retry crossed Business or changed frozen body")
    for grant in [SyntheticInboxRetryGrant(business:101,conversation:901,actor:5001,update:false),SyntheticInboxRetryGrant(business:202,conversation:901,actor:5001,update:true),SyntheticInboxRetryGrant(business:101,conversation:951,actor:5001,update:true),SyntheticInboxRetryGrant(business:101,conversation:901,actor:0,update:true)] {try expect(grant.authorization(for:owner)==nil,"GET/scope/actor created synthetic UPDATE")}
    var rejected=InboxRetryLedger();let a=rejected.begin(review)!;rejected.complete(a,outcome:.rejectedWithoutWrite);let record=rejected.visible(auth)!;try expect(record.phase == .rejected && rejected.acknowledge(auth,record:record) && rejected.records.count==1,"Explicit no-write rejection lost input or invented send success")
    let raw=(catalog["scenarios"] as! [[String:Any]])[0]["response_json"] as! String
    for status in [200,400,403,500] {var l=InboxRetryLedger();let a=l.begin(review)!;l.complete(a,outcome:.response(status:status,data:Data(raw.utf8)));let r=l.visible(auth)!;try expect(r.phase == .unknown && !l.acknowledge(auth,record:r) && l.begin(review)==nil,"Unexpected status inferred no-write/result or safe retry")}
    for row in (catalog["receipt_cases"] as! [[String:Any]]).filter({!($0["valid"] as! Bool)}) {
        var l=InboxRetryLedger();let a=l.begin(review)!;l.complete(a,outcome:.response(status:201,data:Data((row["response_json"] as! String).utf8)))
        // A case with a deliberately ineligible source still uses a valid original here; only shape/raw-invalid receipts must quarantine.
        if row["name"] as! String != "ineligible_source_sent" {try expect(l.visible(auth)?.phase == .unknown && l.records[0].attempt==a,"Malformed201 released unknown or changed attempted input")}
    }
    let read=APIInboxMessageFilesRepository(transport:FixtureInboxRetryReadTransport(directory:directory)),anchor=try await read.anchor(c),window=try await read.messages(c,anchor:anchor)
    try expect(window.retrySource==source && window.retrySource?.status=="failed" && window.observation.state == .failed,"Separate fixture GET did not supply exact independent generic source")
    return count
}
