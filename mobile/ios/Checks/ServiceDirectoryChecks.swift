import Foundation
import CRMCore

actor ServiceDirectoryRecordingTransport:ReadTransport {
    private let fixed:FixtureServiceDirectoryTransport
    private let status:Int
    private var requests:[ReadRequest]=[]
    init(_ directory:URL,status:Int=200) {fixed=FixtureServiceDirectoryTransport(directory:directory);self.status=status}
    func get(_ request:ReadRequest) async throws -> ReadResponse {requests.append(request);return status==200 ? try await fixed.get(request):ReadResponse(status:status,data:Data())}
    func recorded()->[ReadRequest] {requests}
}
func runServiceDirectoryChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("service-directory.json"))) as! [String:Any]
    for row in catalog["cases"] as! [[String:Any]] {
        let value=ServiceDirectoryWindow.decode(Data((row["response_json"] as! String).utf8),business:row["business"] as! Int)
        try expect((value != nil)==(row["valid"] as! Bool),"Service window strictness/scope mismatch: \(row["name"]!)")
        if let value {try expect(value.items.map(\.id)==row["ids"] as! [Int] && value.items.allSatisfy {$0.business==value.business},"Foreign/malformed rows leaked into selected Service window")}
    }
    let transport=ServiceDirectoryRecordingTransport(directory),repo=APIServiceDirectoryRepository(transport:transport)
    let a=try await repo.services(business:101),b=try await repo.services(business:202),detail=try await repo.service(business:101,id:8001),zero=try await repo.service(business:101,id:8003)
    try expect(a.receivedCount==3 && a.observedCount==999 && a.next == .present && a.previous == .null && a.items.count==2,"Global metadata inferred selected total/completeness or lost presence")
    try expect(b.items.map(\.id)==[8002] && detail != a.items.first && zero.durationMinutes==0 && !zero.isActive && zero.priceFrom==nil,"Independent detail changed data/zero/inactive/null was defaulted or filtered")
    do {_ = try await repo.service(business:101,id:8002);throw CheckFailure(message:"Cross-Business Service detail accepted")} catch ReadFailure.invalidPayload {count += 1}
    do {_ = try await repo.services(business:0);throw CheckFailure(message:"Invalid Business reached port")} catch ReadFailure.invalidContext {count += 1}
    let calls=await transport.recorded()
    try expect(calls==[ReadRequest(path:"/api/services/"),ReadRequest(path:"/api/services/"),ReadRequest(path:"/api/services/8001/"),ReadRequest(path:"/api/services/8003/"),ReadRequest(path:"/api/services/8002/")],"Service query/path guessed Business/paging/default/filter or followed next URL")
    for (status,failure) in [(403,ReadFailure.denied),(404,.notFound),(500,.unavailable)] {
        let port=ServiceDirectoryRecordingTransport(directory,status:status),reader=APIServiceDirectoryRepository(transport:port)
        do {_ = try await reader.services(business:101);throw CheckFailure(message:"Service read status became empty success")} catch let e as ReadFailure {try expect(e==failure,"Wrong Service status lens")}
        try expect(await port.recorded().count==1,"Service read auto-retried/fell back")
    }
    let zeroJSON=(catalog["reads"] as! [[String:Any]])[2]["response_json"] as! String
    var object=try JSONSerialization.jsonObject(with:Data(zeroJSON.utf8)) as! [String:Any]
    // Canonically equivalent business data is still a different observed payload.
    object["name"]="Caf\u{0065}\u{0301}";let decomposed=ServiceDirectoryItem.decode(try JSONSerialization.data(withJSONObject:object))!
    try expect(zero != decomposed,"Service row identity normalized raw name bytes")
    object["name"]=zero.name;object["created_at"]="2026-10-01T04:00:00+00:00";let rawTime=ServiceDirectoryItem.decode(try JSONSerialization.data(withJSONObject:object))!
    try expect(zero != rawTime,"Observed timestamp became a normalized version/identity proof")
    return count
}
