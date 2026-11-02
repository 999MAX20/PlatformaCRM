import Foundation
import CRMCore

actor MessageFilesRecordedTransport:ReadTransport {
    let base:FixtureInboxMessageFilesTransport;private var requests:[ReadRequest]=[]
    init(_ directory:URL) {base=FixtureInboxMessageFilesTransport(directory:directory)}
    func get(_ request:ReadRequest) async throws -> ReadResponse {requests.append(request);return try await base.get(request)}
    func recorded()->[ReadRequest] {requests}
}
func runInboxMessageFilesChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("inbox-message-files.json"))) as! [String:Any]
    func context(_ row:[String:Any])->InboxMessageFilesContext {let c=row["context"] as! [String:Int];return InboxMessageFilesContext(business:c["business"]!,conversation:c["conversation"]!,message:c["message"]!,epoch:c["epoch"]!,revision:c["revision"]!,limit:c["limit"]!)}
    for row in catalog["anchor_cases"] as! [[String:Any]] {let c=context(row),anchor=InboxFilesConversationAnchor.decode(Data((row["response_json"] as! String).utf8),context:c);try expect((anchor != nil)==(row["valid"] as! Bool),"Generic anchor strict identity: \(row["name"]!)");if let anchor {try expect(anchor.matches(c),"Anchor failed own context")}}
    for row in catalog["cases"] as! [[String:Any]] {
        let c=context(row);var result="valid"
        do {let value=try InboxMessageFileWindow.decode(Data((row["response_json"] as! String).utf8),context:c);try expect(value.valid(for:c),"Accepted selected-message metadata failed context validation");try expect(value.items.allSatisfy {Mirror(reflecting:$0).children.count==9},"URL/uploader/scan/payload retained in file projection")}
        catch let error as ReadFailure {result=error == .unavailable ? "unavailable":"invalidPayload"}
        try expect(result==(row["expected"] as! String),"Message first-window/selected/all-row scope vector: \(row["name"]!)")
    }
    for row in catalog["source_identity_cases"] as! [[String:Any]] {let a=try JSONDecoder().decode(InboxMessage.self,from:JSONSerialization.data(withJSONObject:row["left"]!)),b=try JSONDecoder().decode(InboxMessage.self,from:JSONSerialization.data(withJSONObject:row["right"]!));try expect(InboxMessageFileSourceIdentity.same(a,b)==(row["same"] as! Bool),"Bounded message raw/typed observation identity: \(row["name"]!)")}
    let c=InboxMessageFilesContext(business:101,conversation:901,message:9011,epoch:1,revision:1,limit:30),transport=MessageFilesRecordedTransport(directory),repo=APIInboxMessageFilesRepository(transport:transport),anchor=try await repo.anchor(c),window=try await repo.messages(c,anchor:anchor)
    try expect(await transport.recorded()==[ReadRequest(path:"/api/inbox/conversations/901/"),ReadRequest(path:"/api/inbox/conversations/901/messages/",query:["limit":"30"])],"Message metadata guessed query/business/cursor or bypassed anchor")
    try expect(window.items.count==2 && window.items[0].size==4294967296 && window.items[1].size==0 && window.providedMessages==2 && window.count==2 && !window.hasMore,"Source metadata/window/64-bit observations defaulted")
    let other=InboxMessageFilesContext(business:101,conversation:901,message:9012,epoch:1,revision:1,limit:30),empty=try await repo.messages(other,anchor:anchor);try expect(empty.items.isEmpty && empty.valid(for:other),"Provided selected empty attachments confused with missing message")
    for (status,error) in [(403,ReadFailure.denied),(404,.notFound),(503,.unavailable)] {do {_ = try await APIInboxMessageFilesRepository(transport:FixedTransport(response:ReadResponse(status:status,data:Data()))).anchor(c);throw CheckFailure(message:"Anchor HTTP error accepted")}catch let received as ReadFailure {try expect(received==error,"Anchor status mapping changed")}}
    return count
}
