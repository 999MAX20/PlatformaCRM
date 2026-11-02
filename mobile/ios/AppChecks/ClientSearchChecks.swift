import Foundation
import CRMCore

actor ClientQueryTransport: ReadTransport {
    private let fixture: FixtureTransport
    private var requests: [ReadRequest]=[]
    private var searchHeld=false,profilesHeld=false,next=0
    private var pending: [Int:CheckedContinuation<ReadResponse,any Error>]=[:]
    private var waiters: [Int:CheckedContinuation<Void,Never>]=[:]
    private var nextSearch: ReadResponse?,nextList: ReadResponse?
    init(_ directory: URL) {fixture=FixtureTransport(directory:directory)}
    func holdSearch(_ value: Bool) {searchHeld=value}
    func holdProfiles(_ value: Bool) {profilesHeld=value}
    func overrideSearch(_ response: ReadResponse) {nextSearch=response}
    func overrideList(_ response: ReadResponse) {nextList=response}
    func get(_ request: ReadRequest) async throws -> ReadResponse {
        requests.append(request)
        let search=request.path=="/api/mobile/v1/clients/" && request.query["search"] != nil
        if search,let reply=nextSearch {nextSearch=nil;return reply}
        if request.path=="/api/mobile/v1/clients/",!search,let reply=nextList {nextList=nil;return reply}
        if (search && searchHeld) || (request.path.hasPrefix("/api/mobile/v1/clients/") && Int(request.path.split(separator:"/").last ?? "") != nil && profilesHeld) {
            let index=next;next += 1
            return try await withCheckedThrowingContinuation {pending[index]=$0;waiters.removeValue(forKey:index)?.resume()}
        }
        return try await fixture.get(request)
    }
    func recorded() -> [ReadRequest] {requests}
    func wait(_ index: Int) async {if pending[index]==nil {await withCheckedContinuation {waiters[index]=$0}}}
    func resolve(_ index: Int,_ response: ReadResponse) {pending.removeValue(forKey:index)!.resume(returning:response)}
}

@MainActor func checkClientServerSearch(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func response(_ business: Int,_ query: String) throws -> ReadResponse {try FixtureClientSearch.list(Data(contentsOf:directory.appendingPathComponent("client-search-catalogue-\(business).json")),business:business,search:query)}
    let transport=ClientQueryTransport(directory),repo=APIReadRepository(transport:transport),directoryModel=ClientDirectoryViewModel(repository:repo)
    await directoryModel.load(business:101,epoch:20);directoryModel.query="Alpha"
    let parentRows=directoryModel.items,search=directoryModel.serverSearch!,a=ClientSearchContext(business:101,epoch:20)
    let initialReads=await transport.recorded().count
    search.open(a);let first=search.session.selection!
    try expect(await transport.recorded().count==initialReads && !search.session.loaded && !search.session.showsEmpty,"Search opened with implicit fetch or false empty")
    search.update("  Beyond  ",first);await search.submit(first)
    try expect(search.session.items.map(\.id)==[1701] && search.session.total==1 && search.session.query=="  Beyond  ","Owner failed source search beyond original/window50")
    let request=await transport.recorded().last!
    try expect(request.query==["business":"101","limit":"50","search":"Beyond"],"Owner invented query fields or scope")
    let beforeProfile=await transport.recorded().count
    await search.openClient(1701,first)
    try expect(search.profile.detail?.client.id==1701 && search.session.selectedID==1701,"Independent search-result Client profile failed")
    let profileRequests=await transport.recorded()
    try expect(profileRequests.count==beforeProfile+1 && transportPath(profileRequests.last)=="/api/mobile/v1/clients/1701/","Profile reused search projection instead of one independent GET")
    let oldProfile=search.session.profileSelection!;await search.openClient(1701,first);let newProfile=search.session.profileSelection!
    let beforeStaleProfile=await transport.recorded().count
    search.backProfile(first,expectedProfile:oldProfile);await search.retryProfile(first,expectedProfile:oldProfile)
    try expect(search.session.profileSelection==newProfile && search.profile.detail?.client.id==1701 && newProfile != oldProfile,"Old profile dismissal closed the reopened same-ID profile")
    try expect(await transport.recorded().count==beforeStaleProfile,"Old profile Retry issued a request for new child")
    search.backProfile(first,expectedProfile:newProfile)
    try expect(search.profile.detail==nil && search.session.query=="  Beyond  " && search.session.items.map(\.id)==[1701],"Profile Back lost search snapshot or retained profile")
    try expect(directoryModel.items==parentRows && directoryModel.query=="Alpha" && directoryModel.selectedID==nil && directoryModel.draft.session.values==ClientDraftValues(),"Search changed parent local filter/list/manual draft")
    search.update("fixture-note-tag",first);await search.submit(first)
    try expect(search.session.items.map(\.id)==[1702],"Source result was incorrectly re-filtered by visible contact fields")
    let beforeInvalid=await transport.recorded().count;await search.openClient(1701,first)
    try expect(await transport.recorded().count==beforeInvalid && search.session.selectedID==nil,"Out-of-result ID issued a profile GET")
    search.update("Synthetic",first);await search.submit(first)
    try expect(search.session.items.count==50 && search.session.total==56 && search.session.partial && !search.session.showsEmpty,"Count/window completeness was fabricated")
    let beforeClear=await transport.recorded().count;search.clear(first)
    try expect(await transport.recorded().count==beforeClear && search.session.query.isEmpty && !search.session.loaded && !search.session.showsEmpty,"Clear fetched data or kept stale rows")
    await search.submit(first);try expect(search.session.items.count==50 && search.session.total==56 && search.session.submitted=="","Explicit blank source query did not produce bounded unfiltered response")
    search.update("does-not-exist",first);await search.submit(first)
    try expect(search.session.showsEmpty && search.session.total==0,"Confirmed zero matches not distinguished")
    for status in [503,403,404] {
        search.update("Recoverable",first);await transport.overrideSearch(ReadResponse(status:status,data:Data()));await search.submit(first)
        try expect(search.session.failure != nil && search.session.query=="Recoverable" && !search.session.showsEmpty && search.session.items.isEmpty,"Search error lost input or asserted empty")
    }
    search.update("Beyond",first);await search.submit(first)
    await transport.holdProfiles(true)
    let denied=Task {await search.openClient(1701,first)};await transport.wait(0);await transport.resolve(0,ReadResponse(status:403,data:Data()));await denied.value
    try expect(search.profile.failure == .denied && search.profile.detail==nil && search.session.items.map(\.id)==[1701],"Denied target fell back to search contact or erased parent")
    search.backProfile(first);await transport.holdProfiles(false)
    await transport.holdSearch(true)
    let oldQuery=Task {await search.submit(first)};await transport.wait(1);search.update("new query",first);await transport.resolve(1,try response(101,"Beyond"));await oldQuery.value
    try expect(!search.session.loaded && search.session.items.isEmpty && search.session.query=="new query","Late old-query response reappeared")
    let clearing=Task {await search.submit(first)};await transport.wait(2);search.clear(first);await transport.resolve(2,try response(101,"Beyond"));await clearing.value
    try expect(!search.session.loaded && search.session.query.isEmpty,"Clear did not invalidate pending result")
    search.update("Beyond",first);let closing=Task {await search.submit(first)};await transport.wait(3);search.close(first);search.open(a);let fresh=search.session.selection!
    search.update("stale callback",first);search.clear(first);search.close(first)
    await transport.resolve(3,try response(101,"Beyond"));await closing.value
    try expect(fresh != first && search.session.selection==fresh && search.session.query=="Beyond" && !search.session.loaded,"Late route close/edit/result changed reopened query")
    let foreign=Task {await search.submit(fresh)};await transport.wait(4);await directoryModel.load(business:202,epoch:21)
    try expect(search.session.selection==nil && search.session.query.isEmpty && search.profile.detail==nil,"Business invalidation waited for pending search")
    await transport.resolve(4,try response(101,"Beyond"));await foreign.value
    try expect(search.session.context==ClientSearchContext(business:202,epoch:21) && search.session.items.isEmpty,"Foreign result entered new Business")
    await transport.holdSearch(false);let b=ClientSearchContext(business:202,epoch:21);search.open(b);let token=search.session.selection!;search.update("Beyond",token);await search.submit(token)
    try expect(search.session.items.map(\.id)==[2701],"Business search dataset mixed IDs")
    await transport.holdProfiles(true);let lateProfile=Task {await search.openClient(2701,token)};await transport.wait(5)
    await directoryModel.load(business:101,epoch:22)
    let profileResponse=try FixtureClientSearch.profile(Data(contentsOf:directory.appendingPathComponent("client-search-catalogue-202.json")),business:202,id:2701)
    await transport.resolve(5,profileResponse);await lateProfile.value
    try expect(search.profile.detail==nil && search.profile.id==nil && search.session.selection==nil,"Late old-Business profile survived owner invalidation")
    let c=ClientSearchContext(business:101,epoch:22);search.open(c);let current=search.session.selection!;search.update("Retained manual query",current)
    await transport.overrideList(ReadResponse(status:503,data:Data()));await directoryModel.load(business:101,epoch:22)
    try expect(search.session.selection==current && search.session.query=="Retained manual query","Recoverable same-scope parent error erased input")
    await transport.overrideList(ReadResponse(status:403,data:Data()));await directoryModel.load(business:101,epoch:22)
    try expect(search.session.selection==nil && search.session.context==nil && search.session.query.isEmpty,"Denied parent scope retained child context")
    return count
}
private func transportPath(_ request: ReadRequest?) -> String? {request?.path}
