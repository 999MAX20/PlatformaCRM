import Foundation
import CRMCore

private actor RescheduleReadTransport:ReadTransport {
    let fixture:FixtureTransport;private var calls:[ReadRequest]=[]
    init(_ directory:URL) {fixture=FixtureTransport(directory:directory)}
    func get(_ request:ReadRequest) async throws -> ReadResponse {calls.append(request);return try await fixture.get(request)}
    func requests()->[ReadRequest] {calls}
}
private actor HeldRescheduleReferences:AppointmentReferenceRepository {
    private var pending:[CheckedContinuation<AppointmentReferenceDetail,any Error>]=[]
    func reference(_ kind:AppointmentReferenceKind,business:Int,id:Int) async throws -> AppointmentReferenceDetail {try await withCheckedThrowingContinuation {pending.append($0)}}
    func wait(_ n:Int) async {while pending.count<n {await Task.yield()}}
    func resolve(_ n:Int,_ value:Result<AppointmentReferenceDetail,any Error>) {pending[n].resume(with:value)}
}
private actor HeldReschedulePort:SyntheticAppointmentLifecyclePort {
    nonisolated let grants:[SyntheticAppointmentLifecycleGrant];private var pending:[CheckedContinuation<SyntheticAppointmentLifecycleOutcome,Never>]=[];private var attempts:[AppointmentLifecycleAttempt]=[]
    init(_ grants:[SyntheticAppointmentLifecycleGrant]) {self.grants=grants}
    func execute(_ attempt:AppointmentLifecycleAttempt) async throws -> SyntheticAppointmentLifecycleOutcome {attempts.append(attempt);return await withCheckedContinuation {pending.append($0)}}
    func wait(_ n:Int) async {while pending.count<n {await Task.yield()}}
    func resolve(_ n:Int,_ value:SyntheticAppointmentLifecycleOutcome) {pending[n].resume(returning:value)}
    func calls()->[AppointmentLifecycleAttempt] {attempts}
}
@MainActor func checkAppointmentReschedule(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let repository=APIReadRepository(transport:FixtureTransport(directory:directory)),fixture=FixtureAppointmentLifecyclePort(directory:directory),transport=RescheduleReadTransport(directory),references=APIAppointmentReferenceRepository(transport:transport)
    let initial=Appointment.instant("2026-10-28T07:00:00Z")!,m=AgendaViewModel(repository:repository,initialDate:initial,lifecyclePort:fixture,lifecycleReferences:references)
    await m.start();await m.loadDetail(id:501);let model=m.lifecycle!,original=m.session.detail!,list=m.session.items
    m.prepareLifecycle(.reschedule,entry:m.lifecycleEntryControl,child:model.control)
    try expect(model.reschedulePresented && model.rawStart.isEmpty && model.rawReason.isEmpty && model.resourceChoice==nil && !model.canReviewReschedule,"Reschedule invented date/reason/resource defaults or skipped explicit review")
    let input=model.inputControl!,before=model.control!
    model.setStart("2026-10-28T05:00:00",expected:input);model.setStart("2026-10-28T05:00:00Z",expected:input)
    model.setReason("é",expected:input);model.setReason("  Synthetic move e\u{301}  ",expected:input)
    try expect(model.timeInputValid && model.rawStart=="2026-10-28T05:00:00Z" && SourceTextIdentity.same(model.rawReason,"  Synthetic move e\u{301}  ") && !model.canReviewReschedule,"Stable continuous-input visit rejected later keystroke/canonical variant or invented resource choice")
    model.chooseClear(expected:before);try expect(model.resourceChoice==nil,"Old pre-edit resource button changed new input")
    model.chooseClear(expected:model.control);model.reviewReschedule(expected:model.control);let review=model.review!
    try expect(review.reschedule?.resource == .clear && review.reschedule?.reason=="Synthetic move e\u{301}","Explicit clear/source-stripped review lost raw original")
    model.setStart("2026-10-29T00:00:00Z",expected:input);model.back(expected:model.control)
    try expect(model.rawStart=="2026-10-28T05:00:00Z" && SourceTextIdentity.same(model.rawReason,review.reschedule?.rawReason),"Review allowed stale edit or Back destroyed raw input")
    model.setReason("stale",expected:input);try expect(SourceTextIdentity.same(model.rawReason,"  Synthetic move e\u{301}  "),"Old field visit edited reopened form")
    await model.loadLinkedResource(expected:model.control)
    let calls=await transport.requests()
    try expect(model.resourceChoice?.id==9001 && calls.count==1 && calls[0].path=="/api/resources/9001/" && calls[0].query.isEmpty,"Linked choice skipped exact existing scoped Resource GET or used guessed endpoint/query")
    model.chooseClear(expected:model.control);model.reviewReschedule(expected:model.control);await model.submit(expected:model.control)
    try expect(model.submission?.phase == .acceptedFixture && model.submission?.attempt.review.reschedule==review.reschedule,"Explicit exact reschedule fixture request/receipt failed")
    try expect(m.session.detail?.appointment.start_at==original.appointment.start_at && m.session.items.map(\.start_at)==list.map(\.start_at) && m.session.detail?.details.resource?.id==original.details.resource?.id,"Fake reschedule mutated GET/calendar/resource or claimed absent echo")
    model.acknowledge(expected:model.control,record:model.submission!)
    try expect(model.used(.reschedule) && !model.canPrepare(.reschedule) && model.canPrepare(.cancel),"Accepted reschedule reused supplied key or blocked independent explicit lifecycle")
    let heldRefs=HeldRescheduleReferences(),port=HeldReschedulePort(fixture.grants),n=AgendaViewModel(repository:repository,initialDate:initial,lifecyclePort:port,lifecycleReferences:heldRefs)
    await n.start();await n.loadDetail(id:501);let child=n.lifecycle!;n.prepareLifecycle(.reschedule,entry:n.lifecycleEntryControl,child:child.control)
    let first=child.inputControl!;child.setStart("2026-10-28T05:00:00Z",expected:first);child.setReason("  retained e\u{301}  ",expected:first)
    let loading=Task {await child.loadLinkedResource(expected:child.control)};await heldRefs.wait(1)
    child.back(expected:child.control);n.prepareLifecycle(.reschedule,entry:n.lifecycleEntryControl,child:child.control)
    let resource=AppointmentReferenceDetail.decode(try Data(contentsOf:directory.appendingPathComponent("resource-reference-9001.json")),kind:.resource)!
    await heldRefs.resolve(0,.success(resource));await loading.value
    try expect(child.resourceChoice==nil && !child.resourceLoading && child.rawStart=="2026-10-28T05:00:00Z" && SourceTextIdentity.same(child.rawReason,"  retained e\u{301}  "),"Late Resource GET selected in a reopened form or destroyed draft")
    let denied=Task {await child.loadLinkedResource(expected:child.control)};await heldRefs.wait(2);await heldRefs.resolve(1,.failure(ReadFailure.denied));await denied.value
    try expect(child.resourceFailure == .denied && child.resourceChoice==nil && !child.canReviewReschedule && child.rawStart=="2026-10-28T05:00:00Z","Resource denial fell back to clear/choice or lost input")
    child.chooseClear(expected:child.control);child.reviewReschedule(expected:child.control);let heldControl=child.control!,pending=Task {await child.submit(expected:heldControl)};await port.wait(1)
    for action in AppointmentLifecycleAction.allCases {child.prepare(action,expected:child.control)};child.setReason("lost",expected:first)
    try expect(child.blocked && child.retainedAttemptCount==1,"Pending reschedule admitted a different lifecycle or input overwrite")
    await n.loadDetail(id:502);await port.resolve(0,.unknown);await pending.value
    try expect(n.session.detail?.appointment.id==502 && child.submission==nil && child.canPrepare(.reschedule),"Late unknown poisoned another target or exposed old input")
    await n.load(business:202);await n.load(business:101);await n.loadDetail(id:501)
    try expect(child.blocked && child.submission==nil && AppointmentLifecycleAction.allCases.allSatisfy {!child.canPrepare($0)} && child.retainedAttemptCount==1,"Matching reread/Business round trip released cross-action unknown")
    let attempt=await port.calls()[0],body=try JSONSerialization.jsonObject(with:attempt.body) as! [String:Any]
    try expect(SourceTextIdentity.same(attempt.review.reschedule?.rawReason,"  retained e\u{301}  ") && body["resource"] is NSNull && body["reason"] as? String=="retained e\u{301}","Unknown did not retain original raw and frozen source-strip body")
    return count
}
