import Foundation
import CRMCore

func runClientCreationChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let context=ClientDraftContext(business:101,epoch:1),grant=SyntheticClientCreateGrant(business:101,actor:9001,create:true),authorization=SyntheticClientCreateGrant(business:101,actor:9001,create:true).authorization(for:ClientDraftContext(business:101,epoch:1))!
    func review(_ context:ClientDraftContext,notes:String="  Manual notes\n")->ClientDraftReview {var s=ClientDraftSession();s.bind(context);_=s.open(expected:context);let token=s.selection!;for (field,text) in [(ClientDraftField.fullName,"  Manual client\n"),(.phone,"  +7 123\n"),(.email,"alpha@example.invalid"),(.notes,notes)] {s.update(field,value:text,expected:token)};_=s.prepare(expected:token);return s.review!}
    let r=review(context)
    try expect(SyntheticClientCreateGrant(business:101,actor:9001,create:false).authorization(for:context)==nil && grant.authorization(for:ClientDraftContext(business:202,epoch:1))==nil && grant.authorization(for:ClientDraftContext(business:101,epoch:0))==nil,"VIEW/UPDATE/invalid scope granted Client CREATE")
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("client-create-outcome.json"))) as! [String:Any]
    for row in catalog["validation_cases"] as! [[String:Any]] {
        var ledger=ClientCreateAttemptLedger();let a=ledger.begin(review:r,authorization:authorization)!
        try expect(a.review.values.fullName=="  Manual client\n" && a.review.preview.fullName=="Manual client","Client create lost raw/normalized snapshot")
        try expect(ledger.begin(review:r,authorization:authorization)==nil && !ledger.acknowledge(authorization),"Pending Client create repeated/cleared")
        let client=try? JSONDecoder().decode(ClientContact.self,from:JSONSerialization.data(withJSONObject:row["response"]!))
        ledger.complete(a,outcome:client.map {.response(status:row["status"] as! Int,client:$0)} ?? .unknown)
        let expected:ClientCreateAttemptPhase = row["expected"] as! String == "confirmed" ? .confirmed:.unknown
        try expect(ledger.visible(authorization)?.phase==expected,"Client response/actor-absence/read completeness boundary changed: \(row["name"]!)")
        ledger.complete(a,outcome:.rejectedWithoutWrite);try expect(ledger.records[0].phase==expected,"Terminal Client result rewritten by duplicate completion")
        if expected == .unknown {try expect(!ledger.acknowledge(authorization) && ledger.begin(review:r,authorization:authorization)==nil,"Unknown Client create blindly replayed")}
    }
    let profile=try JSONDecoder().decode(ClientProfile.self,from:Data(contentsOf:directory.appendingPathComponent("client-101-701.json")))
    try expect(profile.client.full_name==nil && profile.client.business==nil && profile.client.notes==nil && profile.client.created_at==nil,"Bounded _client_item note/date/title was promoted into full creation/original fields")
    let long=review(context,notes:String(repeating:"N",count:2001)),v=long.preview
    for cap in [160,1000,2001] {
        var ledger=ClientCreateAttemptLedger();let a=ledger.begin(review:long,authorization:authorization)!
        ledger.complete(a,outcome:.response(status:201,client:ClientContact(id:87001,title:nil,phone:v.phone,email:v.email,business:101,full_name:v.fullName,source:v.source,notes:String(v.notes.prefix(cap)),created_at:"2026-10-30T12:00:00Z",updated_at:"2026-10-30T12:00:00Z")))
        try expect(ledger.visible(authorization)?.phase == (cap==2001 ? .confirmed:.unknown),"Client note read cap became full create echo or input cap")
    }
    var ledger=ClientCreateAttemptLedger();let first=ledger.begin(review:r,authorization:authorization)!,epoch=grant.authorization(for:ClientDraftContext(business:101,epoch:2))!
    try expect(ledger.visible(epoch)==nil && ledger.blocked(epoch.context),"New Client epoch exposed/replayed earlier attempt")
    ledger.complete(first,outcome:.rejectedWithoutWrite);try expect(ledger.acknowledge(authorization) && ledger.records[0].attempt.review.values==r.values,"Client no-write acknowledgement lost raw")
    let second=ledger.begin(review:r,authorization:authorization)!;ledger.complete(second,outcome:.unknown);let other=ClientDraftContext(business:202,epoch:2),otherAuth=SyntheticClientCreateGrant(business:202,actor:9002,create:true).authorization(for:ClientDraftContext(business:202,epoch:2))!
    try expect(ledger.begin(review:review(other),authorization:otherAuth) != nil && first.localID != second.localID,"Client unknown globally blocked another Business or reused correlation")
    return count
}
