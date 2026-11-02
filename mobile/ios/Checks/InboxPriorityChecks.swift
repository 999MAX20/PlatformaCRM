import Foundation
import CRMCore
func runInboxPriorityChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ v:Bool,_ m:String) throws {guard v else {throw CheckFailure(message:m)};count += 1}
    guard let fixtureData=try? Data(contentsOf:directory.appendingPathComponent("inbox-priority.json")),
          let d=(try? JSONSerialization.jsonObject(with:fixtureData)) as? [String:Any],
          d["fixture_only"] as? Bool == true,
          d["source_cases"] is [[String:Any]], d["receipt_cases"] is [[String:Any]],
          let fixtureContext=d["context"] as? [String:Int],
          ["business","conversation","epoch","revision"].allSatisfy({fixtureContext[$0] != nil}),
          let fixtureSourceJSON=d["source_json"] as? String
    else {throw CheckFailure(message:"Missing or invalid fixture envelope: inbox-priority.json")}
    func context(_ v:[String:Int])->InboxConversationFilesContext {InboxConversationFilesContext(business:v["business"]!,conversation:v["conversation"]!,epoch:v["epoch"]!,revision:v["revision"]!)}
    for row in d["source_cases"] as! [[String:Any]] {let s=InboxPrioritySource.decode(Data((row["response_json"] as! String).utf8),context:context(row["context"] as! [String:Int]));try expect((s != nil)==row["valid"] as! Bool,"Priority raw source \(row["name"]!)");if let s {try expect(s.valid && Mirror(reflecting:s).children.count==3,"Priority source retained authority/version/metadata")}}
    let c=context(fixtureContext)
    guard let s=InboxPrioritySource.decode(Data(fixtureSourceJSON.utf8),context:c)
    else {throw CheckFailure(message:"Invalid source fixture: inbox-priority.json")}
    let port=FixtureInboxPriorityPort(directory:directory)
    func fixtureAuthorization(_ owner:InboxConversationFilesContext) throws -> SyntheticInboxPriorityAuthorization {
        guard let grant=port.grants.first,let authorization=grant.authorization(for:owner)
        else {throw CheckFailure(message:"Missing, invalid or unauthorized fixture grants: inbox-priority.json")}
        return authorization
    }
    let auth=try fixtureAuthorization(c)
    for row in d["receipt_cases"] as! [[String:Any]] {let value=InboxPriorityValue(rawValue:row["priority"] as! String)!;var l=InboxPriorityLedger();let a=l.begin(InboxPriorityReview(source:s,authorization:auth,value:value,visit:1))!,r=InboxPriorityReceipt.decode(Data((row["response_json"] as! String).utf8),attempt:a);try expect((r != nil)==row["valid"] as! Bool,"Priority plain200 scope/value \(row["name"]!)");l.complete(a,outcome:.response(status:200,data:Data((row["response_json"] as! String).utf8)));try expect(l.visible(auth)?.phase == (r==nil ? .unknown:.response) && l.records[0].attempt==a,"Malformed200 changed original choice or released unknown")}
    for value in InboxPriorityValue.allCases {var l=InboxPriorityLedger();let review=InboxPriorityReview(source:s,authorization:auth,value:value,visit:2),a=l.begin(review)!,body=try JSONSerialization.jsonObject(with:a.preparedBody()) as! [String:String];try expect(body==["priority":value.rawValue] && a.query.isEmpty && a.headers.isEmpty && a.path=="/api/inbox/conversations/901/set-priority/","Priority invented wire fields/header/query/key");try expect(l.begin(review)==nil && !l.acknowledge(auth,record:l.visible(auth)!),"Pending priority repeated or acknowledged");l.complete(a,outcome:try await port.execute(a));let r=l.visible(auth)!;try expect(r.phase == .response && r.result?.source.priority==value.rawValue && r.attempt.review.source==s && l.acknowledge(auth,record:r),"Known fake priority mutated original or lost explicit ack")}
    var l=InboxPriorityLedger();let review=InboxPriorityReview(source:s,authorization:auth,value:.high,visit:3),a=l.begin(review)!;l.complete(a,outcome:.unknown);let unknown=l.visible(auth)!,next=InboxConversationFilesContext(business:101,conversation:901,epoch:2,revision:2),na=try fixtureAuthorization(next)
    let matching=InboxPrioritySource.decode(Data("{\"id\":901,\"business\":101,\"priority\":\"high\",\"updated_at\":\"synthetic raw update\"}".utf8),context:next)!
    try expect(l.visible(na)==unknown && !l.acknowledge(na,record:unknown) && l.begin(InboxPriorityReview(source:matching,authorization:na,value:.low,visit:4))==nil && l.records[0].attempt==a,"Matching priority/GET/opposite choice recovered unknown")
    let other=SyntheticInboxPriorityGrant(business:101,conversation:901,actor:6002,update:true).authorization(for:next)!;try expect(l.visible(other)==nil && l.blocked(business:101,conversation:901) && !l.blocked(business:202,conversation:951),"Priority actor/Business isolation")
    for g in [SyntheticInboxPriorityGrant(business:101,conversation:901,actor:5001,update:false),SyntheticInboxPriorityGrant(business:202,conversation:901,actor:5001,update:true),SyntheticInboxPriorityGrant(business:101,conversation:951,actor:5001,update:true),SyntheticInboxPriorityGrant(business:101,conversation:901,actor:0,update:true)] {try expect(g.authorization(for:c)==nil,"GET/other grant minted priority authority")}
    for status in [201,400,403,409,500] {var x=InboxPriorityLedger();let a=x.begin(review)!;x.complete(a,outcome:.response(status:status,data:Data("{}".utf8)));try expect(x.visible(auth)?.phase == .unknown && !x.acknowledge(auth,record:x.visible(auth)!),"Unexpected priority response inferred safe repetition")}
    return count
}
