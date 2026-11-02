import Foundation
import CRMCore

private actor HeldAppointmentTerminalPort:SyntheticAppointmentLifecyclePort {
    nonisolated let grants:[SyntheticAppointmentLifecycleGrant];nonisolated let terminalGrants:[SyntheticAppointmentTerminalGrant]
    private var pending:[CheckedContinuation<SyntheticAppointmentLifecycleOutcome,Never>]=[];private var attempts:[AppointmentLifecycleAttempt]=[]
    init(_ fixture:FixtureAppointmentTerminalPort) {grants=fixture.grants;terminalGrants=fixture.terminalGrants}
    func execute(_ a:AppointmentLifecycleAttempt) async throws -> SyntheticAppointmentLifecycleOutcome {attempts.append(a);return await withCheckedContinuation {pending.append($0)}}
    func wait(_ n:Int) async {while pending.count<n {await Task.yield()}}
    func resolve(_ n:Int,_ value:SyntheticAppointmentLifecycleOutcome) {pending[n].resume(returning:value)}
    func calls()->[AppointmentLifecycleAttempt] {attempts}
}
@MainActor func checkAppointmentTerminal(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),fixture=FixtureAppointmentTerminalPort(directory:directory),port=HeldAppointmentTerminalPort(fixture)
    let date=Appointment.instant("2026-10-28T07:00:00Z")!,m=AgendaViewModel(repository:repo,initialDate:date,lifecyclePort:port)
    await m.start();await m.loadDetail(id:501);let child=m.lifecycle!,old=child.control!,entry=m.lifecycleEntryControl!,original=m.session.detail!,list=m.session.items
    try expect(child.canPrepare(.complete) && child.canPrepare(.noShow),"Explicit generic terminal grant did not expose paired local actions")
    m.prepareLifecycle(.complete,entry:entry,child:old);let review=child.control!;child.back(expected:old);child.prepare(.noShow,expected:old);await child.submit(expected:old)
    try expect(child.review?.action == .complete && child.retainedAttemptCount==0,"Stale callbacks changed/submitted terminal review")
    child.back(expected:review);try expect(child.review==nil && child.canPrepare(.noShow),"Explicit Back did not restore local action choice")
    m.prepareLifecycle(.complete,entry:entry,child:old);try expect(child.review==nil,"Old entry/child reopened terminal review after Back")
    m.prepareLifecycle(.complete,entry:m.lifecycleEntryControl,child:child.control);let ticket=child.control!,pending=Task {await child.submit(expected:ticket)};await port.wait(1)
    await child.submit(expected:ticket);for action in AppointmentLifecycleAction.allCases {child.prepare(action,expected:child.control)}
    try expect(child.blocked && child.retainedAttemptCount==1,"Pending complete admitted duplicate/another lifecycle")
    await m.loadDetail(id:502);let calls=await port.calls();await port.resolve(0,try await fixture.execute(calls[0]));await pending.value
    try expect(m.session.detail?.appointment.id==502 && child.submission==nil && child.canPrepare(.noShow),"Late plain501 reply overwrote502 or blocked independent target")
    await m.loadDetail(id:501)
    try expect(m.session.detail?.appointment.status==original.appointment.status && m.session.items.map(\.status)==list.map(\.status) && child.submission?.terminalReceipt?.status=="completed" && child.submission?.receipt==nil,"Plain fixture patched original GET/list/calendar or used mobile receipt")
    child.acknowledge(expected:child.control,record:child.submission!);try expect(child.used(.complete) && !child.canPrepare(.complete) && child.canPrepare(.noShow),"Known complete fixture silently reusable or independently granted no-show lost")
    m.prepareLifecycle(.noShow,entry:m.lifecycleEntryControl,child:child.control);let rejected=Task {await child.submit(expected:child.control)};await port.wait(2);let rejectCalls=await port.calls();await port.resolve(1,try await fixture.execute(rejectCalls[1]));await rejected.value
    try expect(child.submission?.phase == .rejectedFixture,"Explicit synthetic no-write rejection misclassified")
    child.acknowledge(expected:child.control,record:child.submission!);try expect(child.canPrepare(.noShow),"Explicit no-write rejection removed manual review path")
    await m.load(business:202);await m.loadDetail(id:601);m.prepareLifecycle(.complete,entry:m.lifecycleEntryControl,child:child.control)
    let unknownControl=child.control!,unknown=Task {await child.submit(expected:unknownControl)};await port.wait(3);unknown.cancel();let unknownCalls=await port.calls();await port.resolve(2,try await fixture.execute(unknownCalls[2]));await unknown.value
    try expect(child.submission?.phase == .unknown && child.submission?.attempt.authorization.key==nil && child.submission?.attempt.query==["business":"202"],"Cancellation lost generic attempt/query or synthesized mobile key")
    await m.load(business:101);await m.loadDetail(id:502);try expect(child.canPrepare(.noShow),"Unknown601 blocked independent502")
    await m.load(business:202);await m.loadDetail(id:601)
    try expect(child.blocked && child.submission==nil && AppointmentLifecycleAction.allCases.allSatisfy {!child.canPrepare($0)} && child.retainedAttemptCount==3,"Matching reread/Business roundtrip released generic unknown5-action quarantine")
    await child.submit(expected:unknownControl);try expect(await port.calls().count==3,"Stale callback repeated unknown generic command")
    let independent=AgendaViewModel(repository:repo,initialDate:date,lifecyclePort:fixture);await independent.start();await independent.loadDetail(id:502);let n=independent.lifecycle!
    independent.prepareLifecycle(.noShow,entry:independent.lifecycleEntryControl,child:n.control);await n.submit(expected:n.control)
    try expect(n.submission?.terminalReceipt?.status=="no_show" && n.submission?.phase == .acceptedFixture && independent.session.detail?.appointment.status=="created","No-show plain fixture failed or mutated GET")
    let readOnly=AgendaViewModel(repository:repo,initialDate:date,lifecyclePort:FixtureAppointmentLifecyclePort(directory:directory));await readOnly.start();await readOnly.loadDetail(id:501)
    try expect(readOnly.lifecycle?.canPrepare(.complete)==false && readOnly.lifecycle?.canPrepare(.noShow)==false,"Mobile-only/key context created terminal UPDATE admission")
    return count
}
