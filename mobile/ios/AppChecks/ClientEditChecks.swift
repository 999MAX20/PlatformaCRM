import Foundation
import CRMCore

actor ControlledEditOrigins: ClientEditOriginProvider {
    private var pending: [Int:CheckedContinuation<ClientEditOrigin?,Never>]=[:]
    private var waiters: [Int:CheckedContinuation<Void,Never>]=[:]
    private var next=0
    func origin(for profile: ClientProfile) async -> ClientEditOrigin? {
        let id=next;next += 1
        return await withCheckedContinuation {pending[id]=$0;waiters.removeValue(forKey:id)?.resume()}
    }
    func wait(_ id: Int) async {if pending[id]==nil {await withCheckedContinuation {waiters[id]=$0}}}
    func resolve(_ id: Int,_ value: ClientEditOrigin?) {pending.removeValue(forKey:id)!.resume(returning:value)}
}

@MainActor func checkClientEdit(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let source=FixtureClientEditOriginProvider(directory:directory)
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory))
    let a=try await repo.clientProfile(business:101,id:701),b=try await repo.clientProfile(business:202,id:801)
    guard let origin=await source.origin(for:a) else {throw ViewModelCheckFailure(message:"Complete fixture origin missing")}
    let other=await source.origin(for:b)
    try expect(other==nil,"Unknown Business202 email was treated as blank")
    let opaque=ClientProfileViewModel(repository:repo)
    await opaque.load(business:101,id:701,epoch:10)
    try expect(opaque.edit==nil && opaque.detail?.client.id==701,"Opaque repository was granted fixture edit capability")
    let unscoped=ClientProfileViewModel(repository:repo,editOriginSource:source)
    await unscoped.load(business:101,id:701)
    try expect(unscoped.edit?.session.context==nil && unscoped.edit?.session.available==false,"No owner epoch enabled edit")
    let transport=SearchTransport(directory),recorded=APIReadRepository(transport:transport)
    let list=ClientDirectoryViewModel(repository:recorded)
    await list.load(business:101,epoch:10);list.query="Alpha";list.open(id:701)
    let model=ClientProfileViewModel(repository:recorded,editOriginSource:source)
    var callbacks=0
    await model.load(business:101,id:701,epoch:10,onContact:{business,contact in callbacks += 1;list.refreshContact(business:business,contact:contact)})
    let rows=list.items,reads=await transport.recorded(),contact=model.detail!.client
    let edit=model.edit!,context=ClientEditContext(business:101,client:701,epoch:10)
    edit.open(context);let first=edit.session.selection!
    edit.update(.fullName,"Synthetic unsent edit",first);edit.prepare(first)
    try expect(edit.session.phase == .review && edit.session.review?.changed==[.fullName],"Independent profile edit failed to reach local diff review")
    try expect(edit.session.review?.original==origin.values && edit.session.review?.values.fullName=="Synthetic unsent edit","Review lost exact independent original")
    try expect(await transport.recorded()==reads && callbacks==1,"Local review issued request or invoked source refresh")
    try expect(list.items==rows && list.query=="Alpha" && list.selectedID==701 && model.detail?.client==contact,"Unsent edit mutated Directory/profile data")
    edit.back(first);edit.close(first);model.clear()
    try expect(edit.session.values==nil && edit.session.context==nil && model.detail==nil,"Parent Back leaked edit buffer")
    await model.load(business:101,id:701,epoch:10)
    try expect(edit.session.values?.fullName=="Synthetic unsent edit" && edit.session.available,"Fresh matching return failed to restore own edit")
    edit.open(context);edit.cancel(edit.session.selection!)
    try expect(edit.session.values==origin.values && model.detail?.client==contact,"Explicit cancel changed source or failed to restore original")
    let controlled=ControlledProfiles(),owner=ClientProfileViewModel(repository:controlled,editOriginSource:source)
    let start=Task {await owner.load(business:101,id:701,epoch:20)};await controlled.wait(0);await controlled.resolve(0,.success(a));await start.value
    let session=owner.edit!,c=ClientEditContext(business:101,client:701,epoch:20)
    session.open(c);let old=session.session.selection!;session.update(.phone,"Unsent phone",old)
    for (n,problem) in [ReadFailure.denied,.unavailable].enumerated() {
        let failure=Task {await owner.load(business:101,id:701,epoch:20)};await controlled.wait(1+n*2)
        try expect(session.session.values==nil && session.session.selection==nil && owner.detail==nil,"Retry exposed old form before independent read")
        await controlled.resolve(1+n*2,.failure(problem));await failure.value
        try expect(owner.failure==problem && session.session.values==nil && !session.session.available,"403/503 fabricated editable original")
        let recovery=Task {await owner.load(business:101,id:701,epoch:20)};await controlled.wait(2+n*2);await controlled.resolve(2+n*2,.success(a));await recovery.value
        try expect(session.session.available && session.session.values?.phone=="Unsent phone","Recoverable source failure erased own private draft")
    }
    var json=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("client-101-701.json"))) as! [String:Any]
    var client=json["client"] as! [String:Any];client["phone"]="+7***0001";json["client"]=client
    let masked=try JSONDecoder().decode(ClientProfile.self,from:JSONSerialization.data(withJSONObject:json))
    let changed=Task {await owner.load(business:101,id:701,epoch:20)};await controlled.wait(5);await controlled.resolve(5,.success(masked));await changed.value
    try expect(owner.detail?.client.phone=="+7***0001" && !session.session.available && session.session.needsReset && session.session.hasStoredChanges,"Changed independent projection silently rebased local input")
    session.discardStored(c);try expect(!session.session.available && session.session.values==nil,"Discard of unknown origin populated blanks")
    let delayed=ControlledEditOrigins(),races=ClientProfileViewModel(repository:repo,editOriginSource:delayed)
    var accepted:[Int]=[]
    let oldProvider=Task {await races.load(business:101,id:701,epoch:30,onContact:{_,contact in accepted.append(contact.id)})};await delayed.wait(0)
    let newProvider=Task {await races.load(business:202,id:801,epoch:31,onContact:{_,contact in accepted.append(contact.id)})};await delayed.wait(1)
    await delayed.resolve(1,other);await newProvider.value;await delayed.resolve(0,origin);await oldProvider.value
    try expect(races.business==202 && races.detail?.client.id==801 && accepted==[801],"Late origin response published old Business profile/callback")
    try expect(races.edit?.session.context==ClientEditContext(business:202,client:801,epoch:31) && races.edit?.session.origin==other && races.edit?.session.available==false,"Late origin populated wrong edit owner")
    let sameID=Task {await races.load(business:101,id:701,epoch:32)};await delayed.wait(2)
    let newEpoch=Task {await races.load(business:101,id:701,epoch:33)};await delayed.wait(3)
    await delayed.resolve(2,origin);await sameID.value
    try expect(races.loading && races.detail==nil && races.edit?.session.values==nil,"Same-ID prior epoch origin ended current loading")
    await delayed.resolve(3,origin);await newEpoch.value
    try expect(races.scopeEpoch==33 && races.edit?.session.values==origin.values,"Current same-ID epoch failed to load")
    let leaving=Task {await races.load(business:101,id:701,epoch:33)};await delayed.wait(4);races.clear();await delayed.resolve(4,origin);await leaving.value
    try expect(races.detail==nil && races.edit?.session.values==nil && races.scopeEpoch==nil,"Parent clear was repopulated by late origin provider")
    let pendingSource=Task {await owner.load(business:101,id:701,epoch:40)};await controlled.wait(6)
    let currentSource=Task {await owner.load(business:202,id:801,epoch:41)};await controlled.wait(7)
    await controlled.resolve(7,.success(b));await currentSource.value;await controlled.resolve(6,.success(a));await pendingSource.value
    try expect(owner.detail?.client.id==801 && owner.edit?.session.origin==other,"Late independent profile restored old Business edit")
    return count
}
