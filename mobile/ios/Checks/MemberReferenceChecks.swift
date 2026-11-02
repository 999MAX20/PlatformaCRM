import Foundation
import CRMCore

private actor TeamMemberReadRecorder:ReadTransport {
    let base:FixtureTeamMemberReadTransport
    var requests:[ReadRequest]=[]
    init(_ directory:URL) {base=FixtureTeamMemberReadTransport(directory:directory)}
    func get(_ q:ReadRequest) async throws -> ReadResponse {requests.append(q);return try await base.get(q)}
}
func runMemberReferenceChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ v:Bool,_ m:String) throws {guard v else {throw CheckFailure(message:m)};count += 1}
    let f=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("team-member-read.json"))) as! [String:Any]
    for row in f["source_cases"] as! [[String:Any]] {let s=TeamMemberReadSource.decode(Data((row["response_json"] as! String).utf8),business:row["business"] as! Int,id:row["id"] as! Int);try expect((s != nil)==row["valid"] as! Bool,"Team membership source/nested User/strict bool \(row["name"]!)");try expect((s?.isActive==true)==row["eligible"] as! Bool,"Observed membership eligibility vs account/role \(row["name"]!)");if let s {try expect(Mirror(reflecting:s).children.count==5 && Mirror(reflecting:s.user).children.count==3,"Member lens retained role/phone/permission/teams")}}
    for row in f["input_cases"] as! [[String:Any]] {try expect(MemberReferenceIdentifier.parse(row["raw"] as! String)==row["parsed"] as? Int,"Local membership number grammar")}
    let transport=TeamMemberReadRecorder(directory),api=APITeamMemberReadRepository(transport:transport),active=try await api.member(business:101,id:8101),inactive=try await api.member(business:101,id:8102),account=try await api.member(business:101,id:8103),requests=await transport.requests
    try expect(requests==[ReadRequest(path:"/api/team/members/8101/"),ReadRequest(path:"/api/team/members/8102/"),ReadRequest(path:"/api/team/members/8103/")],"Member invented Business query/User lookup/flat DTO fallback")
    try expect(active.id==8101 && active.user.id==5002 && active.id != active.user.id && active.isActive && !inactive.isActive && account.isActive,"Membership id/User id or account active flag conflated")
    do {_=try await api.member(business:101,id:9101);throw CheckFailure(message:"Foreign membership exposed")}catch let error as ReadFailure {try expect(error == .invalidPayload,"Member foreign Business mapping")}
    for (id,error) in [(8199,ReadFailure.notFound),(8104,ReadFailure.denied)] {do {_=try await api.member(business:101,id:id);throw CheckFailure(message:"Member error became data")}catch let value as ReadFailure {try expect(value==error,"Team GET error mapping")}}
    var s=MemberReferenceSession();let a=InboxConversationFilesContext(business:101,conversation:901,epoch:1,revision:1),b=InboxConversationFilesContext(business:202,conversation:951,epoch:2,revision:1);s.bind(a);s.show();try expect(s.rawInput.isEmpty && s.source==nil && !s.canRead,"Member default target/auto GET")
    let input=s.input;s.update("e",input:input);s.update("e\u{0301}",input:input);try expect(SourceTextIdentity.same(s.rawInput,"e\u{0301}") && s.begin(expected:s.control)==nil,"Member raw invalid input normalized/fetched")
    s.clear(expected:s.control);s.update("8101",input:input);try expect(s.rawInput.isEmpty,"Stale pre-clear member input restored target");s.update("008101",input:s.input);let stale=s.control,t=s.begin(expected:s.control)!;try expect(t.id==8101 && t.rawInput=="008101" && s.begin(expected:s.control)==nil,"Member raw id/duplicate read")
    s.use(expected:s.control);try expect(s.choice==nil,"Member number alone qualified target");s.accept(active,ticket:t);s.use(expected:stale);try expect(s.choice==nil && s.canUse,"Stale member Use accepted or active data invalid");s.use(expected:s.control);let reference=s.choice!;try expect(reference.valid && reference.rawInput=="008101" && reference.source.id==8101 && reference.source.user.id==5002 && reference.context==a,"Qualified member lost distinct identities/raw/owner")
    s.update("8102",input:s.input);let it=s.begin(expected:s.control)!;s.accept(inactive,ticket:it);s.use(expected:s.control);try expect(s.source==inactive && !s.canUse && s.choice==nil,"Inactive Business member became qualified from role/account")
    s.update("8103",input:s.input);let at=s.begin(expected:s.control)!;s.accept(account,ticket:at);s.use(expected:s.control);try expect(s.choice?.valid==true && s.choice?.source.user.id==5004,"Nested account active flag replaced membership observation")
    let pending=s.begin(expected:s.control)!;s.update("8101",input:s.input);let edited=s.control;s.accept(account,ticket:pending);try expect(s.control==edited && s.rawInput=="8101" && s.source==nil,"Late old member response changed new input")
    let late=s.begin(expected:s.control)!;s.bind(b);s.show();s.update("9101",input:s.input);let current=s.control;s.accept(active,ticket:late);try expect(s.control==current && s.source==nil && s.rawInput=="9101","Member late response escaped Business switch");s.bind(a);s.show();try expect(!s.accept(active,ticket:late) && s.rawInput.isEmpty && s.choice==nil,"Member ABA restored reference")
    return count
}
