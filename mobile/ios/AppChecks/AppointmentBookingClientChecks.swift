import Foundation
import CRMCore

@MainActor func checkAppointmentBookingClient(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let transport=ClientQueryTransport(directory),repo=APIReadRepository(transport:transport),refs=APIAppointmentReferenceRepository(transport:FixtureTransport(directory:directory)),sr=APIServiceDirectoryRepository(transport:FixtureServiceDirectoryTransport(directory:directory)),rr=APIResourceDirectoryRepository(transport:FixtureResourceDirectoryTransport(directory:directory)),port=FixtureAppointmentBookingPort(directory:directory)
    let parent=AgendaViewModel(repository:repo,initialDate:Appointment.instant("2026-10-28T07:00:00Z")!,bookingPort:port,bookingClients:repo,bookingReferences:refs,bookingServices:sr,bookingResources:rr,bookingClientSearch:repo)
    await parent.start();await parent.loadDetail(id:501);let b=parent.booking!,source=b.source!,search=b.clientChoices!,root=ClientDirectoryViewModel(repository:repo)
    await root.load(business:101,epoch:1);let rootRows=root.items
    b.open(expected:b.control);b.setStart("2026-10-29T05:00:00Z",expected:b.inputControl)
    await b.openSelector(.service,expected:b.control,serviceChild:b.serviceChoices?.control,resourceChild:b.resourceChoices?.control);let serviceOwner=b.selectorControl!,service=b.serviceChoices!
    await service.select(service.window!.items.first {$0.id==8003}!,expected:service.control);service.choose(expected:service.control);b.useService(service.choice!,child:service.control,expected:serviceOwner);b.chooseClear(expected:b.control)
    let directoryProof=b.directory,raw=b.rawStart,oldInput=b.inputControl,oldAction=b.control,before=await transport.recorded().count
    b.openClientPicker(expected:b.control,child:search.control);let owner=b.clientPickerOwner!,input=search.inputControl!,first=search.control!
    try expect(search !== root.serverSearch && !b.editing && b.inputControl==nil && !search.session.loaded && !search.session.loading && b.selector==nil,"Private Client picker reused root or started GET/default choice")
    b.setStart("stale",expected:oldInput);b.chooseClear(expected:oldAction);await b.load(.client,expected:oldAction)
    try expect(b.rawStart==raw && b.client==nil && b.directory==directoryProof && b.resource == .clear,"Old form input/actions changed retained fields during Client picker")
    search.update("é",input:input);search.update("e\u{301}",input:input)
    try expect(SourceTextIdentity.same(search.session.query,"e\u{301}") && b.matchesClientPicker(owner) && search.inputControl==input,"Continuous raw query lost combining update or revoked navigation")
    await search.submit(expected:first);let afterTyping=await transport.recorded().count
    try expect(afterTyping==before && !search.session.loading,"Typing or stale Search control sent GET")
    let rawQuery=" \u{2007} \t";search.update(rawQuery,input:input);await search.submit(expected:search.control)
    try expect(search.session.partial && search.session.items.count==50 && search.session.total==56 && !search.session.showsEmpty && b.matchesClientPicker(owner),"Partial search became complete/empty or revoked stable owner")
    let requests=await transport.recorded(),last=requests.last!
    try expect(last==ReadRequest(path:"/api/mobile/v1/clients/",query:["business":"101","limit":"50","search":""]),"Client query invented defaults/parameters or changed existing strip")
    let listControl=search.control!,id=search.session.items[0].id
    await search.openClient(id,expected:listControl);let leaf=search.control!
    let detailRequest=await transport.recorded().last!
    try expect(detailRequest==ReadRequest(path:"/api/mobile/v1/clients/1754/",query:["business":"101"]) && search.profile.detail?.client.id==1754 && b.client==nil && b.clientSelection==nil,"List row auto-applied or independent profile query changed")
    b.confirmClient(owner,search:listControl);try expect(b.client==nil,"List selection was enough to choose Client")
    await search.retryProfile(expected:leaf);b.confirmClient(owner,search:leaf);try expect(b.client==nil,"Matching profile reread revived old Use")
    let chosenRead=search.profile.readSelection!;b.confirmClient(owner,search:search.control);let proof=b.clientSelection!
    try expect(b.client?.id==1754 && proof.read==chosenRead && SourceTextIdentity.same(proof.rawQuery,rawQuery) && b.source==source && b.source?.clientID==7001 && b.directory==directoryProof && b.resource == .clear && b.rawStart==raw && b.canReview,"Explicit Use lost scope/raw/peers or rewrote immutable linked source")
    try expect(search.session.selection==nil && search.profile.detail==nil && root.items==rootRows,"Client Use retained private pending state or changed root Directory")
    b.closeClientPicker(owner);b.confirmClient(owner,search:leaf);try expect(b.clientSelection==proof,"Old Use/Close changed retained proof")
    b.openClientPicker(expected:b.control,child:search.control);let reopened=b.clientPickerOwner!
    b.closeClientPicker(owner);b.confirmClient(owner,search:leaf);try expect(b.clientPickerOwner==reopened && b.clientSelection==proof,"Old Use/Back crossed reopen")
    try expect(!b.back(expected:b.control) && b.clientPickerOwner==nil && b.presented && b.clientSelection==proof,"Parent Back closed form or lost Client choice instead of private picker")
    await b.openSelector(.resource,expected:b.control,serviceChild:b.serviceChoices?.control,resourceChild:b.resourceChoices?.control);try expect(b.clientPickerOwner==nil && b.clientSelection==proof,"Peer Resource route lost Client proof or overlapped picker");b.closeSelector(expected:b.selectorControl)
    b.prepareReview(expected:b.control);try expect(b.review?.input.clientSelection==proof && b.review?.input.directory==directoryProof,"Review lost independently read proofs")
    await b.submit(expected:b.control);let retained=b.submission!.attempt,body=try JSONSerialization.jsonObject(with:retained.body) as! [String:Any]
    try expect(b.submission?.phase == .unknown && Set(body.keys)==["business","client","service","start_at","resource"] && body["client"] as? Int==1754 && body["service"] as? Int==8003 && body["resource"] is NSNull,"Fixed booking fixture fabricated outcome or proof leaked into body")
    b.openClientPicker(expected:b.control,child:search.control);b.confirmClient(reopened,search:leaf);await b.submit(expected:b.control)
    try expect(b.retainedAttemptCount==1 && b.submission?.attempt==retained && b.clientPickerOwner==nil,"Unknown edited/repeated through Client selector")
    await parent.retryDetail(expected:parent.control);try expect(b.blocked && !b.canOpen && b.retainedAttemptCount==1,"Matching parent reread proved unknown outcome")
    await parent.load(business:202);await parent.load(business:101);await parent.loadDetail(id:501);try expect(b.blocked && !b.canOpen && b.retainedAttemptCount==1,"Business return released unknown selected Client attempt")
    func fresh(_ p:(any SyntheticAppointmentBookingPort)?=nil)->AppointmentBookingViewModel {let value=AppointmentBookingViewModel(port:p ?? port,clients:repo,references:refs,services:sr,resources:rr,clientSearch:repo);value.bind(source);value.open(expected:value.control);value.setStart(raw,expected:value.inputControl);return value}
    // Withheld/empty fields and failures remain read semantics, never fallback names or grants.
    let masked=fresh(),ms=masked.clientChoices!;masked.openClientPicker(expected:masked.control,child:ms.control);let mo=masked.clientPickerOwner!;await ms.submit(expected:ms.control)
    await transport.holdProfiles(true);let profileTask=Task {await ms.openClient(1754,expected:ms.control)};await transport.wait(0)
    let response=try FixtureClientSearch.profile(Data(contentsOf:directory.appendingPathComponent("client-search-catalogue-101.json")),business:101,id:1754)
    var object=try JSONSerialization.jsonObject(with:response.data) as! [String:Any],item=object["client"] as! [String:Any];item["title"]=NSNull();object["client"]=item
    await transport.resolve(0,ReadResponse(status:200,data:try JSONSerialization.data(withJSONObject:object)));await profileTask.value;await transport.holdProfiles(false)
    masked.confirmClient(mo,search:ms.control);try expect(masked.client?.id==1754 && masked.client?.title==nil && masked.clientSelection?.choice.title==nil,"Withheld title prevented explicit identity choice or manufactured a name")
    await masked.load(.service,expected:masked.control);masked.chooseClear(expected:masked.control);let chosen=masked.clientSelection!;masked.back(expected:masked.control)
    let candidateService=try await refs.reference(.service,business:101,id:8001),intent=AppointmentSlotIntent(business:source.read.scope.business,service:candidateService,resource:nil,day:"2026-11-02")!,slots=APIAppointmentSlotRepository(transport:FixtureAppointmentSlotTransport(directory:directory)),slotRead=try await slots.slots(intent)
    let time=AppointmentBookingCandidateTime(source:source,review:AppointmentSlotReadContext(business:source.read.scope.business,service:candidateService,resource:nil,read:slotRead)!.review(index:0)!)!
    try expect(masked.openCandidate(time,expected:masked.control) && masked.clientSelection==chosen && masked.client?.id==1754 && masked.service==candidateService && masked.resource == .clear && SourceTextIdentity.same(masked.rawStart,time.rawStart),"Candidate time transfer replaced explicit Client or inferred Client-specific availability")
    // Empty full result and partial empty window retain the original search semantics.
    masked.openClientPicker(expected:masked.control,child:ms.control);let emptyOwner=masked.clientPickerOwner!;ms.update("not-present-in-catalogue",input:ms.inputControl);await ms.submit(expected:ms.control)
    try expect(ms.session.showsEmpty && !ms.session.partial && ms.session.total==0 && masked.clientSelection==chosen,"Empty query erased retained Client or invented a result")
    let partial=ReadResponse(status:200,data:try JSONSerialization.data(withJSONObject:["business":101,"generated_at":"2026-10-29T00:00:00Z","limit":50,"items":[],"summary":["total":4,"with_phone":0,"with_email":0],"payload_budget":["target_kb":100,"max_items":50]]))
    await transport.overrideSearch(partial);await ms.submit(expected:ms.control)
    try expect(ms.session.partial && !ms.session.showsEmpty && ms.session.items.isEmpty && masked.clientSelection==chosen,"Partial empty response was presented as no matches or defaulted Client")
    masked.closeClientPicker(emptyOwner);let candidateRaw=masked.rawStart
    await masked.load(.client,expected:masked.control);try expect(masked.client?.id==7001 && masked.clientSelection==nil && masked.rawStart==candidateRaw,"Explicit legacy Client read kept conflicting proof/defaulted time")
    // Failure and late reply windows cannot select, restore old input or displace a peer selector.
    let late=fresh(),ls=late.clientChoices!;late.openClientPicker(expected:late.control,child:ls.control);let lo=late.clientPickerOwner!;await transport.overrideSearch(ReadResponse(status:403,data:Data()));await ls.submit(expected:ls.control)
    late.confirmClient(lo,search:ls.control);try expect(ls.session.failure == .denied && late.client==nil && late.matchesClientPicker(lo),"Search denial became a Client/default grant")
    await transport.holdSearch(true);let pending=Task {await ls.submit(expected:ls.control)};await transport.wait(1);let waiting=ls.control!
    late.closeClientPicker(lo);await late.openSelector(.resource,expected:late.control,serviceChild:late.serviceChoices?.control,resourceChild:late.resourceChoices?.control);let peer=late.selectorControl!
    let page=try FixtureClientSearch.list(Data(contentsOf:directory.appendingPathComponent("client-search-catalogue-101.json")),business:101,search:"")
    await transport.resolve(1,page);await pending.value;await transport.holdSearch(false);late.confirmClient(lo,search:waiting);late.closeClientPicker(lo)
    try expect(late.selectorControl==peer && ls.session.selection==nil && ls.session.items.isEmpty && late.client==nil && late.rawStart==raw,"Late query/old Back displaced Resource picker or restored closed Client window")
    late.closeSelector(expected:peer);late.openClientPicker(expected:late.control,child:ls.control);let aba=late.clientPickerOwner!;late.bind(nil);late.bind(source);late.confirmClient(aba,search:ls.control);late.closeClientPicker(aba)
    try expect(late.clientPickerOwner==nil && late.clientSelection==nil && ls.session.selection==nil && late.rawStart.isEmpty,"Source A-B-A restored old Client owner/input")
    let actorPort=MutableDirectoryBookingPort(port.grants),actor=fresh(actorPort),ac=actor.clientChoices!;actor.openClientPicker(expected:actor.control,child:ac.control);let ao=actor.clientPickerOwner!;await ac.submit(expected:ac.control);await ac.openClient(1754,expected:ac.control);actorPort.replace([]);actor.confirmClient(ao,search:ac.control)
    try expect(actor.client==nil && actor.matchesClientPicker(ao),"Profile read bypassed separate missing CREATE actor")
    actor.closeClientPicker(ao);try expect(actor.clientPickerOwner==nil && ac.session.selection==nil,"Missing actor made Client picker impossible to close")
    let noSearch=AppointmentBookingViewModel(port:port,clients:repo,references:refs);noSearch.bind(source);noSearch.open(expected:noSearch.control);noSearch.openClientPicker(expected:noSearch.control,child:nil);try expect(noSearch.clientChoices==nil && noSearch.clientPickerOwner==nil,"Default composition manufactured Client search")
    return count
}
