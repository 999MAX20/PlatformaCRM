import Foundation
import CRMCore

actor ControlledTaskPriorityEditPort:SyntheticTaskPriorityEditPort {
    nonisolated let grants:[SyntheticTaskPriorityEditGrant]
    private var attempts:[TaskPriorityEditAttempt]=[]
    private var pending:[Int:CheckedContinuation<SyntheticTaskPriorityEditOutcome,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    init(_ grants:[SyntheticTaskPriorityEditGrant]) {self.grants=grants}
    func execute(_ attempt:TaskPriorityEditAttempt) async throws -> SyntheticTaskPriorityEditOutcome {let i=attempts.count;attempts.append(attempt);return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ value:SyntheticTaskPriorityEditOutcome) {pending.removeValue(forKey:i)!.resume(returning:value)}
    func fail(_ i:Int) {pending.removeValue(forKey:i)!.resume(throwing:ReadFailure.unavailable)}
    func recorded()->[TaskPriorityEditAttempt] {attempts}
}
@MainActor func checkTaskPriorityEdit(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func detail(_ b:Int=101,_ id:Int=1101) throws -> TaskDetails {try JSONDecoder().decode(TaskDetails.self,from:Data(contentsOf:directory.appendingPathComponent("task-\(b)-\(id).json")))}
    func source(_ d:TaskDetails,epoch:Int=200,revision:Int=1)->TaskPriorityEditSource {TaskPriorityEditSource(read:TaskCommentRead(context:TaskCommentContext(business:d.business,task:d.task.id,epoch:epoch),revision:revision),task:d.task)}
    let original=try detail(),initial=source(original),fixture=FixtureTaskPriorityEditPort(directory:directory),port=ControlledTaskPriorityEditPort(fixture.grants),m=TaskPriorityEditViewModel(port:port)
    m.bind(initial);m.open(expected:m.control);m.prepare(expected:m.control);try expect(m.raw.isEmpty && m.review==nil && m.showsIssue,"Priority defaulted to source/normal")
    let unset=m.control;m.choose("high",expected:unset);m.choose("normal",expected:unset);try expect(m.raw=="high","Old choice control changed priority")
    m.choose("urgent ",expected:m.control);try expect(m.raw=="high","Priority trimmed/coerced invalid choice")
    m.prepare(expected:m.control);let reviewed=m.control!;m.back(expected:reviewed);await m.submit(expected:reviewed);let callsAfterBack=await port.recorded();try expect(m.review==nil && m.raw=="high" && callsAfterBack.isEmpty,"Old priority review submitted after Back")
    m.askClear(expected:m.control);let old=m.clearConfirmation!;m.dismissClear(old);m.choose("low",expected:m.control);m.confirmClear(old);try expect(m.raw=="low","Old reset erased later choice")
    m.askClear(expected:m.control);m.confirmClear(m.clearConfirmation!);m.prepare(expected:m.control);try expect(m.raw.isEmpty && m.review==nil && m.showsIssue,"Local priority reset became normal/null command")
    m.choose("urgent",expected:m.control);m.prepare(expected:m.control);let send=m.control!,job=Task {await m.submit(expected:send)};await port.wait(0);let pending=m.control!,record=m.submission!
    m.choose("low",expected:pending);m.askClear(expected:pending);m.back(expected:pending);m.acknowledge(expected:pending,record:record);await m.submit(expected:send);await m.submit(expected:pending)
    let pendingCalls=await port.recorded();try expect(m.raw=="urgent" && m.submission==record && pendingCalls.count==1,"Pending priority lost exact choice or repeated")
    await port.fail(0);await job.value;let unknown=m.submission!;m.bind(source(original,epoch:201,revision:2));try expect(m.blocked && m.submission==nil && m.raw.isEmpty && !m.canOpen,"New epoch cleared priority attempt")
    m.bind(initial);m.acknowledge(expected:m.control,record:unknown);try expect(m.blocked && unknown.attempt.review.value.raw=="urgent" && unknown.attempt.review.source==initial,"Unknown priority lost choice/source or acknowledged")
    let ok=TaskPriorityEditViewModel(port:fixture);ok.bind(initial);ok.open(expected:ok.control);ok.choose("low",expected:ok.control);ok.prepare(expected:ok.control);let prior=ok.control!;await ok.submit(expected:prior);let accepted=ok.submission!
    try expect(accepted.phase == .confirmed && accepted.result?.priority=="low" && ok.source==initial,"Fake priority changed source")
    ok.acknowledge(expected:ok.control,record:accepted);ok.open(expected:ok.control);await ok.submit(expected:prior);try expect(ok.consumed && !ok.editing && ok.raw.isEmpty && ok.retainedAttemptCount==1,"Confirmed priority reused consumed read")
    let rejected=TaskPriorityEditViewModel(port:fixture);rejected.bind(source(try detail(101,1401)));rejected.open(expected:rejected.control);rejected.choose("normal",expected:rejected.control);rejected.prepare(expected:rejected.control);let rc=rejected.control!;await rejected.submit(expected:rc);let rr=rejected.submission!;rejected.acknowledge(expected:rejected.control,record:rr);await rejected.submit(expected:rc)
    try expect(rejected.editing && rejected.raw=="normal" && rejected.review==nil && rejected.retainedAttemptCount==1,"No-write priority auto-retried/lost choice")
    let lp=ControlledTaskPriorityEditPort(fixture.grants),late=TaskPriorityEditViewModel(port:lp);late.bind(initial);late.open(expected:late.control);late.choose("low",expected:late.control);late.prepare(expected:late.control);let lj=Task {await late.submit(expected:late.control)};await lp.wait(0)
    late.bind(source(try detail(202,1201),epoch:202));late.open(expected:late.control);late.choose("high",expected:late.control);let replacement=late.control,attempt=await lp.recorded()[0];await lp.resolve(0,try await fixture.execute(attempt));await lj.value
    try expect(late.control==replacement && late.raw=="high" && late.submission==nil,"Late priority touched replacement owner")
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),plain=TaskListViewModel(repository:repo),unverified=TaskListViewModel(repository:repo,priorityEditSubmission:fixture)
    await unverified.load(business:101,epoch:203);await unverified.open(id:1101);try expect(plain.priorityEdit==nil && unverified.priorityEdit?.source==nil,"Default/GET source granted UPDATE")
    let transport=SearchTransport(directory),flow=TaskListViewModel(repository:APIReadRepository(transport:transport),commentSource:FixtureTaskCommentDraftSource(directory:directory),dateEditSubmission:FixtureTaskDateEditPort(directory:directory),priorityEditSubmission:fixture)
    await flow.load(business:101,epoch:204);await flow.open(id:1101);let v=flow.priorityEdit!,before=flow.detail!,items=flow.items,reads=await transport.recorded().count
    let oldEntry=v.control;flow.openDateEdit(flow.dateEdit?.control,parent:flow.control);flow.dateEdit?.back(expected:flow.dateEdit?.control);flow.openPriorityEdit(oldEntry,parent:flow.control);try expect(!v.editing,"Old priority entry survived date visit")
    flow.openPriorityEdit(v.control,parent:flow.control);v.choose("urgent",expected:v.control);try expect(!flow.dateEditCurrent(flow.control),"Priority editor failed peer ownership")
    flow.openComment(v.source!.read);if let c=flow.comment {c.close(expected:c.returnControl)};flow.openPriorityEdit(v.control,parent:flow.control);try expect(v.raw=="urgent","Comment return lost priority choice")
    v.prepare(expected:v.control);let body=try JSONSerialization.jsonObject(with:v.review!.value.body()!) as! [String:Any];try expect(Set(body.keys)==["priority"],"Priority serialized untouched fields");await v.submit(expected:v.control)
    let finalReads=await transport.recorded().count;try expect(v.submission?.phase == .confirmed && flow.detail==before && flow.items==items && finalReads==reads,"Fake priority mutated GET or caused read/write")
    v.acknowledge(expected:v.control,record:v.submission!);flow.openDateEdit(flow.dateEdit?.control,parent:flow.control);try expect(flow.dateEdit?.editing==false && flow.taskActionOccupied,"Consumed priority read bypassed dates")
    // Retained unknown for priority blocks every existing peer after owner replacement.
    let qp=ControlledTaskPriorityEditPort(fixture.grants),quarantined=TaskListViewModel(repository:repo,commentSource:FixtureTaskCommentDraftSource(directory:directory),completeSubmission:FixtureTaskCompletePort(directory:directory),selfAssignSubmission:FixtureTaskSelfAssignPort(directory:directory),startSubmission:FixtureTaskStartPort(directory:directory),reopenSubmission:FixtureTaskReopenPort(directory:directory),watcherSubmission:FixtureTaskWatcherPort(directory:directory),undoCancelSubmission:FixtureTaskUndoCancelPort(directory:directory),snoozeSubmission:FixtureTaskSnoozePort(directory:directory),targetAssignSubmission:FixtureTaskAssignPort(directory:directory),dateEditSubmission:FixtureTaskDateEditPort(directory:directory),priorityEditSubmission:qp)
    await quarantined.load(business:101,epoch:205);await quarantined.open(id:1101);let q=quarantined.priorityEdit!;quarantined.openPriorityEdit(q.control,parent:quarantined.control);q.choose("urgent",expected:q.control);q.prepare(expected:q.control);let qj=Task {await q.submit(expected:q.control)};await qp.wait(0);await qp.resolve(0,.unknown);await qj.value
    await quarantined.load(business:101,epoch:206);await quarantined.open(id:1101);let parent=quarantined.control
    try expect(quarantined.taskActionOccupied && q.submission==nil && q.canPresent && q.retainedAttemptCount==1,"Matching read released priority quarantine")
    for current in [quarantined.completionCurrent(parent),quarantined.selfAssignmentCurrent(parent),quarantined.startCurrent(parent),quarantined.reopenCurrent(parent),quarantined.watcherCurrent(parent),quarantined.undoCancelCurrent(parent),quarantined.snoozeCurrent(parent),quarantined.targetAssignCurrent(parent),quarantined.dateEditCurrent(parent)] {try expect(!current,"Unknown priority bypassed existing peer")}
    let dp=ControlledTaskDateEditPort(FixtureTaskDateEditPort(directory:directory).grants),opposite=TaskListViewModel(repository:repo,commentSource:FixtureTaskCommentDraftSource(directory:directory),dateEditSubmission:dp,priorityEditSubmission:fixture)
    await opposite.load(business:101,epoch:207);await opposite.open(id:1101);let d=opposite.dateEdit!;opposite.openDateEdit(d.control,parent:opposite.control);d.select(.dueAt,expected:d.control);d.choose(.clearDate,expected:d.control);d.prepare(expected:d.control);let dj=Task {await d.submit(expected:d.control)};await dp.wait(0);await dp.resolve(0,.unknown);await dj.value
    await opposite.load(business:101,epoch:208);await opposite.open(id:1101);opposite.openPriorityEdit(opposite.priorityEdit?.control,parent:opposite.control)
    try expect(opposite.priorityEdit?.editing==false && opposite.taskActionOccupied && !opposite.priorityEditCurrent(opposite.control),"Unknown date bypassed independent priority")
    return count
}
