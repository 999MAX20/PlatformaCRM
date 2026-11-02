import Foundation
import CRMCore

func runInboxReadMarkerChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    guard let fixtureData=try? Data(contentsOf:directory.appendingPathComponent("inbox-read-markers.json")),
          let d=(try? JSONSerialization.jsonObject(with:fixtureData)) as? [String:Any],
          d["fixture_only"] as? Bool == true,
          d["source_cases"] is [[String:Any]], d["receipt_cases"] is [[String:Any]],
          let fixtureContext=d["context"] as? [String:Int],
          ["business","conversation","epoch","revision"].allSatisfy({fixtureContext[$0] != nil}),
          let fixtureSourceJSON=d["source_json"] as? String
    else {throw CheckFailure(message:"Missing or invalid fixture envelope: inbox-read-markers.json")}
    func context(_ v:[String:Int])->InboxConversationFilesContext {InboxConversationFilesContext(business:v["business"]!,conversation:v["conversation"]!,epoch:v["epoch"]!,revision:v["revision"]!)}
    for row in d["source_cases"] as! [[String:Any]] {let c=context(row["context"] as! [String:Int]),s=InboxReadMarkerSource.decode(Data((row["response_json"] as! String).utf8),context:c);try expect((s != nil)==row["valid"] as! Bool,"Strict generic unread source \(row["name"]!)");if let s {try expect(s.valid && s.context==c && Mirror(reflecting:s).children.count==3,"Read marker source retained permission/default date/metadata")}}
    let c=context(fixtureContext)
    guard let s=InboxReadMarkerSource.decode(Data(fixtureSourceJSON.utf8),context:c)
    else {throw CheckFailure(message:"Invalid source fixture: inbox-read-markers.json")}
    let port=FixtureInboxReadMarkerPort(directory:directory)
    func fixtureAuthorization(_ owner:InboxConversationFilesContext) throws -> SyntheticInboxReadMarkerAuthorization {
        guard let grant=port.grants.first,let authorization=grant.authorization(for:owner)
        else {throw CheckFailure(message:"Missing, invalid or unauthorized fixture grants: inbox-read-markers.json")}
        return authorization
    }
    let auth=try fixtureAuthorization(c)
    var ledger=InboxReadMarkerLedger()
    for action in [InboxReadMarkerAction.read,.unread] {
        let review=InboxReadMarkerReview(source:s,authorization:auth,action:action,visit:1),a=ledger.begin(review)!
        try expect(a.path=="/api/inbox/conversations/901/\(action.rawValue)/" && a.preparedBody()==Data("{}".utf8) && a.headers.isEmpty && a.query.isEmpty,"Marker invented body/key/version/query")
        try expect(ledger.begin(review)==nil && !ledger.acknowledge(auth,record:ledger.visible(auth)!),"Pending repeated/acknowledged")
        ledger.complete(a,outcome:try await port.execute(a));let result=ledger.visible(auth)!
        try expect(result.phase == .response && result.attempt.review.action==action && result.attempt.review.source.unreadCount==7 && result.result?.source.unreadCount==(action == .read ? 0:1),"Fixture result changed original input or inferred max from stale source7")
        ledger.complete(a,outcome:.unknown);try expect(ledger.visible(auth)==result && ledger.acknowledge(auth,record:result),"Late completion or known acknowledgement lost immutable attempt")
    }
    for row in d["receipt_cases"] as! [[String:Any]] {
        let action=InboxReadMarkerAction(rawValue:row["action"] as! String)!,review=InboxReadMarkerReview(source:s,authorization:auth,action:action,visit:2);var l=InboxReadMarkerLedger();let a=l.begin(review)!,r=InboxReadMarkerReceipt.decode(Data((row["response_json"] as! String).utf8),attempt:a)
        try expect((r != nil)==row["valid"] as! Bool,"Plain200 marker projection \(row["name"]!)")
        l.complete(a,outcome:.response(status:200,data:Data((row["response_json"] as! String).utf8)))
        try expect(l.visible(auth)?.phase == (r==nil ? .unknown:.response) && l.records[0].attempt==a,"Malformed200 or synthetic result rewrote original/phase")
    }
    let original=InboxReadMarkerReview(source:s,authorization:auth,action:.read,visit:3),unknownAttempt=ledger.begin(original)!;ledger.complete(unknownAttempt,outcome:.unknown);let unknown=ledger.visible(auth)!
    let next=InboxConversationFilesContext(business:101,conversation:901,epoch:2,revision:2),na=try fixtureAuthorization(next),matching=InboxReadMarkerSource.decode(Data((d["read_response_json"] as! String).utf8),context:next)!
    try expect(!ledger.acknowledge(auth,record:unknown) && ledger.visible(na)==unknown && ledger.begin(InboxReadMarkerReview(source:matching,authorization:na,action:.unread,visit:4))==nil && ledger.records.last?.attempt==unknownAttempt,"Matching0 read/opposite action/epoch released unknown or rebound input")
    let other=SyntheticInboxReadMarkerGrant(business:101,conversation:901,actor:6002,update:true).authorization(for:next)!
    try expect(ledger.visible(other)==nil && ledger.blocked(business:101,conversation:901) && ledger.begin(InboxReadMarkerReview(source:matching,authorization:other,action:.read,visit:5))==nil && !ledger.blocked(business:202,conversation:951),"Actor/Business changed unknown barrier/visibility")
    for g in [SyntheticInboxReadMarkerGrant(business:101,conversation:901,actor:5001,update:false),SyntheticInboxReadMarkerGrant(business:202,conversation:901,actor:5001,update:true),SyntheticInboxReadMarkerGrant(business:101,conversation:951,actor:5001,update:true),SyntheticInboxReadMarkerGrant(business:101,conversation:901,actor:0,update:true)] {try expect(g.authorization(for:c)==nil,"GET/MANAGE/invalid actor invented separate UPDATE")}
    for status in [201,400,403,409,500] {var l=InboxReadMarkerLedger();let a=l.begin(original)!;l.complete(a,outcome:.response(status:status,data:Data((d["read_response_json"] as! String).utf8)));try expect(l.visible(auth)?.phase == .unknown && !l.acknowledge(auth,record:l.visible(auth)!),"Unexpected status inferred safe rejection/repetition")}
    var rejected=InboxReadMarkerLedger();let ra=rejected.begin(original)!;rejected.complete(ra,outcome:.rejectedWithoutWrite);let rr=rejected.visible(auth)!;try expect(rr.phase == .rejected && rejected.acknowledge(auth,record:rr) && rejected.records.count==1,"Explicit no-write rejection lost attempt/history")
    let raw1=Data("{\"id\":901,\"business\":101,\"unread_count\":7,\"updated_at\":\"é\"}".utf8),raw2=Data("{\"id\":901,\"business\":101,\"unread_count\":7,\"updated_at\":\"é\"}".utf8);try expect(InboxReadMarkerSource.decode(raw1,context:c) != InboxReadMarkerSource.decode(raw2,context:c),"Raw update date canonically normalized")
    let repository=APIInboxReadMarkerRepository(transport:FixtureInboxReadMarkerReadTransport(directory:directory));try expect(try await repository.source(c)==s,"Independent generic read adapter")
    return count
}
