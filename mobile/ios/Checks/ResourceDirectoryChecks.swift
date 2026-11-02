import Foundation
import CRMCore

actor ResourceDirectoryRecordingTransport:ReadTransport {
    private let fixed:FixtureResourceDirectoryTransport
    private let status:Int
    private var requests:[ReadRequest]=[]
    init(_ directory:URL,status:Int=200) {fixed=FixtureResourceDirectoryTransport(directory:directory);self.status=status}
    func get(_ request:ReadRequest) async throws -> ReadResponse {requests.append(request);return status==200 ? try await fixed.get(request):ReadResponse(status:status,data:Data())}
    func recorded()->[ReadRequest] {requests}
}
func runResourceDirectoryChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("resource-directory.json"))) as! [String:Any]
    for row in catalog["cases"] as! [[String:Any]] {
        let value=ResourceDirectoryWindow.decode(Data((row["response_json"] as! String).utf8),business:row["business"] as! Int)
        try expect((value != nil)==(row["valid"] as! Bool),"Resource window strictness/scope mismatch: \(row["name"]!)")
        if let value {try expect(value.items.map(\.id)==row["ids"] as! [Int] && value.items.allSatisfy {$0.business==value.business},"Foreign/malformed rows leaked into selected Resource window")}
    }
    let transport=ResourceDirectoryRecordingTransport(directory),repo=APIResourceDirectoryRepository(transport:transport)
    let a=try await repo.resources(business:101),b=try await repo.resources(business:202),detail=try await repo.resource(business:101,id:9001),zero=try await repo.resource(business:101,id:9003)
    try expect(a.receivedCount==3 && a.observedCount==999 && a.next == .present && a.previous == .null && a.items.count==2,"Global metadata inferred selected total/completeness or lost presence")
    try expect(b.items.map(\.id)==[9002] && detail != a.items.first && zero.resourceType=="legacy/unknown" && !zero.isActive && !zero.hasKnownType && zero.typeCopyKey=="notAvailable","Independent Resource detail or unknown/inactive type was defaulted/filtered")
    do {_ = try await repo.resource(business:101,id:9002);throw CheckFailure(message:"Cross-Business Resource detail accepted")} catch ReadFailure.invalidPayload {count += 1}
    do {_ = try await repo.resources(business:0);throw CheckFailure(message:"Invalid Business reached port")} catch ReadFailure.invalidContext {count += 1}
    let calls=await transport.recorded()
    try expect(calls==[ReadRequest(path:"/api/resources/"),ReadRequest(path:"/api/resources/"),ReadRequest(path:"/api/resources/9001/"),ReadRequest(path:"/api/resources/9003/"),ReadRequest(path:"/api/resources/9002/")],"Resource query/path guessed Business/paging/default/filter or followed next URL")
    for (status,failure) in [(403,ReadFailure.denied),(404,.notFound),(500,.unavailable)] {
        let port=ResourceDirectoryRecordingTransport(directory,status:status),reader=APIResourceDirectoryRepository(transport:port)
        do {_ = try await reader.resources(business:101);throw CheckFailure(message:"Resource read status became empty success")} catch let e as ReadFailure {try expect(e==failure,"Wrong Resource status lens")}
        try expect(await port.recorded().count==1,"Resource read auto-retried/fell back")
    }
    let zeroJSON=(catalog["reads"] as! [[String:Any]])[2]["response_json"] as! String
    var object=try JSONSerialization.jsonObject(with:Data(zeroJSON.utf8)) as! [String:Any]
    // Canonically equivalent business data is still a different observed payload.
    object["name"]="Caf\u{0065}\u{0301}";let decomposed=ResourceDirectoryItem.decode(try JSONSerialization.data(withJSONObject:object))!
    try expect(zero != decomposed,"Resource row identity normalized raw name bytes")
    object["name"]=zero.name;object["created_at"]="2026-10-01T04:00:00+00:00";let rawTime=ResourceDirectoryItem.decode(try JSONSerialization.data(withJSONObject:object))!
    try expect(zero != rawTime,"Observed timestamp became a normalized version/identity proof")
    for (raw,key) in [("staff","referenceTypeStaff"),("room","referenceTypeRoom"),("hall","referenceTypeHall"),("box","referenceTypeBox"),("equipment","referenceTypeEquipment"),("other","referenceTypeOther")] {
        object["resource_type"]=raw;let value=ResourceDirectoryItem.decode(try JSONSerialization.data(withJSONObject:object))!
        try expect(value.hasKnownType && value.typeCopyKey==key && !value.isActive,"Known Resource type label changed source activity/eligibility")
    }
    return count
}
