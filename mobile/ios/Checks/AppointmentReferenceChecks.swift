import Foundation
import CRMCore

actor ReferenceCheckTransport:ReadTransport {
    private let status:Int,data:Data
    private var requests:[ReadRequest]=[]
    init(status:Int,data:Data) {self.status=status;self.data=data}
    func get(_ request:ReadRequest) async throws -> ReadResponse {requests.append(request);return ReadResponse(status:status,data:data)}
    func recorded()->[ReadRequest] {requests}
}
func runAppointmentReferenceChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let data=try Data(contentsOf:directory.appendingPathComponent("appointment-reference-read-cases.json")),f=try JSONSerialization.jsonObject(with:data) as! [String:Any]
    for row in f["cases"] as! [[String:Any]] {
        let kind=AppointmentReferenceKind(rawValue:row["kind"] as! String)!,business=row["business"] as! Int,id=row["id"] as! Int,status=row["status"] as! Int,yes=row["valid"] as! Bool
        let source=ReferenceCheckTransport(status:status,data:Data((row["response_json"] as! String).utf8)),repo=APIAppointmentReferenceRepository(transport:source)
        var detail:AppointmentReferenceDetail?,failure:ReadFailure?
        do {detail=try await repo.reference(kind,business:business,id:id)} catch {failure=error as? ReadFailure}
        try expect((detail != nil)==yes,"Reference result \(row["name"]!)")
        let calls=await source.recorded();try expect(calls==(kind.request(id:id).map {[$0]} ?? []),"Reference invented Business/list/slot query or requested unsupported id")
        if let detail {
            let name=try JSONDecoder().decode(String.self,from:Data((row["name_json"] as! String).utf8)),active=row["active"] is NSNull ? nil:row["active"] as? Bool
            try expect(detail.valid(for:business,id:id) && detail.name.utf8.elementsEqual(name.utf8) && detail.isActive==active,"Reference identity/name/unknown active drift")
            try expect(detail.resourceTypeCopyKey==row["type_key"] as! String,"Unknown type defaulted to staff/other")
        } else {
            let expected:ReadFailure=kind.request(id:id)==nil ? .invalidContext:status==403 ? .denied:status==404 ? .notFound:status==200 ? .invalidPayload:.unavailable
            try expect(failure==expected,"Reference failure mapped to data/empty/default")
        }
    }
    let transport=ReferenceCheckTransport(status:200,data:Data()),repo=APIAppointmentReferenceRepository(transport:transport)
    for (business,id) in [(0,8001),(101,0),(101,-1)] {do {_=try await repo.reference(.service,business:business,id:id);try expect(false,"Invalid reference request accepted")}catch let e as ReadFailure {try expect(e == .invalidContext,"Invalid reference request did not fail before GET")}}
    let noCalls=await transport.recorded();try expect(noCalls.isEmpty,"Invalid context issued a GET")
    let base=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-101-501.json"))) as! [String:Any]
    for row in f["parent_cases"] as! [[String:Any]] {
        var parent=base,details=base["details"] as! [String:Any]
        for key in ["service","resource"] {var value=details[key] as! [String:Any];value["id"]=row[key]!;details[key]=value};parent["details"]=details
        let parsed=try JSONDecoder().decode(AppointmentDetail.self,from:JSONSerialization.data(withJSONObject:parent))
        try expect((parsed.referenceID(.service) != nil)==row["service_valid"] as! Bool && (parsed.referenceID(.resource) != nil)==row["resource_valid"] as! Bool,"Reference selected from name/null/zero/out-of-width default")
    }
    let fixture=APIAppointmentReferenceRepository(transport:FixtureTransport(directory:directory)),service=try await fixture.reference(.service,business:101,id:8001),resource=try await fixture.reference(.resource,business:101,id:9001)
    try expect(service.resourceType==nil && resource.resourceType=="staff","Unselected resource type promoted from service")
    do {_=try await fixture.reference(.service,business:202,id:8001);try expect(false,"Legacy shared id silently switched Business")} catch let error as ReadFailure {try expect(error == .invalidPayload,"Shared foreign id was converted to selected Business/default")}
    return count
}
