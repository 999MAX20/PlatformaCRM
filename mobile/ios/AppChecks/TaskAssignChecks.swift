import Foundation
import CRMCore

actor ControlledTaskAssignPort:SyntheticTaskAssignPort {
    nonisolated let grants:[SyntheticTaskAssignGrant]
    private var attempts:[TaskAssignAttempt]=[]
    private var pending:[Int:CheckedContinuation<SyntheticTaskAssignOutcome,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    init(_ grants:[SyntheticTaskAssignGrant]) {self.grants=grants}
    func execute(_ attempt:TaskAssignAttempt) async throws -> SyntheticTaskAssignOutcome {let i=attempts.count;attempts.append(attempt);return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ value:SyntheticTaskAssignOutcome) {pending.removeValue(forKey:i)!.resume(returning:value)}
    func fail(_ i:Int) {pending.removeValue(forKey:i)!.resume(throwing:ReadFailure.unavailable)}
    func recorded()->[TaskAssignAttempt] {attempts}
}
@MainActor func checkTaskAssign(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func detail(_ b:Int=101,_ id:Int=1101) throws -> TaskDetails {try JSONDecoder().decode(TaskDetails.self,from:Data(contentsOf:directory.appendingPathComponent("task-\(b)-\(id).json")))}
    let original=try detail(),foreign=try detail(202,1201),fixture=FixtureTaskAssignPort(directory:directory)
    func source(_ d:TaskDetails,epoch:Int=180,revision:Int=1)->TaskAssignSource {TaskAssignSource(read:TaskCommentRead(context:TaskCommentContext(business:d.business,task:d.task.id,epoch:epoch),revision:revision),task:d.task)}
    let initial=source(original),port=ControlledTaskAssignPort(fixture.grants),m=TaskAssignViewModel(port:port)
    m.bind(initial);m.open(expected:m.control);let firstInput=m.inputControl
    try expect(m.raw.isEmpty && m.eligibleMembers==[9003,9001] && m.review==nil,"Assignment defaulted current actor or used GET catalogue")
    m.update("9999",input:firstInput);m.prepare(expected:m.control);try expect(m.showsIssue && m.review==nil && m.raw=="9999","Unconfigured target accepted or raw discarded")
    m.select(9003,input:m.inputControl);let editing=m.control!;m.prepare(expected:editing);let old=m.control!;m.back(expected:old)
    m.select(9001,input:firstInput);m.prepare(expected:editing);await m.submit(expected:old)
    let calls=await port.recorded();try expect(m.raw=="9003" && m.editing && m.review==nil && calls.isEmpty,"Old assignment editor/review acted after Back")
    m.askClear(expected:m.control);let question=m.clearConfirmation!;m.dismissClear(question);m.select(9001,input:m.inputControl);m.confirmClear(question)
    try expect(m.raw=="9001","Old clear erased explicit actor selection")
    m.askClear(expected:m.control);m.confirmClear(m.clearConfirmation!);try expect(m.raw.isEmpty && m.editing,"Exact clear inferred unassign/default actor")
    m.select(9003,input:m.inputControl);m.prepare(expected:m.control);let control=m.control!,send=Task {await m.submit(expected:control)};await port.wait(0)
    let pending=m.control!,record=m.submission!;await m.submit(expected:control);await m.submit(expected:pending);m.back(expected:pending);m.askClear(expected:pending);m.acknowledge(expected:pending,record:record)
    try expect(await port.recorded().count==1 && m.submission==record && m.raw=="9003" && m.clearConfirmation==nil,"Pending assignment repeated/lost input")
    await port.fail(0);await send.value;let unknown=m.submission!
    m.bind(source(original,epoch:181,revision:2));try expect(m.blocked && m.submission==nil && m.raw.isEmpty && !m.canOpen && m.canPresent,"Assignment matching reread/new epoch cleared quarantine")
    m.bind(initial);m.acknowledge(expected:m.control,record:unknown);try expect(m.blocked && unknown.attempt.review.value.raw=="9003","Unknown assignment acknowledged or lost target")
    let ok=TaskAssignViewModel(port:fixture);ok.bind(initial);ok.open(expected:ok.control);ok.select(9001,input:ok.inputControl);ok.prepare(expected:ok.control);let prior=ok.control!;await ok.submit(expected:prior);let accepted=ok.submission!
    try expect(accepted.phase == .confirmed && accepted.result?.assignee==9001 && accepted.result?.status=="open" && original.task.status=="open","Generic explicit actor assignment reused self-start semantics")
    ok.acknowledge(expected:ok.control,record:accepted);ok.open(expected:ok.control);await ok.submit(expected:prior);try expect(ok.consumed && !ok.editing && ok.retainedAttemptCount==1,"Confirmed assignment reused consumed read")
    let noWrite=TaskAssignViewModel(port:fixture);noWrite.bind(source(try detail(101,1401)));noWrite.open(expected:noWrite.control);noWrite.select(9003,input:noWrite.inputControl);noWrite.prepare(expected:noWrite.control);let rejectedControl=noWrite.control!;await noWrite.submit(expected:rejectedControl);let rejected=noWrite.submission!
    noWrite.acknowledge(expected:noWrite.control,record:rejected);await noWrite.submit(expected:rejectedControl);try expect(noWrite.editing && noWrite.raw=="9003" && noWrite.review==nil && noWrite.retainedAttemptCount==1,"No-write assignment repeated without new review")
    let latePort=ControlledTaskAssignPort(fixture.grants),late=TaskAssignViewModel(port:latePort);late.bind(initial);late.open(expected:late.control);late.select(9003,input:late.inputControl);late.prepare(expected:late.control);let job=Task {await late.submit(expected:late.control)};await latePort.wait(0)
    late.bind(source(foreign,epoch:182));late.open(expected:late.control);late.select(9004,input:late.inputControl);let replacement=late.control,attempt=await latePort.recorded()[0]
    await latePort.resolve(0,try await fixture.execute(attempt));await job.value;try expect(late.control==replacement && late.raw=="9004" && late.submission==nil,"Late assignment touched replacement target")
    let repository=APIReadRepository(transport:FixtureTransport(directory:directory)),plain=TaskListViewModel(repository:repository),unverified=TaskListViewModel(repository:repository,targetAssignSubmission:fixture)
    await unverified.load(business:101,epoch:183);await unverified.open(id:1101);try expect(plain.targetAssignment==nil && unverified.targetAssignment?.source==nil,"GET/default composition granted target assignment")
    let transport=SearchTransport(directory),flow=TaskListViewModel(repository:APIReadRepository(transport:transport),commentSource:FixtureTaskCommentDraftSource(directory:directory),cancelSubmission:FixtureTaskCancelPort(directory:directory),completeSubmission:FixtureTaskCompletePort(directory:directory),selfAssignSubmission:FixtureTaskSelfAssignPort(directory:directory),startSubmission:FixtureTaskStartPort(directory:directory),reopenSubmission:FixtureTaskReopenPort(directory:directory),watcherSubmission:FixtureTaskWatcherPort(directory:directory),undoCancelSubmission:FixtureTaskUndoCancelPort(directory:directory),snoozeSubmission:FixtureTaskSnoozePort(directory:directory),targetAssignSubmission:fixture)
    await flow.load(business:101,epoch:184);await flow.open(id:1101);let assign=flow.targetAssignment!,before=flow.detail!,rows=flow.items,reads=await transport.recorded().count
    let oldEntry=assign.control;flow.openSnooze(flow.snoozeAction?.control,parent:flow.control);flow.snoozeAction?.back(expected:flow.snoozeAction?.control);flow.openTargetAssign(oldEntry,parent:flow.control)
    try expect(!assign.editing,"Old assignment entry survived a completed peer visit")
    flow.openTargetAssign(assign.control,parent:flow.control);assign.select(9003,input:assign.inputControl)
    try expect(!flow.snoozeCurrent(flow.control) && !flow.startCurrent(flow.control) && !flow.completionCurrent(flow.control) && !flow.selfAssignmentCurrent(flow.control),"Target editor did not own peer visits")
    flow.openSnooze(flow.snoozeAction?.control,parent:flow.control);try expect(flow.snoozeAction?.editing==false && assign.editing,"Snooze stole active target editor")
    flow.openComment(assign.source!.read);try expect(!assign.editing,"Comment failed pre-submit interruption");if let c=flow.comment {c.close(expected:c.returnControl)}
    flow.openTargetAssign(assign.control,parent:flow.control);try expect(assign.raw=="9003","Comment return lost target draft")
    assign.prepare(expected:assign.control);await assign.submit(expected:assign.control);try expect(assign.submission?.phase == .confirmed && flow.detail==before && flow.items==rows,"Assignment fake changed source/list/status/assignee")
    try expect(await transport.recorded().count==reads,"Assignment caused request or reread")
    assign.acknowledge(expected:assign.control,record:assign.submission!);flow.openSnooze(flow.snoozeAction?.control,parent:flow.control);flow.openCancelReason(assign.source!.read)
    try expect(flow.snoozeAction?.editing==false && flow.cancelReason?.control==nil && flow.taskActionOccupied,"Consumed assignment read bypassed peer guards")
    // Reverse direction: matching-source snooze unknown remains independent outcome, not permission.
    let snoozePort=ControlledTaskSnoozePort(FixtureTaskSnoozePort(directory:directory).grants),peer=TaskListViewModel(repository:repository,commentSource:FixtureTaskCommentDraftSource(directory:directory),snoozeSubmission:snoozePort,targetAssignSubmission:fixture)
    await peer.load(business:101,epoch:185);await peer.open(id:1101);let snooze=peer.snoozeAction!;peer.openSnooze(snooze.control,parent:peer.control);snooze.update("2026-10-30T12:00:00Z",input:snooze.inputControl);snooze.prepare(expected:snooze.control)
    let pendingSnooze=Task {await snooze.submit(expected:snooze.control)};await snoozePort.wait(0);await snoozePort.resolve(0,.unknown);await pendingSnooze.value
    await peer.load(business:101,epoch:186);await peer.open(id:1101);peer.openTargetAssign(peer.targetAssignment?.control,parent:peer.control)
    try expect(peer.targetAssignment?.editing==false && peer.taskActionOccupied,"Snooze unknown/read/epoch granted new assignment")
    return count
}
