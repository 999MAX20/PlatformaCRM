import Foundation
import CRMCore

func runClientServerSearchChecks(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let transport=RecordingTransport(FixtureTransport(directory:directory)),repo=APIReadRepository(transport:transport)
    let context=ClientSearchContext(business:101,epoch:20),other=ClientSearchContext(business:202,epoch:21)
    let base=try await repo.clients(business:101)
    let found=try await repo.searchClients(business:101,search:"\u{001C} Beyond \n")
    try expect(found.items.map(\.id)==[1701] && found.summary.total==1 && !base.items.contains(where:{$0.id==1701}),"Search filtered the original loaded list instead of source dataset")
    let request=await transport.requests.last!
    try expect(request.path=="/api/mobile/v1/clients/" && request.query==["business":"101","limit":"50","search":"Beyond"],"Native query does not use existing source parameter/limit/scope")
    let full=try await repo.searchClients(business:101,search:"Synthetic")
    try expect(full.items.count==50 && full.summary.total==56 && !full.items.contains(where:{$0.id==1701}),"Synthetic source window/count did not model filtering before50 limit")
    let notes=try await repo.searchClients(business:101,search:"fixture-note-tag")
    try expect(notes.items.map(\.id)==[1702] && ![notes.items[0].title,notes.items[0].phone,notes.items[0].email].compactMap {$0}.contains(where:{$0.contains("fixture-note-tag")}),"Source-only match reason fixture was lost")
    var s=ClientSearchSession();try expect(!s.open(expected:context),"Unbound search opened")
    s.bind(context);_=s.open(expected:context);let old=s.selection!
    try expect(!s.loaded && !s.showsEmpty && s.items.isEmpty,"Idle search asserted no matches")
    s.update("  Beyond  ",expected:old);let first=s.begin(expected:old)!
    try expect(first.query=="Beyond" && s.query=="  Beyond  " && s.loading && !s.showsEmpty,"Submission lost raw query or fabricated empty state")
    try expect(s.accept(found,request:first) && s.items.map(\.id)==[1701] && !s.partial,"Source result not accepted unchanged")
    try expect(!s.select(id:701,expected:old) && s.select(id:1701,expected:old),"Selection accepted an ID outside current results")
    let firstProfile=s.profileSelection!;_=s.select(id:1701,expected:old);let secondProfile=s.profileSelection!
    s.backProfile(expected:old,profile:firstProfile)
    try expect(s.profileSelection==secondProfile && s.selectedID==1701 && secondProfile != firstProfile,"Old profile Back closed same-ID reopened child")
    s.backProfile(expected:old,profile:secondProfile);try expect(s.query=="  Beyond  " && s.items.map(\.id)==[1701] && s.selectedID==nil,"Profile Back lost query/results")
    s.update("fixture-note-tag",expected:old);let noteTicket=s.begin(expected:old)!;_=s.accept(notes,request:noteTicket)
    try expect(s.items.map(\.id)==[1702],"Consumer re-filtered server matches by visible contact fields")
    s.update("Synthetic",expected:old);_=s.accept(full,request:s.begin(expected:old)!)
    try expect(s.partial && s.total==56 && !s.showsEmpty,"Matching count was replaced by loaded count")
    let stale=s.begin(expected:old)!;s.update("new query",expected:old);_=s.accept(found,request:stale);s.fail(.denied,request:stale)
    try expect(s.items.isEmpty && !s.loaded && s.failure==nil && !s.loading,"Late old-query response/error restored stale results")
    let failing=s.begin(expected:old)!;s.fail(.unavailable,request:failing)
    try expect(s.query=="new query" && s.failure == .unavailable && !s.showsEmpty,"Recoverable error lost input or claimed no matches")
    s.clear(expected:old);try expect(s.query.isEmpty && s.failure==nil && !s.loaded && !s.showsEmpty,"Clear did not reset query/result state")
    let empty=try await repo.searchClients(business:101,search:"does-not-exist")
    s.update("does-not-exist",expected:old);_=s.accept(empty,request:s.begin(expected:old)!)
    try expect(s.showsEmpty && s.total==0,"Confirmed empty response unavailable")
    let emptyObject: [String:Any] = ["business":101,"summary":["total":3],"items":[]]
    let partialEmpty=try JSONDecoder().decode(ClientList.self,from:JSONSerialization.data(withJSONObject:emptyObject))
    _=s.accept(partialEmpty,request:s.begin(expected:old)!);try expect(s.partial && !s.showsEmpty,"Incomplete empty window asserted no matches")
    for mutate in [0,1,2,3] {
        var object=try JSONSerialization.jsonObject(with:FixtureClientSearch.list(Data(contentsOf:directory.appendingPathComponent("client-search-catalogue-101.json")),business:101,search:"Beyond").data) as! [String:Any]
        var rows=object["items"] as! [[String:Any]]
        switch mutate {case 0:object["business"]=202;case 1:rows.append(rows[0]);object["items"]=rows;object["summary"]=["total":2];case 2:rows[0]["id"]=0;object["items"]=rows;default:object["summary"]=["total":0]}
        let bad=try JSONDecoder().decode(ClientList.self,from:JSONSerialization.data(withJSONObject:object));_=s.accept(bad,request:s.begin(expected:old)!)
        try expect(s.failure == .invalidPayload && s.items.isEmpty && !s.showsEmpty,"Malformed source result accepted")
    }
    let pending=s.begin(expected:old)!;s.close(expected:old);_=s.open(expected:context);let reopened=s.selection!
    _=s.accept(found,request:pending);s.update("old callback",expected:old);s.clear(expected:old);s.close(expected:old)
    try expect(reopened != old && s.selection==reopened && s.query=="does-not-exist" && !s.loaded,"Old presentation changed reopened search")
    s.bind(other);_=s.accept(found,request:pending)
    try expect(s.context==other && s.query.isEmpty && s.selection==nil && s.items.isEmpty,"Business switch retained query/result route")
    s.bind(ClientSearchContext(business:202,epoch:22));try expect(s.query.isEmpty && !s.loaded,"New epoch retained search")
    s.bind(ClientSearchContext(business:0,epoch:1));try expect(s.context==nil,"Invalid scope accepted")
    let unsafe="+700 &business=202/测试?x=1#fragment"
    _=try await repo.searchClients(business:101,search:unsafe)
    let encoded=try NativeRequestBuilder(origin:URL(string:"https://fixtures.invalid")!,timeout:30).request(for:await transport.requests.last!)
    let components=URLComponents(url:encoded.url!,resolvingAgainstBaseURL:false)!
    try expect(components.path=="/api/mobile/v1/clients/" && components.queryItems!.filter {$0.name=="business"}.map(\.value)==["101"] && components.queryItems!.first(where:{$0.name=="search"})?.value==unsafe,"Search text changed scope/path instead of staying one encoded query value")
    let rawCases=(try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("client-search-raw-unicode-cases.json"))) as! [String:Any])["cases"] as! [[String:Any]]
    for row in rawCases {
        let before=row["before"] as! String,after=row["after"] as! String,changed=row["changed"] as! Bool,submitted=row["after_submitted"] as! String
        var rawSession=ClientSearchSession();rawSession.bind(context);_=rawSession.open(expected:context);let owner=rawSession.selection!
        rawSession.update(before,expected:owner);let pending=rawSession.begin(expected:owner)!;rawSession.update(after,expected:owner)
        try expect(rawSession.query.utf8.elementsEqual(after.utf8),"Raw canonical-equivalent Client query was discarded: \(row["name"]!)")
        try expect(rawSession.accept(base,request:pending) == !changed,"A changed raw query kept old pending Client results")
        let current=rawSession.begin(expected:owner)!;try expect(current.query.utf8.elementsEqual(submitted.utf8) && rawSession.query.utf8.elementsEqual(after.utf8),"Request normalized raw Client query beyond source strip")
        try expect(rawSession.accept(base,request:current),"Explicit current raw query result rejected")
        _=try await repo.searchClients(business:101,search:after);let sent=await transport.requests.last!
        try expect(sent.query["search"]!.utf8.elementsEqual(submitted.utf8) && sent.query["business"]=="101" && sent.query["limit"]=="50","Raw Unicode query changed scope/limit or was normalized in repository")
    }
    return count
}
