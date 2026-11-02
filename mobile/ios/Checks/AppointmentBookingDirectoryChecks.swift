import Foundation
import CRMCore

func runAppointmentBookingDirectoryChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),services=APIServiceDirectoryRepository(transport:FixtureServiceDirectoryTransport(directory:directory)),resources=APIResourceDirectoryRepository(transport:FixtureResourceDirectoryTransport(directory:directory))
    let page=try await repo.appointments(business:101,day:"2026-10-28")
    var session=AgendaSession();try session.install(try await repo.bootstrap());let scope=try session.begin(businessID:101,day:page.date);try session.receive(page,for:scope);let read=try session.beginDetail(id:501)
    let client=TaskDraftClientChoice(profile:try await repo.clientProfile(business:101,id:7001),business:101,id:7001)!,otherClient=TaskDraftClientChoice(profile:try await repo.clientProfile(business:101,id:7002),business:101,id:7002)!
    let a=try await services.service(business:101,id:8001),b=try await services.service(business:101,id:8003),foreignService=try await services.service(business:202,id:8002),r=try await resources.resource(business:101,id:9001),u=try await resources.resource(business:101,id:9003),foreignResource=try await resources.resource(business:202,id:9002)
    let serviceMap=[8001:a,8003:b,8002:foreignService],resourceMap=[9001:r,9003:u,9002:foreignResource]
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-booking-directory.json"))) as! [String:Any]
    for row in catalog["cases"] as! [[String:Any]] {
        let source=AppointmentBookingSource(read:read,epoch:row["source_epoch"] as! Int,clientID:7001,serviceID:8001,resourceID:9001),choiceSource=AppointmentBookingSource(read:read,epoch:row["choice_epoch"] as! Int,clientID:7001,serviceID:8001,resourceID:9001)
        let wanted=row["proof"] as! Bool,ps=(row["proof_service"] as? Int).flatMap {serviceMap[$0]},pr=(row["proof_resource"] as? Int).flatMap {resourceMap[$0]},proof=wanted ? AppointmentBookingDirectorySelection(source:choiceSource,service:ps,resource:pr):nil
        var service=serviceMap[row["service"] as! Int]!.reference
        if row["mutate_name"] as! Bool {service=AppointmentReferenceDetail.decode(try JSONSerialization.data(withJSONObject:["id":service.id,"business":service.business,"name":service.name+"changed","is_active":service.isActive!]),kind:.service)!}
        let resource=(row["resource"] as? Int).map {AppointmentRescheduleResource.linked(resourceMap[$0]!.reference)} ?? .clear
        let input=wanted && proof==nil ? nil:AppointmentBookingInput(source:source,client:(row["client"] as! Int)==7001 ? client:otherClient,service:service,resource:resource,startAt:"2026-10-29T05:00:00Z",directory:proof)
        try expect((input != nil)==(row["valid"] as! Bool),"Form directory proof scope/echo/legacy/client restriction mismatch: \(row["name"]!)")
        if let input {try expect(input.valid(for:source),"Typed field proof failed same-source validation");let body=try JSONSerialization.jsonObject(with:input.body(business:101)!) as! [String:Any];try expect(Set(body.keys)==["business","client","service","start_at","resource"] && body["service"] as? Int==service.id && (body["resource"] as? Int)==resource.id,"Directory metadata/permission/version leaked into5-field body or selected ids lost")}
    }
    let source=AppointmentBookingSource(read:read,epoch:1,clientID:7001,serviceID:8001,resourceID:9001),proof=AppointmentBookingDirectorySelection(source:source,service:b,resource:u)!,input=AppointmentBookingInput(source:source,client:client,service:b.reference,resource:.linked(u.reference),startAt:"2026-10-29T05:00:00Z",directory:proof)!
    try expect(!b.isActive && b.durationMinutes==0 && !u.isActive && !u.hasKnownType && input.directory==proof,"Read observations were defaulted into active/type/eligibility")
    let grant=SyntheticAppointmentBookingGrant(business:101,fromAppointment:501,actor:5001,create:true),auth=grant.authorization(source)!,review=AppointmentBookingReview(source:source,input:input,visit:1)
    try expect(SyntheticAppointmentBookingGrant(business:101,fromAppointment:501,actor:5001,create:false).authorization(source)==nil,"Directory read generated CREATE grant")
    var ledger=AppointmentBookingLedger();let attempt=ledger.begin(review,authorization:auth)!,original=attempt.body
    let booking=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-booking.json"))) as! [String:Any],scenario=(booking["scenarios"] as! [[String:Any]])[0]
    var receipt=try JSONSerialization.jsonObject(with:Data((scenario["response_json"] as! String).utf8)) as! [String:Any];receipt["service"]=b.id;receipt["resource"]=u.id
    ledger.complete(attempt,outcome:.response(status:201,data:try JSONSerialization.data(withJSONObject:receipt)))
    try expect(ledger.records[0].phase == .acceptedFixture && ledger.records[0].attempt.review.input.directory==proof && ledger.records[0].attempt.body==original,"Plain local201 selected-id echo lost proof or changed frozen body")
    var unknown=AppointmentBookingLedger();let retained=unknown.begin(review,authorization:auth)!;unknown.complete(retained,outcome:.unknown)
    let rereadService=try await services.service(business:101,id:8003),rereadResource=try await resources.resource(business:101,id:9003)
    try expect(rereadService==b && rereadResource==u && unknown.blocked(source) && !unknown.acknowledge(unknown.records[0]) && unknown.begin(review,authorization:auth)==nil && unknown.records[0].attempt==retained,"Matching directory reread released/repeated unknown input/attempt")
    return count
}
