import Foundation
import CRMCore

func runAppointmentBookingCandidateChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-booking-candidate-time.json"))) as! [String:Any]
    for row in catalog["cases"] as! [[String:Any]] {
        let business=row["source_business"] as! Int
        var boot=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("bootstrap.json"))) as! [String:Any],businesses=boot["businesses"] as! [[String:Any]]
        for i in businesses.indices where businesses[i]["id"] as? Int==business {businesses[i]["timezone"]=row["source_timezone"]!};boot["businesses"]=businesses
        var active=boot["active_business"] as! [String:Any];if active["id"] as? Int==business {active["timezone"]=row["source_timezone"]!};boot["active_business"]=active
        var session=AgendaSession();try session.install(JSONDecoder().decode(Bootstrap.self,from:JSONSerialization.data(withJSONObject:boot)));let scope=try session.begin(businessID:business,day:"2026-10-28");let page=try JSONDecoder().decode(AppointmentList.self,from:Data(contentsOf:directory.appendingPathComponent("appointments-\(business).json")));try session.receive(page,for:scope)
        let source=AppointmentBookingSource(read:try session.beginDetail(id:business == 101 ? 501:601),epoch:1,clientID:business == 101 ? 7001:7003,serviceID:row["source_service"] as! Int,resourceID:row["source_resource"] as? Int)
        let contextBusiness=try JSONDecoder().decode(Business.self,from:JSONSerialization.data(withJSONObject:["id":row["context_business"]!,"name":"Synthetic Business","timezone":row["context_timezone"]!])),service=AppointmentReferenceDetail.decode(try JSONSerialization.data(withJSONObject:["id":row["context_service"]!,"business":row["context_business"]!,"name":"Synthetic Service","is_active":false]),kind:.service)!
        let resource:AppointmentReferenceDetail? = try (row["context_resource"] as? Int).map {id in AppointmentReferenceDetail.decode(try JSONSerialization.data(withJSONObject:["id":id,"business":row["context_business"]!,"name":"Synthetic Resource"]),kind:.resource)!}
        var selected:AppointmentBookingCandidateTime?
        if let intent=AppointmentSlotIntent(business:contextBusiness,service:service,resource:resource,day:row["day"] as! String),let read=AppointmentSlotRead.decode(Data((row["response_json"] as! String).utf8),intent:intent),let context=AppointmentSlotReadContext(business:contextBusiness,service:service,resource:resource,read:read),let review=context.review(index:row["index"] as! Int) {selected=AppointmentBookingCandidateTime(source:source,review:review)}
        try expect((selected != nil)==(row["valid"] as! Bool),"Candidate time admitted wrong scope/service/resource/zone/index/precision or rejected exact raw choice: \(row["name"]!)")
        if let selected {
            try expect(SourceTextIdentity.same(selected.rawStart,selected.review.candidate.startAt) && selected.valid(for:source),"Candidate time was reformatted/rounded or lost source")
            let other=AppointmentBookingSource(read:source.read,epoch:2,clientID:source.clientID,serviceID:source.serviceID,resourceID:source.resourceID)
            try expect(!selected.valid(for:other),"Old time choice crossed source epoch")
            try expect(SyntheticAppointmentBookingGrant(business:business,fromAppointment:source.read.id,actor:5001,create:false).authorization(source)==nil,"Read candidate manufactured CREATE grant")
        }
    }
    return count
}
