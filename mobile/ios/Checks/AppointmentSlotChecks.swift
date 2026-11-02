import Foundation
import CRMCore

func runAppointmentSlotChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let fixed=APIAppointmentReferenceRepository(transport:FixtureTransport(directory:directory)),service=try await fixed.reference(.service,business:101,id:8001),resource=try await fixed.reference(.resource,business:101,id:9001)
    func business(_ zone:String="Asia/Almaty",id:Int=101)throws -> Business {try JSONDecoder().decode(Business.self,from:JSONSerialization.data(withJSONObject:["id":id,"name":"Synthetic","timezone":zone]))}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-slot-read-cases.json"))) as! [String:Any]
    for row in catalog["intent_cases"] as! [[String:Any]] {let raw=try JSONDecoder().decode(String.self,from:Data((row["day_json"] as! String).utf8));try expect((AppointmentSlotIntent(business:try business(),service:service,resource:nil,day:raw) != nil)==row["valid"] as! Bool,"Slot exact date input rejected/defaulted: \(String(reflecting:raw))")}
    try expect(AppointmentSlotIntent(business:try business("Unknown/Zone"),service:service,resource:nil,day:"2026-11-02")==nil,"Unknown Business zone fell back to UTC")
    try expect(AppointmentSlotIntent(business:try business(id:202),service:service,resource:nil,day:"2026-11-02")==nil,"Foreign Service became read context")
    let foreign=try await fixed.reference(.resource,business:202,id:9002)
    try expect(AppointmentSlotIntent(business:try business(),service:service,resource:foreign,day:"2026-11-02")==nil,"Foreign Resource became selected context")
    for row in catalog["cases"] as! [[String:Any]] {
        let intent=AppointmentSlotIntent(business:try business(row["timezone"] as! String),service:service,resource:nil,day:row["day"] as! String)!,transport=ReferenceCheckTransport(status:row["status"] as! Int,data:Data((row["response_json"] as! String).utf8)),repo=APIAppointmentSlotRepository(transport:transport)
        var result:AppointmentSlotRead?,failure:ReadFailure?
        do {result=try await repo.slots(intent)}catch {failure=error as? ReadFailure}
        try expect((result != nil)==row["valid"] as! Bool,"Slot read \(row["name"]!)")
        let calls=await transport.recorded();try expect(calls==[ReadRequest(path:"/api/appointments/available-slots/",query:["business_id":"101","service_id":"8001","date":intent.day])],"Slot read invented exclude/default Resource/key/version or mobile route")
        if let result {try expect(result.valid(for:intent),"Slot read lost exact intent");let items=row["response"] as! [[String:Any]];try expect(zip(result.candidates,items).allSatisfy {pair in pair.0.startAt==pair.1["start_at"] as! String && pair.0.endAt==pair.1["end_at"] as! String} && result.candidates.count==items.count,"Slot candidates were sorted/defaulted/mutated")}
        else {let status=row["status"] as! Int;try expect(failure == (status==403 ? .denied:status==404 ? .notFound:status==200 ? .invalidPayload:.unavailable),"Slot failure became successful empty result")}
    }
    let selected=AppointmentSlotIntent(business:try business(),service:service,resource:resource,day:"2026-11-02")!,repo=APIAppointmentSlotRepository(transport:FixtureAppointmentSlotTransport(directory:directory))
    try expect(selected.request.query==["business_id":"101","service_id":"8001","resource_id":"9001","date":"2026-11-02"],"Selected Resource query changed")
    let result=try await repo.slots(selected);try expect(result.candidates.count==2 && result.valid(for:selected),"Explicit synthetic catalogue read failed")
    let empty=AppointmentSlotIntent(business:try business(),service:service,resource:nil,day:"2026-11-03")!;try expect(try await repo.slots(empty).candidates.isEmpty,"Explicit empty catalogue became permanent/no read result")
    let adapter=FixtureAppointmentSlotTransport(directory:directory);let extra=try await adapter.get(ReadRequest(path:selected.request.path,query:selected.request.query.merging(["exclude_appointment_id":"501"],uniquingKeysWith:{$1})));try expect(extra.status==404,"Fixture inferred exclusion from old Appointment")
    return count
}
