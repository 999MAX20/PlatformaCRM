import Foundation
import CRMCore

func runInboxSelfAssignmentChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let d=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("inbox-self-assignment.json"))) as! [String:Any]
    func context(_ v:[String:Int])->InboxConversationFilesContext {InboxConversationFilesContext(business:v["business"]!,conversation:v["conversation"]!,epoch:v["epoch"]!,revision:v["revision"]!)}
    for row in d["source_cases"] as! [[String:Any]] {let c=context(row["context"] as! [String:Int]),s=InboxSelfAssignmentSource.decode(Data((row["response_json"] as! String).utf8),context:c);try expect((s != nil)==row["valid"] as! Bool,"Strict raw self source \(row["name"]!)");if let s {try expect(s.context==c && Mirror(reflecting:s).children.count==3,"Source retained metadata/authority or default date")}}
    let c=context(d["context"] as! [String:Int]),s=InboxSelfAssignmentSource.decode(Data((d["source_json"] as! String).utf8),context:c)!,port=FixtureInboxSelfAssignmentPort(directory:directory),auth=port.grants[0].authorization(for:c)!,review=InboxSelfAssignmentReview(source:s,authorization:auth,visit:1)
    var ledger=InboxSelfAssignmentLedger();let a=ledger.begin(review)!
    try expect(a.path=="/api/inbox/conversations/901/assign/" && a.preparedBody()==Data("{}".utf8) && a.headers.isEmpty && a.query.isEmpty,"Self subset invented wire user_id/Business/key/version")
    for row in d["receipt_cases"] as! [[String:Any]] {let r=InboxSelfAssignmentReceipt.decode(Data((row["response_json"] as! String).utf8),attempt:a);try expect((r != nil)==row["valid"] as! Bool,"Plain200 scope/actor receipt \(row["name"]!)");if let r {try expect(r.source.context==c && r.source.assignedTo==5001 && Mirror(reflecting:r).children.count==1,"Receipt retained nonprojection data")}}
    try expect(ledger.begin(review)==nil && !ledger.acknowledge(auth,record:ledger.visible(auth)!),"Pending duplicate or acknowledge")
    ledger.complete(a,outcome:try await port.execute(a));let response=ledger.visible(auth)!
    try expect(response.phase == .response && response.result?.source.assignedTo==5001 && response.attempt.review.source.assignedTo==nil,"Fixture result rewrote original source")
    ledger.complete(a,outcome:.unknown);try expect(ledger.visible(auth)==response && ledger.acknowledge(auth,record:response) && ledger.records.count==1,"Late completion or known acknowledgement erased history")
    let second=ledger.begin(review)!;ledger.complete(second,outcome:.unknown);let unknown=ledger.visible(auth)!
    try expect(ledger.begin(review)==nil && !ledger.acknowledge(auth,record:unknown) && second.preparedBody()==Data("{}".utf8),"Unknown repeated or discarded original body")
    let next=InboxConversationFilesContext(business:101,conversation:901,epoch:2,revision:2),nextAuth=port.grants[0].authorization(for:next)!,matching=InboxSelfAssignmentSource.decode(Data((d["response_json"] as! String).utf8),context:next)!
    try expect(ledger.visible(nextAuth)==unknown && ledger.begin(InboxSelfAssignmentReview(source:matching,authorization:nextAuth,visit:2))==nil && ledger.records[1].attempt==second,"Matching assigned_to reread proved own attempt or rebound old read")
    let other=SyntheticInboxSelfAssignmentGrant(business:101,conversation:901,actor:6002,manage:true,activeMember:true).authorization(for:next)!
    try expect(ledger.visible(other)==nil && ledger.blocked(business:101,conversation:901) && ledger.begin(InboxSelfAssignmentReview(source:matching,authorization:other,visit:3))==nil && !ledger.blocked(business:202,conversation:951),"Actor/Business isolation or conversation barrier")
    for g in [SyntheticInboxSelfAssignmentGrant(business:101,conversation:901,actor:5001,manage:false,activeMember:true),SyntheticInboxSelfAssignmentGrant(business:101,conversation:901,actor:5001,manage:true,activeMember:false),SyntheticInboxSelfAssignmentGrant(business:202,conversation:901,actor:5001,manage:true,activeMember:true),SyntheticInboxSelfAssignmentGrant(business:101,conversation:951,actor:5001,manage:true,activeMember:true),SyntheticInboxSelfAssignmentGrant(business:101,conversation:901,actor:0,manage:true,activeMember:true)] {try expect(g.authorization(for:c)==nil,"GET/UPDATE/no membership minted MANAGE authority")}
    for status in [201,400,403,409,500] {var l=InboxSelfAssignmentLedger();let a=l.begin(review)!;l.complete(a,outcome:.response(status:status,data:Data((d["response_json"] as! String).utf8)));try expect(l.visible(auth)?.phase == .unknown && !l.acknowledge(auth,record:l.visible(auth)!),"Unexpected status inferred safe no-write/result")}
    for row in (d["receipt_cases"] as! [[String:Any]]).filter({!($0["valid"] as! Bool)}) {var l=InboxSelfAssignmentLedger();let a=l.begin(review)!;l.complete(a,outcome:.response(status:200,data:Data((row["response_json"] as! String).utf8)));try expect(l.visible(auth)?.phase == .unknown && l.records[0].attempt==a,"Malformed200 changed immutable input or released barrier")}
    var rejected=InboxSelfAssignmentLedger();let ra=rejected.begin(review)!;rejected.complete(ra,outcome:.rejectedWithoutWrite);let record=rejected.visible(auth)!;try expect(record.phase == .rejected && rejected.acknowledge(auth,record:record) && rejected.records.count==1,"Explicit no-write rejection lost history")
    let raw1=Data("{\"id\":901,\"business\":101,\"assigned_to\":null,\"updated_at\":\"é\"}".utf8),raw2=Data("{\"id\":901,\"business\":101,\"assigned_to\":null,\"updated_at\":\"é\"}".utf8)
    try expect(InboxSelfAssignmentSource.decode(raw1,context:c) != InboxSelfAssignmentSource.decode(raw2,context:c),"Raw observations canonically normalized")
    let repository=APIInboxSelfAssignmentRepository(transport:FixtureInboxSelfAssignmentReadTransport(directory:directory));try expect(try await repository.source(c)==s,"Independent generic GET source")
    return count
}
