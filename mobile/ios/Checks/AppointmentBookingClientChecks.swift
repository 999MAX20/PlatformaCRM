import Foundation
import CRMCore

func runAppointmentBookingClientChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),refs=APIAppointmentReferenceRepository(transport:FixtureTransport(directory:directory))
    let page=try await repo.appointments(business:101,day:"2026-10-28")
    var agenda=AgendaSession();try agenda.install(try await repo.bootstrap());let scope=try agenda.begin(businessID:101,day:page.date);try agenda.receive(page,for:scope);let read=try agenda.beginDetail(id:501)
    let service=try await refs.reference(.service,business:101,id:8001)
    let original=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("client-101-7002.json"))) as! [String:Any]
    func profile(id:Int,business:Int,title:Any) throws -> ClientProfile {
        var o=original,item=o["client"] as! [String:Any];item["id"]=id;item["title"]=title;o["business"]=business;o["client"]=item
        return try JSONDecoder().decode(ClientProfile.self,from:JSONSerialization.data(withJSONObject:o))
    }
    let vectors=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-booking-client.json"))) as! [String:Any]
    for row in vectors["cases"] as! [[String:Any]] {
        let s=AppointmentBookingSource(read:read,epoch:row["source_epoch"] as! Int,clientID:7001,serviceID:8001,resourceID:9001),ps=AppointmentBookingSource(read:read,epoch:row["proof_source_epoch"] as! Int,clientID:7001,serviceID:8001,resourceID:9001)
        let context=ClientSearchContext(business:row["context_business"] as! Int,epoch:row["context_epoch"] as! Int)
        let selection=ClientSearchSelection(context:context,generation:row["selection_generation"] as! Int)
        let selected=ClientSearchProfileSelection(selection:selection,id:row["selected_id"] as! Int,generation:row["profile_generation"] as! Int)
        let p=try profile(id:row["profile_id"] as! Int,business:row["profile_business"] as! Int,title:row["proof_title"]!)
        let proof=(row["proof"] as! Bool) ? AppointmentBookingClientSelection(source:ps,selected:selected,read:ClientReadSelection(business:row["read_business"] as! Int,id:row["read_id"] as! Int,revision:row["read_revision"] as! Int),rawQuery:row["raw_query"] as! String,profile:p):nil
        let client=TaskDraftClientChoice(profile:try profile(id:row["client"] as! Int,business:101,title:row["client_title"]!),business:101,id:row["client"] as! Int)!
        let input=(row["proof"] as! Bool) && proof==nil ? nil:AppointmentBookingInput(source:s,client:client,service:service,resource:.clear,startAt:"2026-10-29T05:00:00Z",clientSelection:proof)
        try expect((input != nil)==(row["valid"] as! Bool),"Client scope/raw/withheld/legacy proof vector: \(row["name"]!)")
        if let input {try expect(input.valid(for:s),"Retained Client proof failed revalidation");let body=try JSONSerialization.jsonObject(with:input.body(business:101)!) as! [String:Any];try expect(Set(body.keys)==["business","client","service","start_at","resource"] && body["client"] as? Int==client.id,"Client search/read metadata leaked into body")}
    }
    let source=AppointmentBookingSource(read:read,epoch:1,clientID:7001,serviceID:8001,resourceID:9001)
    var search=ClientSearchSession();let context=ClientSearchContext(business:101,epoch:1);search.bind(context);search.open(expected:context);let query=search.begin(expected:search.selection!)!;search.accept(try await repo.searchClients(business:101,search:""),request:query);search.select(id:1754,expected:search.selection!)
    let p=try await repo.clientProfile(business:101,id:1754),selected=search.profileSelection!,pr=ClientReadSelection(business:101,id:1754,revision:1)
    let proof=AppointmentBookingClientSelection(source:source,selected:selected,read:pr,rawQuery:"é",profile:p)!,other=AppointmentBookingClientSelection(source:source,selected:selected,read:pr,rawQuery:"e\u{301}",profile:p)!
    try expect(proof != other,"Client proof normalized raw query")
    let input=AppointmentBookingInput(source:source,client:proof.choice,service:service,resource:.clear,startAt:"2026-10-29T05:00:00Z",clientSelection:proof)!,review=AppointmentBookingReview(source:source,input:input,visit:1)
    let grant=SyntheticAppointmentBookingGrant(business:101,fromAppointment:501,actor:5001,create:true),auth=grant.authorization(source)!
    try expect(SyntheticAppointmentBookingGrant(business:101,fromAppointment:501,actor:5001,create:false).authorization(source)==nil,"Profile read generated CREATE")
    let fixture=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-booking.json"))) as! [String:Any],row=(fixture["scenarios"] as! [[String:Any]])[0]
    var receipt=try JSONSerialization.jsonObject(with:Data((row["response_json"] as! String).utf8)) as! [String:Any];receipt["client"]=1754
    var ledger=AppointmentBookingLedger();let attempt=ledger.begin(review,authorization:auth)!;ledger.complete(attempt,outcome:.response(status:201,data:try JSONSerialization.data(withJSONObject:receipt)))
    try expect(ledger.records[0].phase == .acceptedFixture && ledger.records[0].attempt.review.input.clientSelection==proof,"Plain synthetic201 did not match chosen Client or retain proof")
    var unknown=AppointmentBookingLedger();let retained=unknown.begin(review,authorization:auth)!;unknown.complete(retained,outcome:.unknown);let matching=try await repo.clientProfile(business:101,id:1754)
    try expect(TaskDraftClientChoice(profile:matching,business:101,id:1754)==proof.choice && unknown.blocked(source) && !unknown.acknowledge(unknown.records[0]) && unknown.begin(review,authorization:auth)==nil && unknown.records[0].attempt==retained,"Matching profile read released/repeated unknown")
    return count
}
