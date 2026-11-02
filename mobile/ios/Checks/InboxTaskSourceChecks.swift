import Foundation
import CRMCore

private actor InboxTaskSourceRecorder:ReadTransport {
    let base:FixtureInboxTaskSourceTransport
    private var calls:[ReadRequest]=[]
    init(_ directory:URL) {base=FixtureInboxTaskSourceTransport(directory:directory)}
    func get(_ q:ReadRequest) async throws -> ReadResponse {calls.append(q);return try await base.get(q)}
    func recorded()->[ReadRequest] {calls}
}
func runInboxTaskSourceChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let d=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("inbox-task-source.json"))) as! [String:Any]
    func context(_ x:[String:Int])->InboxConversationFilesContext {InboxConversationFilesContext(business:x["business"]!,conversation:x["conversation"]!,epoch:x["epoch"]!,revision:x["revision"]!)}
    let a=context(d["context"] as! [String:Int]),b=InboxConversationFilesContext(business:202,conversation:951,epoch:801,revision:1),transport=InboxTaskSourceRecorder(directory),repo=APIInboxTaskSourceRepository(transport:transport)
    for x in d["source_cases"] as! [[String:Any]] {let s=InboxTaskSource.decode(Data((x["response_json"] as! String).utf8),context:context(x["context"] as! [String:Int]));try expect((s != nil)==x["valid"] as! Bool,"Exact generic Client/Lead source \(x["name"]!)");if let s {try expect(Mirror(reflecting:s).children.count==4 && s.valid,"Read retained Task/default/permission metadata")}}
    let source=try await repo.source(a),other=try await repo.source(b);let calls=await transport.recorded();try expect(calls.map(\.path)==["/api/inbox/conversations/901/","/api/inbox/conversations/951/"] && calls.allSatisfy {$0.query.isEmpty},"Task source invented endpoint/filter/query")
    var s=InboxTaskSourceSession();s.bind(a);s.show();let start=s.control!;s.use(expected:start);try expect(s.source==nil && s.choice==nil,"Show/Use inferred source")
    let first=s.begin(expected:start)!;try expect(!s.accept(other,ticket:first) && s.failure == .invalidPayload && s.source==nil,"Foreign source exposed relations")
    let ticket=s.begin(expected:s.control)!;try expect(s.accept(source,ticket:ticket) && s.canUse && s.choice==nil,"Read implicitly used source");let old=s.control;s.use(expected:old);let choice=s.choice!;try expect(choice.valid && choice.source==source && choice.readRevision==ticket.revision && choice.context==a,"Qualified source lost owner/read/raw fields")
    s.clearChoice(expected:old);try expect(s.choice==choice,"Stale clear removed choice");s.clearChoice(expected:s.control);try expect(s.choice==nil && s.source==source,"Clear removed observed source or changed relations")
    s.use(expected:s.control);let next=s.begin(expected:s.control)!;try expect(s.source==nil && s.choice==nil && !s.canUse,"New explicit GET retained old qualification");s.cancel(ticket:next);try expect(!s.loading && s.failure==nil && !s.accept(source,ticket:next),"Cancellation/late success qualified source")
    let late=s.begin(expected:s.control)!;s.hide();s.bind(b);s.show();let before=s.control;s.fail(.unavailable,ticket:late);try expect(s.control==before && !s.accept(source,ticket:late) && s.source==nil,"Late foreign response/failure changed owner")
    s.bind(a);s.show();try expect(!s.accept(source,ticket:late) && s.choice==nil,"Business ABA revived old ticket")
    for (id,error) in [(903,ReadFailure.denied),(904,.notFound),(905,.unavailable),(906,.invalidPayload)] {do {_=try await repo.source(InboxConversationFilesContext(business:101,conversation:id,epoch:800,revision:1));try expect(false,"Read failure accepted")}catch let value as ReadFailure {try expect(value==error,"Incorrect read failure mapping")}}
    return count
}
