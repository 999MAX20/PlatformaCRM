import Foundation
import CRMCore

final class MutableDirectoryBookingPort:SyntheticAppointmentBookingPort,@unchecked Sendable {
    private let lock=NSLock();private var values:[SyntheticAppointmentBookingGrant]
    init(_ values:[SyntheticAppointmentBookingGrant]) {self.values=values}
    var grants:[SyntheticAppointmentBookingGrant] {lock.lock();defer {lock.unlock()};return values}
    func replace(_ values:[SyntheticAppointmentBookingGrant]) {lock.lock();defer {lock.unlock()};self.values=values}
    func execute(_ attempt:AppointmentBookingAttempt) async throws -> SyntheticAppointmentBookingOutcome {.unknown}
}
@MainActor func checkAppointmentBookingDirectory(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),refs=APIAppointmentReferenceRepository(transport:FixtureTransport(directory:directory)),sr=APIServiceDirectoryRepository(transport:FixtureServiceDirectoryTransport(directory:directory)),rr=APIResourceDirectoryRepository(transport:FixtureResourceDirectoryTransport(directory:directory)),port=FixtureAppointmentBookingPort(directory:directory),date=Appointment.instant("2026-10-28T07:00:00Z")!
    let parent=AgendaViewModel(repository:repo,initialDate:date,bookingPort:port,bookingClients:repo,bookingReferences:refs,serviceRepository:sr,resourceRepository:rr,bookingServices:sr,bookingResources:rr)
    await parent.start();await parent.loadDetail(id:501);let b=parent.booking!,source=b.source!,original=parent.session.detail!,items=parent.session.items
    b.open(expected:b.control);b.setStart("2026-10-29T05:00:00Z",expected:b.inputControl);await b.load(.client,expected:b.control);let client=b.client,raw=b.rawStart,oldInput=b.inputControl,oldAction=b.control
    let service=b.serviceChoices!,resource=b.resourceChoices!
    await b.openSelector(.service,expected:b.control,serviceChild:service.control,resourceChild:resource.control);let firstSession=b.selectorControl!
    try expect(service.presented && !resource.presented && !b.editing && b.inputControl==nil && parent.services?.owner==nil && parent.resources?.owner==nil,"Form reused root directory route or left peer/input editable")
    b.setStart("stale",expected:oldInput);b.chooseClear(expected:oldAction);await b.load(.service,expected:oldAction)
    try expect(b.rawStart==raw && b.resource==nil && b.service==nil && b.client==client,"Old form controls changed pending selector input/choices")
    let row=service.window!.items.first {$0.id==8003}!;await service.select(row,expected:service.control);service.choose(expected:service.control)
    let selected=service.choice!,leaf=service.control!
    try expect(b.service==nil && b.directory==nil && b.selectorControl==firstSession,"Read choice automatically applied or detail loading revoked navigation ownership")
    b.useService(selected,child:leaf,expected:firstSession)
    try expect(b.service?.id==8003 && b.directory?.service==selected.item && b.directory?.resource==nil && b.resource==nil && b.rawStart==raw && b.client==client && b.selector==nil && service.owner==nil,"Explicit Service use lost proof/input or copied Resource/default/grant")
    b.useService(selected,child:leaf,expected:firstSession);b.closeSelector(expected:firstSession)
    try expect(b.service?.id==8003 && !b.canReview,"Old selector use/close changed current form or skipped explicit Resource")
    await b.openSelector(.resource,expected:b.control,serviceChild:service.control,resourceChild:resource.control);let resourceSession=b.selectorControl!
    await resource.select(resource.window!.items.first {$0.id==9003}!,expected:resource.control);resource.choose(expected:resource.control);let chosenResource=resource.choice!,resourceLeaf=resource.control!
    b.useResource(chosenResource,child:resourceLeaf,expected:resourceSession)
    try expect(b.resource?.id==9003 && b.directory?.service==selected.item && b.directory?.resource==chosenResource.item && b.canReview && b.rawStart==raw && b.client==client,"Resource selection discarded Service/input or defaulted unknown/inactive type")
    let sourceStill=b.source!;try expect(sourceStill==source && sourceStill.serviceID==8001 && sourceStill.resourceID==9001,"Choice rewrote immutable linked-source identity instead of selected input")
    b.chooseClear(expected:b.control);try expect(b.resource == .clear && b.directory?.resource==nil && b.directory?.service==selected.item && b.canReview,"Explicit clear retained resource proof or erased Service proof")
    await b.openSelector(.resource,expected:b.control,serviceChild:service.control,resourceChild:resource.control);let reopened=b.selectorControl!
    b.useResource(chosenResource,child:resourceLeaf,expected:resourceSession);b.closeSelector(expected:resourceSession)
    try expect(b.selectorControl==reopened && b.resource == .clear,"Old Resource Use/Back crossed reopen")
    let row9003=resource.window!.items.first {$0.id==9003}!;await resource.select(row9003,expected:resource.control);resource.choose(expected:resource.control);b.useResource(resource.choice!,child:resource.control,expected:reopened)
    b.prepareReview(expected:b.control);let input=b.review!.input
    try expect(input.directory?.service==selected.item && input.directory?.resource==chosenResource.item && input.client==client && input.start.raw==raw,"Review lost full exact selected read snapshots")
    await b.submit(expected:b.control);let attempt=b.submission!.attempt,body=try JSONSerialization.jsonObject(with:attempt.body) as! [String:Any]
    try expect(b.submission?.phase == .unknown && b.retainedAttemptCount==1 && Set(body.keys)==["business","client","service","start_at","resource"] && body["service"] as? Int==8003 && body["resource"] as? Int==9003,"Fixed fixture fabricated success for new ids or field proof leaked into POST body")
    let retained=attempt;await b.openSelector(.service,expected:b.control,serviceChild:service.control,resourceChild:resource.control);b.useService(selected,child:leaf,expected:firstSession)
    try expect(b.selector==nil && b.submission?.attempt==retained && b.retainedAttemptCount==1,"Unknown was edited/replayed through directory selection")
    try expect(parent.session.items==items && parent.session.detail?.appointment.id==original.appointment.id && parent.session.detail?.appointment.start_at==original.appointment.start_at,"Form directory binding patched original Calendar/Appointment")
    await parent.retryDetail(expected:parent.control);try expect(b.blocked && !b.canOpen && b.retainedAttemptCount==1,"Matching parent reread released unknown directory-origin attempt")
    await parent.load(business:202);await parent.load(business:101);await parent.loadDetail(id:501);try expect(b.blocked && !b.canOpen && b.retainedAttemptCount==1,"Business round trip released unknown selected body")
    // Fresh model proves exact list/detail/choice controls; same payload reread cannot revive callbacks.
    let fresh=AppointmentBookingViewModel(port:port,clients:repo,references:refs,services:sr,resources:rr);fresh.bind(source);fresh.open(expected:fresh.control);fresh.setStart(raw,expected:fresh.inputControl)
    let fs=fresh.serviceChoices!,fr=fresh.resourceChoices!
    await fresh.openSelector(.service,expected:fresh.control,serviceChild:fs.control,resourceChild:fr.control);let session=fresh.selectorControl!,first=fs.window!.items[0];await fs.select(first,expected:fs.control);fs.choose(expected:fs.control);let oldChoice=fs.choice!,oldLeaf=fs.control!
    fs.backToWindow(expected:fs.control);await fs.reload(expected:fs.control);fresh.useService(oldChoice,child:oldLeaf,expected:session)
    try expect(fresh.service==nil && fresh.selectorControl==session,"Matching list reread revived old detail choice")
    await fs.select(fs.window!.items[0],expected:fs.control);fs.choose(expected:fs.control);let current=fs.choice!,currentLeaf=fs.control!;fresh.useService(current,child:oldLeaf,expected:session)
    try expect(fresh.service==nil,"Old child control applied new same-id choice")
    fresh.useService(current,child:currentLeaf,expected:session);await fresh.load(.client,expected:fresh.control);fresh.chooseClear(expected:fresh.control);let before=fresh.inputControl!
    fresh.setStart("2026-10-29T05:00:0",expected:before);fresh.setStart(raw,expected:before);try expect(fresh.rawStart==raw && fresh.directory?.service==current.item,"Continuous time input lost selected proof or a second update")
    @MainActor func candidate(_ linked:Bool) async throws -> AppointmentBookingCandidateTime {
        let service=try await refs.reference(.service,business:101,id:8001),business=source.read.scope.business
        let resource:AppointmentReferenceDetail?
        if linked {resource=try await refs.reference(.resource,business:101,id:9001)} else {resource=nil}
        let intent=AppointmentSlotIntent(business:business,service:service,resource:resource,day:"2026-11-02")!,slots=APIAppointmentSlotRepository(transport:FixtureAppointmentSlotTransport(directory:directory)),read=try await slots.slots(intent)
        return AppointmentBookingCandidateTime(source:source,review:AppointmentSlotReadContext(business:business,service:service,resource:resource,read:read)!.review(index:0)!)!
    }
    let time=try await candidate(false),proofBefore=fresh.directory,rawBefore=fresh.rawStart
    fresh.back(expected:fresh.control);try expect(!fresh.permitsCandidate(time) && !fresh.openCandidate(time,expected:fresh.control) && fresh.rawStart==rawBefore && fresh.directory==proofBefore,"Old linked candidate overwrote current independently selected Service or input")
    fresh.open(expected:fresh.control)
    await fresh.load(.service,expected:fresh.control);try expect(fresh.service?.id==8001 && fresh.directory==nil && fresh.resource == .clear,"Explicit legacy reread kept conflicting directory proof or reset explicit clear")
    fresh.back(expected:fresh.control);let linkedTime=try await candidate(true)
    try expect(fresh.permitsCandidate(time) && !fresh.permitsCandidate(linkedTime) && fresh.resource == .clear,"Candidate availability context silently replaced explicit Resource clear")
    // Late child replies cannot cross close/reopen/other selector or parent source changes.
    let held=HeldServiceDirectory(),late=AppointmentBookingViewModel(port:port,clients:repo,references:refs,services:held,resources:rr);late.bind(source);late.open(expected:late.control);late.setStart(raw,expected:late.inputControl)
    let request=Task {await late.openSelector(.service,expected:late.control,serviceChild:late.serviceChoices?.control,resourceChild:late.resourceChoices?.control)};await held.wait(0);let waiting=late.selectorControl!;late.closeSelector(expected:waiting)
    await late.openSelector(.resource,expected:late.control,serviceChild:late.serviceChoices?.control,resourceChild:late.resourceChoices?.control);let other=late.selectorControl!
    await held.resolve(0,window:try await sr.services(business:101));await request.value;late.closeSelector(expected:waiting)
    try expect(late.selectorControl==other && late.service==nil && late.serviceChoices?.window==nil && late.rawStart==raw,"Late Service list/old Back displaced current Resource selector/input")
    late.bind(nil);late.bind(source);late.closeSelector(expected:other);try expect(late.selector==nil && late.resourceChoices?.owner==nil && late.serviceChoices?.owner==nil,"Parent A-B-A restored stale directory presentation")
    // Explicit synthetic actor snapshot is checked separately from read data; closing remains possible.
    let actorPort=MutableDirectoryBookingPort(port.grants),actor=AppointmentBookingViewModel(port:actorPort,clients:repo,references:refs,services:sr,resources:rr);actor.bind(source);actor.open(expected:actor.control)
    await actor.openSelector(.service,expected:actor.control,serviceChild:actor.serviceChoices?.control,resourceChild:actor.resourceChoices?.control);let actorSession=actor.selectorControl!,ac=actor.serviceChoices!;await ac.select(ac.window!.items[0],expected:ac.control);ac.choose(expected:ac.control);actorPort.replace([]);actor.useService(ac.choice!,child:ac.control,expected:actorSession)
    try expect(actor.service==nil && actor.selectorControl==actorSession,"Read choice bypassed missing explicit synthetic CREATE actor context")
    actor.closeSelector(expected:actorSession);try expect(actor.selector==nil && ac.window==nil,"Actor change made private selector impossible to close")
    let noPort=AppointmentBookingViewModel(port:port,clients:repo,references:refs);noPort.bind(source);noPort.open(expected:noPort.control);await noPort.openSelector(.service,expected:noPort.control,serviceChild:nil,resourceChild:nil);try expect(noPort.selector==nil && noPort.serviceChoices==nil,"Default composition manufactured directory port")
    return count
}
