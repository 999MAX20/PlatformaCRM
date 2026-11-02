import Foundation
import CRMCore

private actor HeldAppointmentLifecyclePort:SyntheticAppointmentLifecyclePort {
    nonisolated let grants:[SyntheticAppointmentLifecycleGrant]
    private var attempts:[AppointmentLifecycleAttempt]=[]
    private var pending:[CheckedContinuation<SyntheticAppointmentLifecycleOutcome,Never>]=[]
    init(_ grants:[SyntheticAppointmentLifecycleGrant]) {self.grants=grants}
    func execute(_ a:AppointmentLifecycleAttempt) async throws -> SyntheticAppointmentLifecycleOutcome {attempts.append(a);return await withCheckedContinuation {pending.append($0)}}
    func wait(_ count:Int) async {while pending.count<count {await Task.yield()}}
    func resolve(_ i:Int,_ value:SyntheticAppointmentLifecycleOutcome) {pending[i].resume(returning:value)}
    func calls()->[AppointmentLifecycleAttempt] {attempts}
}
@MainActor func checkAppointmentLifecycle(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),fixture=FixtureAppointmentLifecyclePort(directory:directory),port=HeldAppointmentLifecyclePort(fixture.grants)
    let initial=Appointment.instant("2026-10-28T07:00:00Z")!,links=AppointmentRelationsViewModel(repository:repo)
    let baseline=AgendaViewModel(repository:repo,initialDate:initial);await baseline.start();await baseline.loadDetail(id:501)
    try expect(baseline.lifecycle==nil && baseline.lifecycleEntryControl==nil,"GET-only/default Agenda gained synthetic UPDATE authority")
    let m=AgendaViewModel(repository:repo,initialDate:initial,relations:links,lifecyclePort:port);await m.start();await m.loadDetail(id:501)
    let child=m.lifecycle!,entry=m.lifecycleEntryControl!,original=m.session.detail!,list=m.session.items,old=child.control!
    await links.openClient(presentation:links.presentation);links.back(presentation:links.presentation)
    m.prepareLifecycle(.confirm,entry:entry,child:old)
    try expect(child.review==nil,"Old related A-B-A entry prepared lifecycle review")
    m.prepareLifecycle(.confirm,entry:m.lifecycleEntryControl,child:old);let review=child.control!
    child.back(expected:old);child.prepare(.cancel,expected:old);await child.submit(expected:old)
    try expect(child.review?.action == .confirm && child.retainedAttemptCount==0,"Stale child callback altered/started new review")
    let pending=Task {await child.submit(expected:review)};await port.wait(1)
    await child.submit(expected:review);child.prepare(.cancel,expected:child.control)
    try expect(child.submission?.phase == .pending && child.blocked && child.retainedAttemptCount==1,"Duplicate/cross-action pending submission escaped entity barrier")
    let oldParent=m.control;await m.loadDetail(id:502);m.closeDetail(expected:oldParent)
    let held=await port.calls(),reply=try await fixture.execute(held[0]);await port.resolve(0,reply);await pending.value
    try expect(m.session.detailSelection?.id==502 && m.session.detail?.appointment.status=="created" && child.submission==nil && child.retainedAttemptCount==1,"Late501 receipt overwrote502 detail or exposed another target result")
    try expect(m.session.items.map(\.status)==list.map(\.status),"Fake outcome changed list/calendar GET status")
    await m.loadDetail(id:501)
    try expect(m.session.detail?.appointment.title==original.appointment.title && m.session.detail?.appointment.status==original.appointment.status && child.submission?.phase == .acceptedFixture,"New GET did not retain source / known fixture record")
    let accepted=child.submission!;child.acknowledge(expected:child.control,record:accepted)
    try expect(child.used(.confirm) && !child.canPrepare(.confirm) && child.canPrepare(.cancel),"Known fake result was retried or blocked independent explicit cancel")
    m.prepareLifecycle(.cancel,entry:m.lifecycleEntryControl,child:child.control);let cancelControl=child.control!
    let unknown=Task {await child.submit(expected:cancelControl)};await port.wait(2);m.closeDetail();await m.load(business:202);await m.loadDetail(id:601)
    await port.resolve(1,.unknown);await unknown.value
    try expect(m.session.selection?.business.id==202 && m.session.detail?.appointment.id==601 && child.submission==nil && child.retainedAttemptCount==2,"Unknown crossed Business/target ownership")
    await m.load(business:101);await m.loadDetail(id:501)
    try expect(child.blocked && child.submission==nil && !child.canPrepare(.confirm) && !child.canPrepare(.cancel) && child.retainedAttemptCount==2,"Matching reread or Business round trip resolved/rekeyed unknown or lost quarantine")
    m.prepareLifecycle(.confirm,entry:entry,child:old);await child.submit(expected:cancelControl)
    try expect(await port.calls().count==2,"Stale callback repeated retained attempt")
    await m.loadDetail(id:502)
    try expect(child.canPrepare(.cancel),"Unknown for501 blocked independent502 local work")
    let explicit=AgendaViewModel(repository:repo,initialDate:initial,lifecyclePort:fixture);await explicit.start();await explicit.loadDetail(id:502)
    let rejection=explicit.lifecycle!;explicit.prepareLifecycle(.confirm,entry:explicit.lifecycleEntryControl,child:rejection.control);await rejection.submit(expected:rejection.control)
    try expect(rejection.submission?.phase == .rejectedFixture && explicit.session.detail?.appointment.status=="created","Explicit no-write fixture rejection lost original GET")
    rejection.acknowledge(expected:rejection.control,record:rejection.submission!)
    try expect(rejection.canPrepare(.confirm),"Explicit synthetic no-write refusal lost retained source review path")
    // Cancelling an in-flight task keeps unknown even if a late in-memory reply appears valid.
    await m.load(business:202);await m.loadDetail(id:601);m.prepareLifecycle(.confirm,entry:m.lifecycleEntryControl,child:child.control)
    let cancelled=Task {await child.submit(expected:child.control)};await port.wait(3);let calls=await port.calls();cancelled.cancel();await port.resolve(2,try await fixture.execute(calls[2]));await cancelled.value
    try expect(child.submission?.phase == .unknown && child.retainedAttemptCount==3,"Cancellation accepted late fake receipt or discarded attempt")
    return count
}
