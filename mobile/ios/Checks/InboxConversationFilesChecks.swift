import Foundation
import CRMCore

func runInboxConversationFilesChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("inbox-conversation-files.json"))) as! [String:Any]
    for row in catalog["cases"] as! [[String:Any]] {
        let c=row["context"] as! [String:Int],context=InboxConversationFilesContext(business:c["business"]!,conversation:c["conversation"]!,epoch:c["epoch"]!,revision:c["revision"]!),result=InboxConversationFileMetadata.decode(Data((row["response_json"] as! String).utf8),context:context)
        try expect((result != nil)==(row["valid"] as! Bool),"Conversation metadata exact scope/strict/null/empty/raw vector: \(row["name"]!)")
        if let result {try expect(result.allSatisfy {$0.valid(for:context)},"Accepted metadata failed same-context validation");try expect(result.allSatisfy {Mirror(reflecting:$0).children.count==9},"URL/uploader/payload retained in metadata projection")}
    }
    let context=InboxConversationFilesContext(business:101,conversation:901,epoch:1,revision:1),transport=FixtureInboxConversationFilesTransport(directory:directory),repo=APIInboxConversationFilesRepository(transport:transport)
    let rows=try await repo.files(context);try expect(rows.count==2 && rows[0].size==4294967296 && rows[1].size==0 && rows[1].contentType.isEmpty,"64-bit/explicit zero/blank observations defaulted")
    let raw=(catalog["reads"] as! [[String:String]])[0]["response_json"]!,changed=raw.replacingOccurrences(of:"e\u{301}.txt",with:"é.txt"),other=InboxConversationFileMetadata.decode(Data(changed.utf8),context:context)!
    try expect(rows[1] != other[1] && rows[0]==other[0],"Metadata equality normalized a raw filename")
    for (status,error) in [(403,ReadFailure.denied),(404,.notFound),(503,.unavailable)] {
        do {_ = try await APIInboxConversationFilesRepository(transport:FixedTransport(response:ReadResponse(status:status,data:Data()))).files(context);throw CheckFailure(message:"Unexpected metadata response success")}
        catch let received as ReadFailure {try expect(received==error,"Metadata status mapping changed")}
    }
    let foreign=InboxConversationFilesContext(business:202,conversation:901,epoch:1,revision:1)
    do {_ = try await repo.files(foreign);throw CheckFailure(message:"Generic detail leaked foreign Business rows")} catch let error as ReadFailure {try expect(error == .invalidPayload,"Foreign metadata scope fallback inferred")}
    return count
}
