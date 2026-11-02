import Foundation
import CRMCore

actor ControlledClientCreatePort:SyntheticClientCreatePort {
    nonisolated let grants:[SyntheticClientCreateGrant]
    private var attempts:[ClientCreateAttempt]=[]
    private var pending:[Int:CheckedContinuation<SyntheticClientCreateOutcome,any Error>]=[:]
    private var waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    init(create:Bool=true) {grants=[SyntheticClientCreateGrant(business:101,actor:9001,create:create),SyntheticClientCreateGrant(business:202,actor:9002,create:create)]}
    func execute(_ attempt:ClientCreateAttempt) async throws -> SyntheticClientCreateOutcome {let id=attempts.count;attempts.append(attempt);return try await withCheckedThrowingContinuation {pending[id]=$0;waiters.removeValue(forKey:id)?.resume()}}
    func wait(_ id:Int) async {if pending[id]==nil {await withCheckedContinuation {waiters[id]=$0}}}
    func recorded()->[ClientCreateAttempt] {attempts}
    func resolve(_ id:Int,_ outcome:SyntheticClientCreateOutcome) {pending.removeValue(forKey:id)!.resume(returning:outcome)}
    func loseReply(_ id:Int) {pending.removeValue(forKey:id)!.resume(throwing:ReadFailure.unavailable)}
}

@MainActor func checkClientCreation(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let transport=SearchTransport(directory),repo=APIReadRepository(transport:transport),context=ClientDraftContext(business:101,epoch:1)
    func review(_ m:ClientDraftViewModel,_ c:ClientDraftContext)->ClientDraftReview {m.open(c);let s=m.session.selection!;for (f,v) in [(ClientDraftField.fullName,"  Manual client\n"),(.phone,"  +7 123\n"),(.email,"alpha@example.invalid"),(.notes,"  Manual notes\n")] {m.update(f,v,s)};m.prepare(s);return m.session.review!}
    func response(_ a:ClientCreateAttempt)->SyntheticClientCreateOutcome {let v=a.review.preview;return .response(status:201,client:ClientContact(id:87001,title:nil,phone:v.phone,email:v.email,business:a.authorization.context.business,full_name:v.fullName,source:v.source,notes:v.notes,created_at:"2026-10-30T12:00:00Z",updated_at:"2026-10-30T12:00:00Z"))}
    let port=ControlledClientCreatePort(),owner=ClientDirectoryViewModel(repository:repo,createSubmission:port)
    await owner.load(business:101,epoch:1);owner.query="Own filter";let m=owner.draft,old=review(m,context),rows=owner.items,total=owner.total,reads=await transport.recorded()
    m.back(old.selection);m.update(.fullName,"Changed",old.selection);m.prepare(old.selection);await m.submit(old)
    try expect(await port.recorded().isEmpty,"Old Client review submitted changed input")
    let current=m.session.review!,sending=Task {await m.submit(current)};await port.wait(0);await m.submit(current);m.update(.notes,"overwrite",current.selection);m.discard(current.selection)
    try expect(await port.recorded().count==1 && m.submission?.phase == .pending && m.session.values.notes=="  Manual notes\n","Pending Client CREATE repeated/edited/cleared")
    m.back(current.selection);m.open(context);let fresh=m.session.selection!,sent=await port.recorded()[0];await port.resolve(0,response(sent));await sending.value
    try expect(m.submission?.phase == .confirmed && m.submission?.client?.full_name=="Changed","Verified existing ClientSerializer body did not reach synthetic result")
    try expect(await transport.recorded()==reads && owner.items==rows && owner.total==total && owner.query=="Own filter","Fake Client create inserted/contact-refreshed real rows or issued lookup/duplicate request")
    m.acknowledge(current.selection,attemptID:1);try expect(m.submission?.phase == .confirmed,"Old Client sheet acknowledged new result")
    m.acknowledge(fresh,attemptID:1);try expect(m.session.values==ClientDraftValues() && m.session.selection==nil && m.retainedAttemptCount==1,"Client fake success close failed to clear own form/retain attempt")
    let rejection=review(m,context),rejecting=Task {await m.submit(rejection)};await port.wait(1);await port.resolve(1,.rejectedWithoutWrite);await rejecting.value
    m.close(rejection.selection);m.open(context);let e=m.session.selection!;m.acknowledge(e,attemptID:2)
    try expect(m.session.phase == .editing && m.session.selection==e && m.session.values==rejection.values,"Reopened no-write Client error failed raw editor return")
    await m.submit(rejection);try expect(await port.recorded().count==2,"Client error retried without explicit fresh preview")
    m.prepare(e);let u=m.session.review!,unknown=Task {await m.submit(u)};await port.wait(2);await port.loseReply(2);await unknown.value
    m.acknowledge(e,attemptID:2);m.acknowledge(e,attemptID:3);m.discard(e);await m.submit(u)
    try expect(await port.recorded().count==3 && m.submission?.phase == .unknown && m.session.values==u.values,"Unknown Client CREATE discarded/replayed or lost raw")
    owner.open(id:rows[0].id);try expect(m.session.selection==nil && m.retainedAttemptCount==3,"Directory profile navigation erased attempt or retained create sheet")
    owner.back();m.open(context);try expect(m.submission?.phase == .unknown && !m.canSubmit && m.session.values==u.values,"Client Back/reread inferred outcome")

    let racePort=ControlledClientCreatePort(),raceOwner=ClientDirectoryViewModel(repository:repo,createSubmission:racePort)
    await raceOwner.load(business:101,epoch:10);let race=raceOwner.draft,r=review(race,ClientDraftContext(business:101,epoch:10)),racing=Task {await race.submit(r)};await racePort.wait(0);let attempt=await racePort.recorded()[0],beforeOwner=await transport.recorded()
    raceOwner.reconcileOwner(business:202,epoch:11)
    try expect(raceOwner.business==nil && raceOwner.items.isEmpty && race.session.context==nil && race.submission==nil && race.session.values==ClientDraftValues(),"Off-tab root owner retained old Client directory/form")
    try expect(await transport.recorded()==beforeOwner,"Root Client owner invalidation issued a read")
    await raceOwner.load(business:202,epoch:11);await racePort.resolve(0,response(attempt));await racing.value
    try expect(race.submission==nil && race.session.values==ClientDraftValues() && race.retainedAttemptCount==1,"Late old Client CREATE leaked into new Business")
    await raceOwner.load(business:101,epoch:12);let nc=ClientDraftContext(business:101,epoch:12);race.open(nc)
    try expect(race.submission==nil && race.submissionBlocked && !race.canSubmit,"New epoch exposed/replayed old Client creation")
    let cancelPort=ControlledClientCreatePort(),cancelOwner=ClientDirectoryViewModel(repository:repo,createSubmission:cancelPort)
    await cancelOwner.load(business:101,epoch:20);let cm=cancelOwner.draft,c=review(cm,ClientDraftContext(business:101,epoch:20)),cancelling=Task {await cm.submit(c)};await cancelPort.wait(0);cancelling.cancel();let ca=await cancelPort.recorded()[0];await cancelPort.resolve(0,response(ca));await cancelling.value
    try expect(cm.submission?.phase == .unknown && cm.submissionBlocked,"Cancelled Client CREATE inferred no write/success")
    for candidate in [ClientDirectoryViewModel(repository:repo),ClientDirectoryViewModel(repository:repo,createSubmission:ControlledClientCreatePort(create:false))] {await candidate.load(business:101,epoch:30);let local=candidate.draft,v=review(local,ClientDraftContext(business:101,epoch:30));await local.submit(v);try expect(!local.canSubmit && local.retainedAttemptCount==0,"Client VIEW/default dependency inferred CREATE")}
    let fixtureOwner=ClientDirectoryViewModel(repository:repo,createSubmission:FixtureClientCreatePort(directory:directory))
    for (b,p) in [(101,ClientCreateAttemptPhase.confirmed),(202,.unknown)] {await fixtureOwner.load(business:b,epoch:40);let local=fixtureOwner.draft,v=review(local,ClientDraftContext(business:b,epoch:40));await local.submit(v);try expect(local.submission?.phase==p,"Explicit DEBUG Client CREATE outcome unreachable")}

    let controlled=ControlledClients(),pendingOwner=ClientDirectoryViewModel(repository:controlled)
    let reading=Task {await pendingOwner.load(business:101,epoch:50)};await controlled.wait(0);pendingOwner.reconcileOwner(business:101,epoch:51)
    let page=try JSONDecoder().decode(ClientList.self,from:Data(contentsOf:directory.appendingPathComponent("clients-101.json")));await controlled.resolve(0,.success(page));await reading.value
    try expect(pendingOwner.business==nil && pendingOwner.items.isEmpty && pendingOwner.draft.session.context==nil,"Late directory read repopulated same Business/new epoch")
    let profiles=ControlledProfiles(),profileOwner=ClientProfileViewModel(repository:profiles)
    let pendingProfile=Task {await profileOwner.load(business:101,id:701,epoch:60)};await profiles.wait(0);profileOwner.reconcileOwner(business:101,epoch:61)
    let profile=try JSONDecoder().decode(ClientProfile.self,from:Data(contentsOf:directory.appendingPathComponent("client-101-701.json")));await profiles.resolve(0,.success(profile));await pendingProfile.value
    try expect(profileOwner.business==nil && profileOwner.detail==nil && profileOwner.scopeEpoch==nil,"Off-tab same Business/new epoch profile resurrected")
    return count
}
