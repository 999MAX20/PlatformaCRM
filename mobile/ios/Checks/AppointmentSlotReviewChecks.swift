import Foundation
import CRMCore

func runAppointmentSlotReviewChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let refs=APIAppointmentReferenceRepository(transport:FixtureTransport(directory:directory)),service=try await refs.reference(.service,business:101,id:8001),resource=try await refs.reference(.resource,business:101,id:9001),catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-slot-review-cases.json"))) as! [String:Any]
    for row in catalog["cases"] as! [[String:Any]] {
        let contextBusiness=try JSONDecoder().decode(Business.self,from:Data((row["context_business_json"] as! String).utf8)),contextService=AppointmentReferenceDetail.decode(Data((row["context_service_json"] as! String).utf8),kind:.service),contextResource=AppointmentReferenceDetail.decode(Data((row["context_resource_json"] as! String).utf8),kind:.resource)
        let business=try JSONDecoder().decode(Business.self,from:JSONSerialization.data(withJSONObject:["id":101,"name":"Synthetic Business A","timezone":row["intent_timezone"] as! String])),intent=AppointmentSlotIntent(business:business,service:service,resource:row["request_resource"] as! Bool ? resource:nil,day:"2026-11-02")!,read=AppointmentSlotRead.decode(Data((row["response_json"] as! String).utf8),intent:intent)
        let context=contextService.flatMap {s in read.flatMap {AppointmentSlotReadContext(business:contextBusiness,service:s,resource:contextResource,read:$0)}}
        try expect((context != nil)==row["context_valid"] as! Bool,"Candidate read context \(row["name"]!)")
        let review=context?.review(index:row["index"] as! Int);try expect((review != nil)==row["review_valid"] as! Bool,"Candidate membership \(row["name"]!)")
        if let context {
            let expected=try JSONDecoder().decode(String.self,from:Data((row["service_name_json"] as! String).utf8));try expect(context.service.name.utf8.elementsEqual(expected.utf8),"Review service name was trimmed/normalized/substituted")
            if let resource=context.resource {let expected=try JSONDecoder().decode(String.self,from:Data((row["resource_name_json"] as! String).utf8));try expect(resource.name.utf8.elementsEqual(expected.utf8),"Review Resource name came from parent label/default")}
            try expect(context.read.intent==intent && (context.resource?.id)==intent.resource,"Review changed exact query/resource mode")
        }
        if let review,let context {try expect(review.valid(for:context) && review.index==row["index"] as! Int && review.candidate==context.read.candidates[review.index],"Review selected an arbitrary/default range")}
    }
    return count
}
