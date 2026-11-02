import Foundation
import CRMCore

func runClientProfileChecks(directory: URL) async throws -> Int {
    var count = 0
    func expect(_ value: Bool, _ message: String) throws { guard value else { throw CheckFailure(message: message) }; count += 1 }
    func variant(_ change: (inout [String: Any]) -> Void) throws -> ClientProfile {
        var json = try JSONSerialization.jsonObject(with: Data(contentsOf: directory.appendingPathComponent("client-101-701.json"))) as! [String: Any]
        change(&json); return try JSONDecoder().decode(ClientProfile.self, from: JSONSerialization.data(withJSONObject: json))
    }
    let source = RecordingTransport(FixtureTransport(directory: directory)); let repo = APIReadRepository(transport: source)
    let profile = try await repo.clientProfile(business: 101, id: 701)
    try expect(profile.valid(for: 101, id: 701) && profile.details.notes == "Synthetic client profile note", "Client profile projection changed")
    try expect(profile.related.appointments.map(\.clientID) == [701] && profile.related.appointments.map { $0.appointment.id } == [5101], "Profile inferred wrong association")
    let requests = await source.requests
    try expect(requests == [ReadRequest(path: "/api/mobile/v1/clients/701/", query: ["business":"101"])], "Profile invented route/query")
    let history = try await repo.appointments(business: 101, day: "2026-10-27")
    try expect(history.items.map(\.id) == [5101] && history.items[0] == profile.related.appointments[0].appointment, "Profile/agenda history identity differs")
    let record = try await repo.appointment(business: 101, id: 5101)
    try expect(record.appointment == history.items[0], "Profile history target differs from record")
    let mismatch = try variant { json in
        var related = json["related"] as! [String: Any]; var visits = related["appointments"] as! [[String: Any]]
        visits[0]["client_id"] = 702; related["appointments"] = visits; json["related"] = related
    }
    try expect(!mismatch.valid(for: 101, id: 701), "Unrelated Client visit accepted")
    let duplicated = try variant { json in
        var related = json["related"] as! [String: Any]; let visits = related["appointments"] as! [[String: Any]]; related["appointments"] = [visits[0], visits[0]]; json["related"] = related
    }
    try expect(!duplicated.valid(for: 101, id: 701), "Duplicate Client visit accepted")
    let capped = try variant { $0["payload_budget"] = ["max_related_per_section":1] }
    try expect(capped.valid(for: 101, id: 701) && capped.historyCapped, "Capped Client history looked complete")
    let empty = try await repo.clientProfile(business: 101, id: 702)
    try expect(empty.related.appointments.isEmpty && empty.client.phone == nil, "Empty/withheld Client fields changed")
    let denied = APIReadRepository(transport: FixedTransport(response: ReadResponse(status: 403, data: Data())))
    do { _ = try await denied.clientProfile(business: 101, id: 701); throw CheckFailure(message: "Directory access granted profile access") }
    catch let error as ReadFailure { try expect(error == .denied, "Wrong profile denied error") }
    count += try await runClientMergeContractChecks(directory:directory)
    return count
}

private func runClientMergeContractChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("client-merge-preview.json"))) as! [String:Any]
    for row in catalog["decode_cases"] as! [[String:Any]] {
        let value=try? ClientMergePreview.decode(Data((row["response_json"] as! String).utf8))
        try expect((value != nil) == (row["valid"] as! Bool),"Merge preview shape/required13/policy mismatch: \(row["name"]!)")
        if let value {let raw=try JSONSerialization.jsonObject(with:Data((row["response_json"] as! String).utf8)) as! [String:Any];let counts=raw["transferred"] as! [String:Int];try expect(value.transferred.provided==counts && counts.count==13,"Provided transfer counts were defaulted/omitted/combined")}
    }
    for row in catalog["snapshot_identity_pairs"] as! [[String:Any]] {
        let a=try ClientMergePreview.decode(Data((row["before_json"] as! String).utf8)),b=try ClientMergePreview.decode(Data((row["after_json"] as! String).utf8))
        try expect(a.duplicate != b.duplicate && a != b,"Provided duplicate snapshot field canonicalized: \(row["field"]!)")
    }
    let source=FixtureClientMergePreviewSource(directory:directory),c=ClientMergePreviewContext(business:101,target:701,epoch:5,readRevision:1)
    let rows=try await source.candidates(for:c)
    try expect(rows?.map(\.id)==[702,703],"Scoped local merge choices changed or guessed first choice")
    let value=try await source.preview(for:c,duplicate:702)
    try expect(value?.matches(c,duplicate:702)==true && value?.will_delete_duplicate==false && value?.policy=="archive_duplicate_after_transfer","Existing target/duplicate/archive-only preview changed")
    try expect(try await source.preview(for:c,duplicate:999)==nil,"Unprovided duplicate produced fixture result")
    try expect(try await source.candidates(for:ClientMergePreviewContext(business:202,target:701,epoch:5,readRevision:1))==nil,"Fixture catalog inferred Business from target id")
    try expect(try await source.candidates(for:ClientMergePreviewContext(business:101,target:702,epoch:5,readRevision:1))?.isEmpty==true,"Explicit empty catalog was not retained")
    try expect(try await source.candidates(for:ClientMergePreviewContext(business:202,target:801,epoch:5,readRevision:1))?.map(\.id)==[802],"Other Business target mixed choices")
    try expect(try await source.candidates(for:ClientMergePreviewContext(business:0,target:701,epoch:5,readRevision:1))==nil,"Invalid local source context accepted")
    return count
}
