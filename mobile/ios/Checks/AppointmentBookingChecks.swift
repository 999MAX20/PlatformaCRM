import Foundation
import CRMCore

func runAppointmentBookingChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let repository=APIReadRepository(transport:FixtureTransport(directory:directory)),references=APIAppointmentReferenceRepository(transport:FixtureTransport(directory:directory))
    let boot=try await repository.bootstrap(),page=try await repository.appointments(business:101,day:"2026-10-28"),detail=try await repository.appointment(business:101,id:501)
    var session=AgendaSession();try session.install(boot);let scope=try session.begin(businessID:101,day:page.date);try session.receive(page,for:scope)
    let source=AppointmentBookingSource(read:try session.beginDetail(id:501),epoch:1,clientID:detail.linkedClientID!,serviceID:detail.referenceID(.service)!,resourceID:detail.referenceID(.resource))
    let profile=try await repository.clientProfile(business:101,id:7001),client=TaskDraftClientChoice(profile:profile,business:101,id:7001)!,service=try await references.reference(.service,business:101,id:8001),resource=try await references.reference(.resource,business:101,id:9001)
    let input=AppointmentBookingInput(source:source,client:client,service:service,resource:.clear,startAt:"2026-10-29T05:00:00Z")!,fixture=FixtureAppointmentBookingPort(directory:directory),grant=fixture.grants.first {$0.business==101 && $0.from_appointment==501}!,auth=grant.authorization(source)!
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-booking.json"))) as! [String:Any]
    for row in catalog["time_cases"] as! [[String:Any]] {let raw=row["raw"] as! String,value=AppointmentBookingInput(source:source,client:client,service:service,resource:.clear,startAt:raw);try expect((value != nil)==(row["valid"] as! Bool),"Booking guessed/defaulted/rounded naive or invalid time");if let value {try expect(SourceTextIdentity.same(value.start.raw,raw),"Booking rewrote explicit raw time")}}
    let otherProfile=try await repository.clientProfile(business:101,id:7002),otherClient=TaskDraftClientChoice(profile:otherProfile,business:101,id:7002)!,foreign=try await references.reference(.service,business:202,id:8002)
    try expect(AppointmentBookingInput(source:source,client:otherClient,service:service,resource:.clear,startAt:input.start.raw)==nil && AppointmentBookingInput(source:source,client:client,service:foreign,resource:.clear,startAt:input.start.raw)==nil,"Wrong linked Client/cross-Business Service became booking input")
    let noResource=AppointmentBookingSource(read:source.read,epoch:1,clientID:7001,serviceID:8001,resourceID:nil)
    try expect(AppointmentBookingInput(source:noResource,client:client,service:service,resource:.linked(resource),startAt:input.start.raw)==nil,"Unlinked Resource typed id became booking choice")
    for denied in [SyntheticAppointmentBookingGrant(business:202,fromAppointment:501,actor:5001,create:true),SyntheticAppointmentBookingGrant(business:101,fromAppointment:502,actor:5001,create:true),SyntheticAppointmentBookingGrant(business:101,fromAppointment:501,actor:0,create:true),SyntheticAppointmentBookingGrant(business:101,fromAppointment:501,actor:5001,create:false)] {try expect(denied.authorization(source)==nil,"GET/invalid scope/actor/CREATE manufactured booking authorization")}
    for row in catalog["receipt_cases"] as! [[String:Any]] {
        var ledger=AppointmentBookingLedger();let review=AppointmentBookingReview(source:source,input:input,visit:1),attempt=ledger.begin(review,authorization:auth)!,body=try JSONSerialization.jsonObject(with:attempt.body) as! [String:Any]
        try expect(attempt.method=="POST" && attempt.path=="/api/appointments/" && attempt.query.isEmpty && Set(body.keys)==["business","client","service","start_at","resource"] && body["business"] as? Int==101 && body["client"] as? Int==7001 && body["service"] as? Int==8001 && body["resource"] is NSNull && body["start_at"] as? String==input.start.raw,"Booking body copied old fields/defaults/end/status/source/lead/notes/key/version or route/query")
        try expect(ledger.begin(review,authorization:auth)==nil && ledger.records[0].attempt.review.input==input,"Pending booking admitted duplicate or destroyed frozen input")
        ledger.complete(attempt,outcome:.response(status:row["status"] as! Int,data:try JSONSerialization.data(withJSONObject:row["body"]!)));let record=ledger.records[0],accepted=row["expected"] as! String=="acceptedFixture"
        try expect((record.phase == .acceptedFixture)==accepted && (record.receipt != nil)==accepted,"Booking plain201/FK/resource/instant/required-type oracle failed: \(row["name"]!)")
        let reread=AppointmentBookingSource(read:source.read,epoch:2,clientID:7001,serviceID:8001,resourceID:9001)
        if accepted {try expect(ledger.acknowledge(record) && ledger.used(reread),"Known local booking did not consume source entry across reread")}
        else {
            try expect(ledger.blocked(reread) && !ledger.acknowledge(record) && record.attempt==attempt && record.attempt.body==attempt.body,"Unknown/reread lost input/body/attempt or released barrier")
            ledger.complete(attempt,outcome:.response(status:201,data:try JSONSerialization.data(withJSONObject:(catalog["receipt_cases"] as! [[String:Any]])[0]["body"]!)))
            try expect(ledger.records[0].phase == .unknown && ledger.begin(AppointmentBookingReview(source:reread,input:input,visit:2),authorization:grant.authorization(reread)!)==nil,"Matching later response/reread rekeyed or repeated unknown")
        }
    }
    var ledger=AppointmentBookingLedger();let linked=AppointmentBookingInput(source:source,client:client,service:service,resource:.linked(resource),startAt:input.start.raw)!,attempt=ledger.begin(AppointmentBookingReview(source:source,input:linked,visit:1),authorization:auth)!
    var response=(catalog["receipt_cases"] as! [[String:Any]])[0]["body"] as! [String:Any];response["resource"]=9001;response["resource_name"]=resource.name;response["resource_type"]="staff"
    ledger.complete(attempt,outcome:.response(status:201,data:try JSONSerialization.data(withJSONObject:response)))
    let linkedBody=try JSONSerialization.jsonObject(with:attempt.body) as! [String:Any]
    try expect(ledger.records[0].phase == .acceptedFixture && linkedBody["resource"] as? Int==9001,"Explicit read Resource body/receipt mismatch")
    var rejected=AppointmentBookingLedger();let a=rejected.begin(AppointmentBookingReview(source:source,input:input,visit:1),authorization:auth)!;rejected.complete(a,outcome:.rejectedWithoutWrite)
    try expect(rejected.acknowledge(rejected.records[0]) && !rejected.used(source),"Explicit synthetic no-write rejection lost manual review path")
    var fromFixture=AppointmentBookingLedger();let f=fromFixture.begin(AppointmentBookingReview(source:source,input:input,visit:1),authorization:auth)!;fromFixture.complete(f,outcome:try await fixture.execute(f));try expect(fromFixture.records[0].phase == .acceptedFixture,"Exact fixture request was not accepted locally")
    let different=AppointmentBookingInput(source:source,client:client,service:service,resource:.clear,startAt:"2026-10-29T06:00:00Z")!;var mismatch=AppointmentBookingLedger();let m=mismatch.begin(AppointmentBookingReview(source:source,input:different,visit:1),authorization:auth)!;mismatch.complete(m,outcome:try await fixture.execute(m));try expect(mismatch.records[0].phase == .unknown && mismatch.records[0].attempt.review.input==different,"Arbitrary request received fabricated fixture success or lost input")
    return count
}
