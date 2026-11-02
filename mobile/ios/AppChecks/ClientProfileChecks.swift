import Foundation
import CRMCore

actor ControlledProfiles: ClientProfileRepository {
    private var pending: [Int: CheckedContinuation<ClientProfile, any Error>] = [:]
    private var waiters: [Int: CheckedContinuation<Void, Never>] = [:]
    private var next = 0
    func clientProfile(business: Int, id: Int) async throws -> ClientProfile {
        let request = next; next += 1
        return try await withCheckedThrowingContinuation { pending[request] = $0; waiters.removeValue(forKey: request)?.resume() }
    }
    func wait(_ id: Int) async { if pending[id] == nil { await withCheckedContinuation { waiters[id] = $0 } } }
    func resolve(_ id: Int, _ result: Result<ClientProfile, ReadFailure>) {
        let c = pending.removeValue(forKey: id)!
        switch result { case .success(let value): c.resume(returning: value); case .failure(let error): c.resume(throwing: error) }
    }
    func cancel(_ id: Int) { pending.removeValue(forKey: id)!.resume(throwing: CancellationError()) }
}

@MainActor func checkClientProfile(directory: URL) async throws -> Int {
    func profile(_ business: Int, _ id: Int) throws -> ClientProfile {
        try JSONDecoder().decode(ClientProfile.self, from: Data(contentsOf: directory.appendingPathComponent("client-\(business)-\(id).json")))
    }
    let a = try profile(101,701), b = try profile(202,801)
    let source = ControlledProfiles()
    let model = ClientProfileViewModel(repository: source)
    let directoryModel = ClientDirectoryViewModel(repository: APIReadRepository(transport: FixtureTransport(directory: directory)))
    var count = 0, accepted = 0
    func expect(_ value: Bool, _ message: String) throws { guard value else { throw ViewModelCheckFailure(message: message) }; count += 1 }
    await directoryModel.load(business: 101); directoryModel.query = "Alpha"; directoryModel.open(id: 701)
    let first = Task { await model.load(business: 101, id: 701, onContact: { business, contact in accepted += 1; directoryModel.refreshContact(business: business, contact: contact) }) }
    await source.wait(0)
    try expect(model.loading && model.detail == nil, "Profile used cached directory while loading")
    await source.resolve(0, .failure(.denied)); await first.value
    try expect(model.failure == .denied && model.detail == nil && accepted == 0, "Denied profile used cached list data")
    let invalid = Task { await model.load(business: 101, id: 701) }; await source.wait(1)
    await source.resolve(1, .success(b)); await invalid.value
    try expect(model.failure == .invalidPayload && model.detail == nil, "Foreign Client profile accepted")
    let old = Task { await model.load(business: 101, id: 701, onContact: { _,_ in accepted += 1 }) }; await source.wait(2)
    let fresh = Task { await model.load(business: 101, id: 701, onContact: directoryModel.refreshContact) }; await source.wait(3)
    var json = try JSONSerialization.jsonObject(with: Data(contentsOf: directory.appendingPathComponent("client-101-701.json"))) as! [String:Any]
    var client = json["client"] as! [String:Any]; client["title"] = NSNull(); client["phone"] = NSNull(); client["email"] = NSNull(); json["client"] = client; json["details"] = ["notes":NSNull()]
    let withheld = try JSONDecoder().decode(ClientProfile.self, from: JSONSerialization.data(withJSONObject: json))
    await source.resolve(3, .success(withheld)); await fresh.value
    await source.resolve(2, .success(a)); await old.value
    try expect(model.detail?.client.title == nil && model.detail?.details.notes == nil && accepted == 0, "Old profile restored withheld data")
    try expect(directoryModel.selected?.title == nil && directoryModel.selected?.phone == nil, "Fresh contact was not applied to current selected row")
    directoryModel.back()
    try expect(directoryModel.query == "Alpha" && directoryModel.visible.isEmpty, "Profile Back lost query or restored old readable name")
    directoryModel.refreshContact(business: 101, contact: a.client)
    try expect(directoryModel.items[0].title == nil, "Closed Client selection accepted a profile update")
    let leaving = Task { await model.load(business: 101, id: 701) }; await source.wait(4); model.clear()
    await source.resolve(4, .success(a)); await leaving.value
    try expect(model.business == nil && model.detail == nil && !model.loading, "Back was repopulated by pending profile")
    let oldBusiness = Task { await model.load(business: 101, id: 701) }; await source.wait(5)
    let other = Task { await model.load(business: 202, id: 801) }; await source.wait(6)
    await source.resolve(6, .success(b)); await other.value
    await source.resolve(5, .failure(.unavailable)); await oldBusiness.value
    try expect(model.detail?.client.id == 801 && model.failure == nil, "Old Business error replaced current profile")
    let cancelled = Task { await model.load(business: 202, id: 801) }; await source.wait(7)
    await source.cancel(7); await cancelled.value
    try expect(!model.loading && model.detail == nil && model.failure == nil, "Cancelled profile stranded or fabricated content")
    count += try await checkClientMergeProductFlow(directory:directory)
    return count
}

private actor HeldClientMergeSource: SyntheticClientMergePreviewSource {
    let rows:[ClientMergeSnapshot]
    private var pending:[CheckedContinuation<ClientMergePreview?,Never>]=[]
    private var waits:[Int:CheckedContinuation<Void,Never>]=[:]
    init(_ rows:[ClientMergeSnapshot]) {self.rows=rows}
    func candidates(for context:ClientMergePreviewContext) async throws -> [ClientMergeSnapshot]? {rows}
    func preview(for context:ClientMergePreviewContext,duplicate:Int) async throws -> ClientMergePreview? {await withCheckedContinuation {let n=pending.count;pending.append($0);waits.removeValue(forKey:n)?.resume()}}
    func wait(_ n:Int) async {if pending.count>n {return};await withCheckedContinuation {waits[n]=$0}}
    func resolve(_ n:Int,_ value:ClientMergePreview?) {pending[n].resume(returning:value)}
    func requests() -> Int {pending.count}
}
@MainActor private func checkClientMergeProductFlow(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let source=FixtureClientMergePreviewSource(directory:directory),transport=SearchTransport(directory),repo=APIReadRepository(transport:transport)
    let owner=ClientProfileViewModel(repository:repo,editOriginSource:FixtureClientEditOriginProvider(directory:directory),mergeSource:source)
    try expect(owner.mergeEntry==nil,"Profile without exact read enabled merge entry")
    await owner.load(business:101,id:701,epoch:5);let detail=owner.detail!,read=owner.readSelection!,entry=owner.mergeEntry!,overlay=owner.localOverlayVisit
    await owner.openMerge(expected:entry);let model=owner.merge!,catalogControl=model.control!
    try expect(model.candidates.map(\.id)==[702,703] && model.selected==nil && model.result==nil && owner.mergeEntry==nil,"Merge catalog chose a duplicate or produced outcome automatically")
    try expect(owner.localOverlayVisit != overlay && owner.detail?.client.id==detail.client.id && owner.readSelection==read,"Opening local preview changed original/read identity or kept stale parent visit")
    await owner.previewMerge(expected:catalogControl);try expect(model.result==nil && model.selected==nil,"Preview ran without explicit duplicate selection")
    owner.chooseMerge(999,expected:catalogControl);try expect(model.selected==nil,"Unprovided duplicate was selected")
    owner.chooseMerge(702,expected:catalogControl);let selected=model.control!
    await owner.previewMerge(expected:selected);let value=model.result!
    try expect(value.duplicate.id==702 && value.target_client_id==701 && value.transferred.provided.count==13 && !value.will_delete_duplicate,"Exact dry-run data/counts/policy lost")
    let ready=model.control!;owner.chooseMerge(703,expected:selected)
    try expect(model.control==ready && model.result==value,"Old selected-row callback changed current preview")
    let requests=await transport.recorded();try expect(requests.count==1 && requests[0].path=="/api/mobile/v1/clients/701/" && requests[0].query==["business":"101"],"Merge preview introduced POST/GET or context query")
    try expect(owner.closeMerge(expected:ready) && owner.detail?.client.id==701 && owner.readSelection==read,"Preview Back closed parent or changed read")
    await owner.openMerge(expected:entry);try expect(model.context==nil,"A-B-A revived old merge entry")
    let freshEntry=owner.mergeEntry!;await owner.openMerge(expected:freshEntry);let reopened=model.control!;_ = owner.closeMerge(expected:ready)
    try expect(model.control==reopened,"Old dismissal closed reopened preview")
    _ = owner.closeMerge(expected:reopened)
    let beforeEdit=owner.mergeEntry!;let edit=owner.edit!;edit.open(ClientEditContext(business:101,client:701,epoch:5));let selection=edit.session.selection!
    await owner.openMerge(expected:beforeEdit);try expect(model.context==nil,"Merge entry crossed active editor")
    edit.close(selection);await owner.openMerge(expected:beforeEdit);try expect(model.context==nil && owner.mergeEntry != beforeEdit,"Editor A-B-A revived prior merge entry")
    let beforeWork=owner.mergeEntry!;await owner.work!.open(.appointment(5101),presentation:owner.work!.presentation);await owner.openMerge(expected:beforeWork)
    try expect(model.context==nil,"Merge entry crossed related work child")
    owner.work!.back();await owner.openMerge(expected:beforeWork);try expect(model.context==nil && owner.mergeEntry != beforeWork,"Work A-B-A revived prior merge entry")
    let context=ClientMergePreviewContext(business:101,target:701,epoch:5,readRevision:1),rows=try await source.candidates(for:context)!,a=try await source.preview(for:context,duplicate:702)!,b=try await source.preview(for:context,duplicate:703)!
    let held=HeldClientMergeSource(rows),late=ClientProfileViewModel(repository:repo,mergeSource:held)
    await late.load(business:101,id:701,epoch:7);await late.openMerge(expected:late.mergeEntry);let child=late.merge!;late.chooseMerge(702,expected:child.control);let firstControl=child.control!
    let first=Task {await late.previewMerge(expected:firstControl)};await held.wait(0)
    late.chooseMerge(703,expected:child.control);let nextControl=child.control!;await held.resolve(0,a);await first.value
    try expect(child.selected==703 && child.result==nil && !child.loading && child.control==nextControl,"Late preview for old duplicate replaced current choice")
    let second=Task {await late.previewMerge(expected:child.control)};await held.wait(1);await held.resolve(1,b);await second.value
    try expect(child.result==b && late.detail?.client.id==701,"Explicit selected duplicate preview failed or mutated target")
    late.chooseMerge(702,expected:child.control);await late.previewMerge(expected:firstControl)
    try expect(await held.requests()==2 && child.result==nil,"Duplicate A-B-A replayed old callback")
    let pending=Task {await late.previewMerge(expected:child.control)};await held.wait(2)
    await late.load(business:202,id:801,epoch:8);await held.resolve(2,a);await pending.value
    try expect(child.context==nil && child.result==nil && late.detail?.client.id==801,"Late preview crossed Business/target/read")
    await late.load(business:101,id:702,epoch:9);await late.openMerge(expected:late.mergeEntry)
    try expect(child.context != nil && child.failure == .invalidPayload && !child.catalogReady && child.result == nil,"Self-target candidate catalog entered supported preview")
    // A separate real fixture source carries an explicitly empty catalog for this target.
    let empty=ClientProfileViewModel(repository:repo,mergeSource:source);await empty.load(business:101,id:702,epoch:9);await empty.openMerge(expected:empty.mergeEntry)
    try expect(empty.merge!.catalogReady && empty.merge!.candidates.isEmpty && empty.merge!.result==nil,"Empty fixture invented missing/complete server result")
    let plain=ClientProfileViewModel(repository:repo);await plain.load(business:101,id:701,epoch:5)
    try expect(plain.merge==nil && plain.mergeEntry==nil,"GET/default profile inferred merge preview source or DELETE authority")
    return count
}
