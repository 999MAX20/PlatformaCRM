import Foundation
import CRMCore

@MainActor func checkClientDraft(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws { guard value else { throw ViewModelCheckFailure(message:message) };count += 1 }
    let transport=SearchTransport(directory),repo=APIReadRepository(transport:transport),model=ClientDirectoryViewModel(repository:repo)
    let context=ClientDraftContext(business:101,epoch:7)
    await model.load(business:101,epoch:7);model.query="Alpha";let rows=model.items.map(\.id),reads=await transport.recorded().count
    model.draft.open(context);let selection=model.draft.session.selection!
    model.draft.update(.fullName,"Synthetic local draft",selection);model.draft.update(.phone,"+70000000000",selection);model.draft.update(.notes,"Synthetic note",selection)
    model.draft.prepare(selection)
    try expect(model.draft.session.phase == .review && model.draft.session.review?.values.source == "manual","Directory draft did not reach local review")
    try expect(model.items.map(\.id)==rows && model.query=="Alpha" && model.selectedID==nil,"Draft created a server-looking list record or changed query")
    try expect(await transport.recorded().count==reads,"Preparing/reviewing draft issued an API request")
    model.draft.back(selection);model.draft.back(selection);try expect(model.draft.session.values.fullName=="Synthetic local draft" && model.query=="Alpha","Back lost input/list context")
    model.draft.open(context);let current=model.draft.session.selection!;model.draft.discard(selection)
    try expect(model.draft.session.selection==current,"Stale sheet dismissal cleared current draft")
    model.back();try expect(model.draft.session.selection==nil && model.draft.session.values.notes=="Synthetic note","Tab/route close discarded local draft")
    await model.load(business:202,epoch:8)
    try expect(model.draft.session.context==ClientDraftContext(business:202,epoch:8) && model.draft.session.values==ClientDraftValues(),"Directory Business change retained previous input")
    model.draft.update(.notes,"old event",current);try expect(model.draft.session.values.notes.isEmpty,"Late old draft callback entered new Business")
    let controlled=ControlledClients();let owner=ClientDirectoryViewModel(repository:controlled)
    let start=Task { await owner.load(business:101,epoch:10) };await controlled.wait(0)
    let list=try JSONDecoder().decode(ClientList.self,from:Data(contentsOf:directory.appendingPathComponent("clients-101.json")));await controlled.resolve(0,.success(list));await start.value
    owner.draft.open(ClientDraftContext(business:101,epoch:10));let pending=owner.draft.session.selection!;owner.draft.update(.fullName,"Retain after error",pending)
    let retry=Task { await owner.load(business:101,epoch:10) };await controlled.wait(1);await controlled.resolve(1,.failure(.unavailable));await retry.value
    try expect(owner.failure == .unavailable && owner.draft.session.values.fullName=="Retain after error" && owner.draft.session.selection==pending,"Recoverable same-context list error erased form")
    let foreign=Task { await owner.load(business:202,epoch:11) };await controlled.wait(2)
    try expect(owner.draft.session.selection==nil && owner.draft.session.values.fullName.isEmpty,"Context invalidation waited for network")
    await controlled.resolve(2,.failure(.denied));await foreign.value
    try expect(owner.failure == .denied && owner.draft.session.values.fullName.isEmpty,"Denied context restored foreign draft")
    count += try await checkClientDuplicateFixtureReview(directory:directory)
    return count
}

private actor HeldClientDuplicateSource: SyntheticClientDuplicatePreviewSource {
    private var continuations:[CheckedContinuation<ClientDuplicateResponse?,Never>]=[]
    private var waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    func preview(for input:ClientDuplicatePreviewInput) async throws -> ClientDuplicateResponse? {
        await withCheckedContinuation {continuation in let i=continuations.count;continuations.append(continuation);waiters.removeValue(forKey:i)?.resume()}
    }
    func wait(_ i:Int) async {if continuations.count>i {return};await withCheckedContinuation {waiters[i]=$0}}
    func finish(_ i:Int,_ value:ClientDuplicateResponse?) {continuations[i].resume(returning:value)}
}
@MainActor private func checkClientDuplicateFixtureReview(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let source=FixtureClientDuplicatePreviewSource(directory:directory),context=ClientDraftContext(business:101,epoch:9)
    let input=ClientDuplicatePreviewInput(context:context,phone:"+70000000000",email:"")
    let provided=try await source.preview(for:input)!
    try expect(provided.duplicates.first?.id==701,"Explicit Business101 fixture lookup failed")
    try expect(try await source.preview(for:ClientDuplicatePreviewInput(context:ClientDraftContext(business:202,epoch:9),phone:input.phone,email:""))?.duplicates.first?.id==801,"Duplicate fixture crossed Business")
    try expect(try await source.preview(for:ClientDuplicatePreviewInput(context:context,phone:"+70000000000 ",email:""))==nil,"Fixture lookup normalized input into invented server result")
    try expect(try await source.preview(for:ClientDuplicatePreviewInput(context:context,phone:"",email:"ALPHA@example.invalid"))==nil,"Fixture lookup performed server email matching")
    try expect(try await source.preview(for:ClientDuplicatePreviewInput(context:ClientDraftContext(business:0,epoch:9),phone:input.phone,email:""))==nil,"Invalid local context got fixture result")
    let transport=SearchTransport(directory),owner=ClientDirectoryViewModel(repository:APIReadRepository(transport:transport),duplicateSource:source)
    await owner.load(business:101,epoch:9);let rows=owner.items.map(\.id),reads=await transport.recorded().count
    let model=owner.draft;model.open(context);let selection=model.session.selection!
    model.update(.fullName,"Unsent owner input",selection);model.update(.phone,input.phone,selection);model.update(.notes,"Private unsent note",selection);model.prepare(selection)
    let control=model.control!,visit=model.duplicates!.visit,review=model.session.review!
    await model.loadDuplicates(expected:control,visit:visit)
    try expect(model.duplicates!.result==provided && model.session.review==review && model.session.values.notes=="Private unsent note","Duplicate preview rewrote draft/review or failed result")
    let currentReads=await transport.recorded().count
    try expect(!model.canSubmit && model.retainedAttemptCount==0 && owner.items.map(\.id)==rows && currentReads==reads,"Duplicate fixture/read inferred CREATE authority, list record or POST/GET")
    let loadedVisit=model.duplicates!.visit;await model.loadDuplicates(expected:control,visit:visit)
    try expect(model.duplicates!.visit==loadedVisit,"Stale preview callback repeated lookup")
    model.back(selection);try expect(model.duplicates!.result==nil && model.session.values.fullName=="Unsent owner input","Review Back retained stale duplicates or lost input")
    model.prepare(selection);await model.loadDuplicates(expected:control,visit:loadedVisit)
    try expect(model.duplicates!.result==nil,"A-B-A review revived old duplicate control")
    await model.loadDuplicates(expected:model.control,visit:model.duplicates!.visit)
    let questionControl=model.control!;model.askClear(expected:questionControl)
    try expect(model.duplicates!.result==nil && model.session.values.notes=="Private unsent note","Clear question did not revoke duplicates or erased input")
    model.dismissClear(model.clearConfirmation!);model.close(selection);model.open(context);let reopened=model.session.selection!;model.prepare(reopened)
    try expect(model.duplicates!.result==nil && model.session.values.notes=="Private unsent note","Reopen reused result or discarded input")
    let held=HeldClientDuplicateSource(),late=ClientDraftViewModel(duplicates:held);late.bind(context);late.open(context);let old=late.session.selection!
    late.update(.fullName,"Held draft",old);late.prepare(old);let oldControl=late.control!,oldVisit=late.duplicates!.visit
    let request=Task {await late.loadDuplicates(expected:oldControl,visit:oldVisit)};await held.wait(0)
    try expect(late.duplicates!.loading,"Held fixture preview not loading")
    late.back(old);late.prepare(old);let next=late.control!
    await held.finish(0,provided);await request.value
    try expect(late.control==next && late.duplicates!.result==nil && !late.duplicates!.loading && late.session.values.fullName=="Held draft","Late preview entered a fresh review")
    let freshVisit=late.duplicates!.visit;let second=Task {await late.loadDuplicates(expected:next,visit:freshVisit)};await held.wait(1)
    late.bind(ClientDraftContext(business:202,epoch:10));await held.finish(1,provided);await second.value
    try expect(late.session.context?.business==202 && late.duplicates!.result==nil && late.session.values.fullName.isEmpty,"Late duplicate result crossed Business/epoch")
    let readOnly=ClientDraftViewModel();readOnly.bind(context);readOnly.open(context);let readSelection=readOnly.session.selection!;readOnly.update(.fullName,"No injected source",readSelection);readOnly.prepare(readSelection)
    try expect(readOnly.duplicates==nil && !readOnly.canSubmit,"GET/default composition created duplicate/command provider")
    let empty=ClientDuplicatePreviewViewModel(source:source);await empty.load(ClientDuplicatePreviewInput(context:context,phone:"",email:""),expected:empty.visit)
    try expect(empty.result?.duplicates.isEmpty==true && empty.failure==nil,"Explicit empty fixture was not a result")
    await empty.load(ClientDuplicatePreviewInput(context:context,phone:"missing",email:""),expected:empty.visit)
    try expect(empty.result==nil && empty.failure == .unavailable,"Missing fixture claimed no server duplicates")
    let unknownPort=UnknownClientCreateForDuplicateChecks(),unknown=ClientDraftViewModel(port:unknownPort,duplicates:source)
    unknown.bind(context);unknown.open(context);let unknownSelection=unknown.session.selection!
    unknown.update(.fullName,"Unknown unsent owner",unknownSelection);unknown.update(.phone,input.phone,unknownSelection);unknown.prepare(unknownSelection)
    let unknownControl=unknown.control!,unknownVisit=unknown.duplicates!.visit
    await unknown.loadDuplicates(expected:unknownControl,visit:unknownVisit);try expect(unknown.duplicates!.result != nil,"Unknown guard scenario never loaded preview")
    await unknown.submit(unknown.session.review!,expected:unknownControl)
    let retained=unknown.submission!
    try expect(retained.phase == .unknown && unknown.retainedAttemptCount==1 && unknown.duplicates!.result==nil && unknown.session.values.fullName=="Unknown unsent owner","Submission did not revoke duplicate preview or retain unknown input/attempt")
    await unknown.loadDuplicates(expected:unknown.control,visit:unknown.duplicates!.visit)
    try expect(unknown.submission==retained && unknown.retainedAttemptCount==1 && unknown.duplicates!.result==nil && !unknown.canSubmit,"Duplicate lookup resolved/replayed independent unknown create")
    let denied=ClientDuplicatePreviewViewModel(source:DeniedClientDuplicateSource())
    await denied.load(input,expected:denied.visit)
    try expect(denied.failure == .denied && denied.result==nil,"Synthetic preview denial lost existing read failure kind")
    return count
}

private struct UnknownClientCreateForDuplicateChecks: SyntheticClientCreatePort {
    let grants=[SyntheticClientCreateGrant(business:101,actor:5001,create:true)]
    func execute(_ attempt:ClientCreateAttempt) async throws -> SyntheticClientCreateOutcome {.unknown}
}
private struct DeniedClientDuplicateSource: SyntheticClientDuplicatePreviewSource {
    func preview(for input:ClientDuplicatePreviewInput) async throws -> ClientDuplicateResponse? {throw ReadFailure.denied}
}
