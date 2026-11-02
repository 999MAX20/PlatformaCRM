import Foundation
import CRMCore

private actor DealReadRecorder:ReadTransport {
    let base:FixtureDealReadTransport
    var requests:[ReadRequest]=[]
    init(_ directory:URL) {base=FixtureDealReadTransport(directory:directory)}
    func get(_ q:ReadRequest) async throws -> ReadResponse {requests.append(q);return try await base.get(q)}
}
func runDealReferenceChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ v:Bool,_ m:String) throws {guard v else {throw CheckFailure(message:m)};count += 1}
    let raw=try Data(contentsOf:directory.appendingPathComponent("deal-read.json")),fixture=try JSONSerialization.jsonObject(with:raw) as! [String:Any]
    for row in fixture["source_cases"] as! [[String:Any]] {let s=DealReadSource.decode(Data((row["response_json"] as! String).utf8),business:row["business"] as! Int,id:row["id"] as! Int);try expect((s != nil)==row["valid"] as! Bool,"Generic Deal projection/scope/alias \(row["name"]!)");if let s {try expect(Mirror(reflecting:s).children.count==6,"Deal source retained amount/currency/notes/permission/version")}}
    for row in fixture["input_cases"] as! [[String:Any]] {let expected=row["parsed"] as? Int;try expect(DealReferenceIdentifier.parse(row["raw"] as! String)==expected,"Local explicit Deal number grammar \(row["raw"]!)")}
    let transport=DealReadRecorder(directory),api=APIDealReadRepository(transport:transport),source=try await api.deal(business:101,id:5701),noLead=try await api.deal(business:101,id:5702),requests=await transport.requests
    try expect(requests==[ReadRequest(path:"/api/deals/5701/"),ReadRequest(path:"/api/deals/5702/")],"Generic Deal invented Business/search/mobile DTO query")
    try expect(source.client==1701 && source.lead==3701 && noLead.client==1702 && noLead.lead==nil,"Deal client/nullable Lead aliases mixed with mobile read")
    do {_=try await api.deal(business:101,id:6701);throw CheckFailure(message:"Foreign Deal Business exposed")}catch let error as ReadFailure {try expect(error == .invalidPayload,"Foreign Deal response was not scope invalid")}
    for (id,expected) in [(5703,ReadFailure.notFound),(5704,ReadFailure.denied)] {do {_=try await api.deal(business:101,id:id);throw CheckFailure(message:"Deal error became data")}catch let error as ReadFailure {try expect(error==expected,"Generic Deal GET error mapping")}}
    var session=DealReferenceSession();let a=InboxConversationFilesContext(business:101,conversation:901,epoch:1,revision:1),b=InboxConversationFilesContext(business:202,conversation:951,epoch:2,revision:1);session.bind(a);session.show();try expect(session.rawInput.isEmpty && !session.canRead && session.source==nil,"Deal default id or automatic read")
    let input=session.input;session.update("e",input:input);session.update("e\u{0301}",input:input);try expect(SourceTextIdentity.same(session.rawInput,"e\u{0301}") && session.invalidIdentifier && session.begin(expected:session.control)==nil,"Deal raw input normalized or invalid id fetched")
    session.clear(expected:session.control);session.update("5701",input:input);try expect(session.rawInput.isEmpty,"Queued pre-clear Deal input resurrected old target");session.update("005701",input:session.input);let before=session.control,t=session.begin(expected:session.control)!;try expect(t.id==5701 && t.rawInput=="005701" && session.begin(expected:session.control)==nil,"Deal parsed target/raw id or duplicate read")
    session.use(expected:session.control);try expect(session.choice==nil,"Deal input alone qualified reference");try expect(session.accept(source,ticket:t) && session.canUse && session.choice==nil,"Independent Deal read auto selected/failed")
    session.use(expected:before);try expect(session.choice==nil,"Stale Deal Use consumed new read");session.use(expected:session.control);let choice=session.choice!;try expect(choice.valid && choice.context==a && choice.rawInput=="005701" && choice.source==source,"Qualified Deal lost scope/raw input/source")
    let used=session.control;session.clearChoice(expected:used);session.use(expected:used);try expect(session.choice==nil && session.source==source,"Local clear performed unlink or stale Use restored choice")
    let pending=session.begin(expected:session.control)!;session.update("5702",input:session.input);let current=session.control;try expect(!session.accept(source,ticket:pending) && session.control==current && session.rawInput=="5702" && session.source==nil,"Late old Deal read changed edited identifier")
    let next=session.begin(expected:session.control)!;session.accept(noLead,ticket:next);session.use(expected:session.control);try expect(session.choice?.source.lead==nil && session.choice?.valid==true,"Nullable Deal Lead reference inferred a relationship")
    session.hide();session.show();try expect(session.rawInput=="5702" && session.choice==nil && session.source==nil,"Deal same-owner hide lost raw input/kept qualification")
    session.update("5701",input:session.input);let late=session.begin(expected:session.control)!;session.bind(b);session.show();session.update("6701",input:session.input);let bControl=session.control;session.accept(source,ticket:late);try expect(session.control==bControl && session.rawInput=="6701" && session.source==nil,"Late Deal read escaped Business switch");session.bind(a);session.show();try expect(!session.accept(source,ticket:late) && session.rawInput.isEmpty,"Deal ABA restored target/reference")
    return count
}
