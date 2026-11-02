import Foundation
import CRMCore

private actor LeadReadRecorder:ReadTransport {
    let data:Data
    var requests:[ReadRequest]=[]
    init(_ data:Data) {self.data=data}
    func get(_ request:ReadRequest) async throws -> ReadResponse {requests.append(request);return try FixtureLeadReadTransport.response(data,request:request)}
}
func runLeadReadChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let raw=try Data(contentsOf:directory.appendingPathComponent("lead-read.json")),o=try JSONSerialization.jsonObject(with:raw) as! [String:Any]
    for c in o["cases"] as! [[String:Any]] {
        let data=try JSONSerialization.data(withJSONObject:c["payload"]!),valid:Bool
        if c["kind"] as! String=="page" {valid=(try? JSONDecoder().decode(LeadReadPage.self,from:data).valid(for:101)) ?? false}
        else {valid=(try? JSONDecoder().decode(LeadReadDetail.self,from:data).valid(for:101,id:3701)) ?? false}
        try expect(valid==c["valid"] as! Bool,"Lead mobile projection/scope case \(c["name"]!)")
    }
    let transport=LeadReadRecorder(raw),api=APILeadReadRepository(transport:transport),page=try await api.leads(business:101,search:"\u{001c} "),profile=try await api.lead(business:101,id:3701),requests=await transport.requests
    try expect(requests==[ReadRequest(path:"/api/mobile/v1/leads/",query:["business":"101","limit":"50","search":""]),ReadRequest(path:"/api/mobile/v1/leads/3701/",query:["business":"101"])],"Lead invented GET parameters/default Business/command")
    try expect(page.items.count==50 && page.summary.total==54 && page.items.first?.id==3701,"Lead first50/count/order wrong")
    try expect(profile.lead.client_id==1701 && profile.details.message.count>profile.lead.message.count,"Lead detail reused list preview as full detail")
    let beyond=try await api.leads(business:101,search:"после окна50");try expect(beyond.items.map(\.id)==[3753],"Lead search filtered loaded first50 instead of fixture server query")
    let archived=try FixtureLeadReadTransport.response(raw,request:ReadRequest(path:"/api/mobile/v1/leads/3755/",query:["business":"101"]));try expect(archived.status==404,"Archived mobile Lead was readable")
    var s=LeadReadSession();let a=InboxConversationFilesContext(business:101,conversation:901,epoch:1,revision:1),b=InboxConversationFilesContext(business:202,conversation:951,epoch:2,revision:1);s.bind(a);s.show();let input=s.input,old=s.control
    s.update("e",input:input);s.update("e\u{0301}",input:input);try expect(SourceTextIdentity.same(s.query,"e\u{0301}") && s.input==input,"Lead continuous raw NFD input/control lost")
    s.clear(expected:s.control);let ticket=s.beginList(expected:s.control)!;try expect(s.beginList(expected:s.control)==nil && !s.canUse && s.choice==nil,"Lead pending duplicate or list authority")
    try expect(s.accept(page,ticket:ticket) && s.partial && !s.showsEmpty,"Lead current page not partial")
    try expect(s.beginProfile(id:3701,expected:old)==nil && s.beginProfile(id:3753,expected:s.control)==nil,"Lead stale/off-window row selected")
    let t=s.beginProfile(id:3701,expected:s.control)!;s.use(expected:s.control);try expect(s.choice==nil,"Lead row alone qualified without profile");try expect(s.accept(profile,ticket:t) && s.canUse,"Independent Lead profile rejected")
    s.use(expected:s.control);try expect(s.choice?.detail.lead.client_id==1701 && s.choice?.context==a,"Lead qualified client/reference mismatch");let stale=s.control;s.clearChoice(expected:stale);s.use(expected:stale);try expect(s.choice==nil,"Stale Lead choice control reused")
    s.backProfile(expected:s.control);try expect(s.detail==nil && s.choice==nil && s.items.count==50,"Lead Back lost window or retained qualification")
    let late=s.beginProfile(id:3701,expected:s.control)!;s.bind(b);s.show();s.update("Business B raw",input:s.input);let current=s.control;s.accept(profile,ticket:late);try expect(s.context==b && s.query=="Business B raw" && s.control==current && s.detail==nil,"Late Lead profile changed Business B")
    s.bind(a);s.show();try expect(!s.accept(page,ticket:ticket) && s.query.isEmpty && s.items.isEmpty && s.choice==nil,"Lead Business A-B-A revived old window/input/reference")
    let pending=s.beginList(expected:s.control)!;s.hide();s.show();try expect(!s.accept(page,ticket:pending) && s.choice==nil,"Hidden Lead late list reappeared")
    return count
}
