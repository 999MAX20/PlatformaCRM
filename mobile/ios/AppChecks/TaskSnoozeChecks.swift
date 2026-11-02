import Foundation
import CRMCore

actor ControlledTaskSnoozePort:SyntheticTaskSnoozePort {
    nonisolated let grants:[SyntheticTaskSnoozeGrant]
    private var attempts:[TaskSnoozeAttempt]=[]
    private var pending:[Int:CheckedContinuation<SyntheticTaskSnoozeOutcome,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    init(_ grants:[SyntheticTaskSnoozeGrant]) {self.grants=grants}
    func execute(_ attempt:TaskSnoozeAttempt) async throws -> SyntheticTaskSnoozeOutcome {let i=attempts.count;attempts.append(attempt);return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ value:SyntheticTaskSnoozeOutcome) {pending.removeValue(forKey:i)!.resume(returning:value)}
    func fail(_ i:Int) {pending.removeValue(forKey:i)!.resume(throwing:ReadFailure.unavailable)}
    func recorded()->[TaskSnoozeAttempt] {attempts}
}
@MainActor func checkTaskSnooze(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func detail(_ b:Int=101,_ id:Int=1101) throws -> TaskDetails {try JSONDecoder().decode(TaskDetails.self,from:Data(contentsOf:directory.appendingPathComponent("task-\(b)-\(id).json")))}
    let original=try detail(),foreign=try detail(202,1201),fixture=FixtureTaskSnoozePort(directory:directory)
    func source(_ d:TaskDetails,epoch:Int=170,revision:Int=1)->TaskSnoozeSource {TaskSnoozeSource(read:TaskCommentRead(context:TaskCommentContext(business:d.business,task:d.task.id,epoch:epoch),revision:revision),task:d.task,reminder:d.details.reminder_at)}
    let initial=source(original),port=ControlledTaskSnoozePort(fixture.grants),m=TaskSnoozeViewModel(port:port)
    m.bind(initial);m.open(expected:m.control);let input=m.inputControl
    try expect(m.editing && m.raw.isEmpty && m.review==nil,"Snooze invented initial date")
    m.update(" 2026-10-30T12:00:00Z",input:input);m.prepare(expected:m.control)
    try expect(m.showsIssue && m.review==nil && m.raw.hasPrefix(" "),"Snooze normalized unsupported raw or lost it")
    m.update("2026-10-30T17:00:00.123456+05:00",input:m.inputControl);let editing=m.control!
    m.prepare(expected:editing);let old=m.control!;m.back(expected:old)
    try expect(m.raw==editing.raw && m.editing && m.review==nil,"Review Back lost exact snooze input")
    m.update("old",input:input);m.prepare(expected:editing);await m.submit(expected:old)
    let staleCalls=await port.recorded();try expect(m.raw==editing.raw && m.review==nil && staleCalls.isEmpty,"Old snooze editor/review acted on resumed visit")
    m.askClear(expected:m.control);let question=m.clearConfirmation!;m.update("bad",input:input);m.dismissClear(question);m.update("2000-02-29T00:00:00Z",input:m.inputControl);m.confirmClear(question)
    try expect(m.raw=="2000-02-29T00:00:00Z","Old clear confirmation erased new input")
    m.askClear(expected:m.control);m.confirmClear(m.clearConfirmation!);try expect(m.raw.isEmpty && m.editing,"Exact clear did not affect only current draft")
    m.update("2000-02-29T00:00:00Z",input:m.inputControl);m.prepare(expected:m.control);let submit=m.control!,job=Task {await m.submit(expected:submit)};await port.wait(0)
    let pending=m.control!,record=m.submission!;await m.submit(expected:submit);await m.submit(expected:pending);m.back(expected:pending);m.askClear(expected:pending);m.acknowledge(expected:pending,record:record)
    try expect(await port.recorded().count==1 && m.submission==record && m.raw=="2000-02-29T00:00:00Z" && m.clearConfirmation==nil,"Pending snooze repeated/cleared/lost input")
    await port.fail(0);await job.value;let unknown=m.submission!
    m.bind(source(original,epoch:171,revision:2));try expect(m.blocked && m.submission==nil && m.raw.isEmpty && m.canPresent && !m.canOpen,"New epoch exposed or cleared unknown snooze")
    m.bind(initial);try expect(m.submission==unknown && unknown.attempt.review.value.raw=="2000-02-29T00:00:00Z","Unknown snooze source/raw lost")
    m.acknowledge(expected:m.control,record:unknown);try expect(m.blocked,"Unknown snooze acknowledged")
    // Explicit test producer echoes manual input only after submit; source remains untouched.
    let ok=TaskSnoozeViewModel(port:fixture);ok.bind(initial);ok.open(expected:ok.control);ok.update("2000-02-29T00:00:00Z",input:ok.inputControl);ok.prepare(expected:ok.control);let oldOK=ok.control!;await ok.submit(expected:oldOK);let accepted=ok.submission!
    try expect(accepted.phase == .confirmed && accepted.result?.snoozed_until=="2000-02-29T00:00:00Z" && original.details.snoozed_until == .notSet && original.task.status=="open","Fake snooze predicted time/default or mutated GET")
    ok.acknowledge(expected:ok.control,record:accepted);ok.open(expected:ok.control);await ok.submit(expected:oldOK)
    try expect(ok.consumed && !ok.editing && ok.retainedAttemptCount==1,"Confirmed snooze reused consumed source")
    ok.bind(source(original,revision:2));ok.open(expected:ok.control);try expect(ok.editing && ok.raw.isEmpty,"Fresh read failed explicit new editor")
    let noWrite=TaskSnoozeViewModel(port:fixture);noWrite.bind(source(try detail(101,1401)));noWrite.open(expected:noWrite.control);noWrite.update("2026-10-30T12:00:00Z",input:noWrite.inputControl);noWrite.prepare(expected:noWrite.control);let rejectedControl=noWrite.control!;await noWrite.submit(expected:rejectedControl);let rejected=noWrite.submission!
    noWrite.acknowledge(expected:noWrite.control,record:rejected);await noWrite.submit(expected:rejectedControl);try expect(noWrite.editing && noWrite.review==nil && noWrite.raw==rejected.attempt.review.value.raw && noWrite.retainedAttemptCount==1,"No-write snooze replayed/lost raw")
    let latePort=ControlledTaskSnoozePort(fixture.grants),late=TaskSnoozeViewModel(port:latePort);late.bind(initial);late.open(expected:late.control);late.update("2026-10-30T12:00:00Z",input:late.inputControl);late.prepare(expected:late.control);let lateJob=Task {await late.submit(expected:late.control)};await latePort.wait(0)
    late.bind(source(foreign,epoch:172));late.open(expected:late.control);late.update("2038-01-19T03:14:08Z",input:late.inputControl);let foreignControl=late.control
    let sent=await latePort.recorded()[0];await latePort.resolve(0,try await fixture.execute(sent));await lateJob.value
    try expect(late.control==foreignControl && late.submission==nil && late.raw=="2038-01-19T03:14:08Z","Late snooze touched foreign draft")
    let repository=APIReadRepository(transport:FixtureTransport(directory:directory)),plain=TaskListViewModel(repository:repository),unverified=TaskListViewModel(repository:repository,snoozeSubmission:fixture)
    await unverified.load(business:101,epoch:173);await unverified.open(id:1101);try expect(plain.snoozeAction==nil && unverified.snoozeAction?.source==nil,"GET/default composition granted snooze")
    let transport=SearchTransport(directory),flow=TaskListViewModel(repository:APIReadRepository(transport:transport),commentSource:FixtureTaskCommentDraftSource(directory:directory),cancelSubmission:FixtureTaskCancelPort(directory:directory),completeSubmission:FixtureTaskCompletePort(directory:directory),selfAssignSubmission:FixtureTaskSelfAssignPort(directory:directory),startSubmission:FixtureTaskStartPort(directory:directory),reopenSubmission:FixtureTaskReopenPort(directory:directory),watcherSubmission:FixtureTaskWatcherPort(directory:directory),undoCancelSubmission:FixtureTaskUndoCancelPort(directory:directory),snoozeSubmission:fixture)
    await flow.load(business:101,epoch:174);await flow.open(id:1101);let snooze=flow.snoozeAction!,before=flow.detail!,rows=flow.items,readCount=await transport.recorded().count
    flow.openSnooze(snooze.control,parent:flow.control);snooze.update("2026-10-30T12:00:00Z",input:snooze.inputControl)
    try expect(!flow.startCurrent(flow.control) && !flow.completionCurrent(flow.control) && !flow.selfAssignmentCurrent(flow.control) && !flow.watcherCurrent(flow.control),"Snooze raw editor did not own peer visit")
    flow.prepareStart(flow.startAction?.control,parent:flow.control);try expect(flow.startAction?.review==nil && snooze.editing,"Peer stole active snooze raw editor")
    flow.openComment(snooze.source!.read);try expect(!snooze.editing,"Comment did not interrupt unsubmitted snooze visit");if let c=flow.comment {c.close(expected:c.returnControl)}
    flow.openSnooze(snooze.control,parent:flow.control);try expect(snooze.raw=="2026-10-30T12:00:00Z","Comment return lost unsubmitted snooze raw")
    snooze.prepare(expected:snooze.control);await snooze.submit(expected:snooze.control);try expect(snooze.submission?.phase == .confirmed && flow.detail==before && flow.items==rows,"Snooze test changed source/detail/status/dates")
    try expect(await transport.recorded().count==readCount,"Snooze test sent request/reloaded source")
    snooze.acknowledge(expected:snooze.control,record:snooze.submission!);flow.prepareStart(flow.startAction?.control,parent:flow.control);flow.openCancelReason(snooze.source!.read)
    try expect(flow.startAction?.review==nil && flow.cancelReason?.control==nil && flow.taskActionOccupied,"Consumed snooze source bypassed through peer/cancellation")
    // Existing Start unknown blocks snooze after a matching re-read and new owner epoch.
    let startPort=ControlledTaskStartPort(FixtureTaskStartPort(directory:directory).grants),peer=TaskListViewModel(repository:repository,commentSource:FixtureTaskCommentDraftSource(directory:directory),startSubmission:startPort,snoozeSubmission:fixture)
    await peer.load(business:101,epoch:175);await peer.open(id:1101);peer.prepareStart(peer.startAction?.control,parent:peer.control)
    guard let startControl=peer.startAction?.control else {throw ViewModelCheckFailure(message:"Source start control missing")}
    let peerJob=Task {await peer.startAction!.submit(expected:startControl)};await startPort.wait(0);await startPort.resolve(0,.unknown);await peerJob.value
    await peer.load(business:101,epoch:176);await peer.open(id:1101);peer.openSnooze(peer.snoozeAction?.control,parent:peer.control)
    try expect(peer.snoozeAction?.editing==false && peer.taskActionOccupied,"Peer unknown/read/new epoch authorized snooze")
    return count
}
