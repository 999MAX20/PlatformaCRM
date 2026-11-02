import Foundation
import CRMCore

actor ControlledTaskDateEditPort:SyntheticTaskDateEditPort {
    nonisolated let grants:[SyntheticTaskDateEditGrant]
    private var attempts:[TaskDateEditAttempt]=[]
    private var pending:[Int:CheckedContinuation<SyntheticTaskDateEditOutcome,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    init(_ grants:[SyntheticTaskDateEditGrant]) {self.grants=grants}
    func execute(_ attempt:TaskDateEditAttempt) async throws -> SyntheticTaskDateEditOutcome {let i=attempts.count;attempts.append(attempt);return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ value:SyntheticTaskDateEditOutcome) {pending.removeValue(forKey:i)!.resume(returning:value)}
    func fail(_ i:Int) {pending.removeValue(forKey:i)!.resume(throwing:ReadFailure.unavailable)}
    func recorded()->[TaskDateEditAttempt] {attempts}
}
@MainActor func checkTaskDateEdit(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func detail(_ b:Int=101,_ id:Int=1101) throws -> TaskDetails {try JSONDecoder().decode(TaskDetails.self,from:Data(contentsOf:directory.appendingPathComponent("task-\(b)-\(id).json")))}
    let original=try detail(),foreign=try detail(202,1201),fixture=FixtureTaskDateEditPort(directory:directory)
    func source(_ d:TaskDetails,epoch:Int=190,revision:Int=1)->TaskDateEditSource {TaskDateEditSource(read:TaskCommentRead(context:TaskCommentContext(business:d.business,task:d.task.id,epoch:epoch),revision:revision),task:d.task)}
    let initial=source(original),port=ControlledTaskDateEditPort(fixture.grants),m=TaskDateEditViewModel(port:port)
    m.bind(initial);m.open(expected:m.control);m.prepare(expected:m.control)
    try expect(m.showsIssue && m.draft.field==nil && m.draft.mode==nil && m.review==nil,"Date invented default field/mode/date")
    m.select(.dueAt,expected:m.control);m.choose(.setDate,expected:m.control);let dueInput=m.inputControl;m.update("2026-10-30T12:00:00Z",input:dueInput)
    m.select(.reminderAt,expected:m.control);try expect(m.draft.mode==nil && m.draft.raw.isEmpty,"Date field switch prefilled another field")
    m.choose(.clearDate,expected:m.control);m.update("old",input:dueInput);try expect(m.draft.mode == .clearDate && m.draft.raw.isEmpty,"Old field input edited selected clear intention")
    m.select(.dueAt,expected:m.control);try expect(m.draft.raw=="2026-10-30T12:00:00Z" && m.draft.mode == .setDate,"Field return lost unsent raw/mode")
    let editor=m.control!;m.prepare(expected:editor);let old=m.control!;m.back(expected:old);m.update("stale",input:dueInput);m.prepare(expected:editor);await m.submit(expected:old)
    let calls=await port.recorded();try expect(m.review==nil && m.draft.raw==editor.draft.raw && calls.isEmpty,"Old date review/input acted after Back")
    m.askClear(expected:m.control);let question=m.clearConfirmation!;m.dismissClear(question);m.select(.reminderAt,expected:m.control);m.confirmClear(question)
    try expect(m.draft.field == .reminderAt && m.draft.mode == .clearDate,"Old draft clear erased new field/intent")
    m.askClear(expected:m.control);m.confirmClear(m.clearConfirmation!);m.prepare(expected:m.control);try expect(m.draft.field==nil && m.review==nil && m.showsIssue,"Draft clear became a null command")
    m.select(.dueAt,expected:m.control);m.choose(.setDate,expected:m.control);m.update("2000-02-29T00:00:00Z",input:m.inputControl);m.prepare(expected:m.control);let submit=m.control!,job=Task {await m.submit(expected:submit)};await port.wait(0)
    let pending=m.control!,record=m.submission!;await m.submit(expected:submit);await m.submit(expected:pending);m.back(expected:pending);m.select(.reminderAt,expected:pending);m.askClear(expected:pending);m.acknowledge(expected:pending,record:record)
    try expect(await port.recorded().count==1 && m.submission==record && m.draft.field == .dueAt && m.clearConfirmation==nil,"Pending date lost intent or repeated")
    await port.fail(0);await job.value;let unknown=m.submission!
    m.bind(source(original,epoch:191,revision:2));try expect(m.blocked && m.submission==nil && m.draft.field==nil && !m.canOpen && m.canPresent,"New date read/epoch cleared quarantine or exposed old draft")
    m.bind(initial);m.acknowledge(expected:m.control,record:unknown);try expect(m.blocked && unknown.attempt.review.change.field == .dueAt && unknown.attempt.review.change.mode == .setDate && unknown.attempt.review.change.raw=="2000-02-29T00:00:00Z","Unknown date lost field/mode/raw or acknowledged")
    // Explicit selected null in fake response, no optimistic changes to the source.
    let ok=TaskDateEditViewModel(port:fixture);ok.bind(initial);ok.open(expected:ok.control);ok.select(.dueAt,expected:ok.control);ok.choose(.clearDate,expected:ok.control);ok.prepare(expected:ok.control);let prior=ok.control!;await ok.submit(expected:prior);let accepted=ok.submission!
    try expect(accepted.phase == .confirmed && accepted.result?.field == .dueAt && accepted.result?.value==nil && original.task.due_at != nil && original.details.reminder_at == .notSet,"Fake selected clear changed GET or inferred another date")
    ok.acknowledge(expected:ok.control,record:accepted);ok.open(expected:ok.control);await ok.submit(expected:prior);try expect(ok.consumed && !ok.editing && ok.retainedAttemptCount==1,"Date consumed read reused")
    let noWrite=TaskDateEditViewModel(port:fixture);noWrite.bind(source(try detail(101,1401)));noWrite.open(expected:noWrite.control);noWrite.select(.reminderAt,expected:noWrite.control);noWrite.choose(.clearDate,expected:noWrite.control);noWrite.prepare(expected:noWrite.control);let rejectedControl=noWrite.control!;await noWrite.submit(expected:rejectedControl);let rejected=noWrite.submission!
    noWrite.acknowledge(expected:noWrite.control,record:rejected);await noWrite.submit(expected:rejectedControl);try expect(noWrite.editing && noWrite.draft.field == .reminderAt && noWrite.draft.mode == .clearDate && noWrite.review==nil && noWrite.retainedAttemptCount==1,"No-write date retried without review or lost intention")
    let latePort=ControlledTaskDateEditPort(fixture.grants),late=TaskDateEditViewModel(port:latePort);late.bind(initial);late.open(expected:late.control);late.select(.dueAt,expected:late.control);late.choose(.clearDate,expected:late.control);late.prepare(expected:late.control);let send=Task {await late.submit(expected:late.control)};await latePort.wait(0)
    late.bind(source(foreign,epoch:192));late.open(expected:late.control);late.select(.reminderAt,expected:late.control);late.choose(.setDate,expected:late.control);late.update("2038-01-19T03:14:08Z",input:late.inputControl);let replacement=late.control,attempt=await latePort.recorded()[0]
    await latePort.resolve(0,try await fixture.execute(attempt));await send.value;try expect(late.control==replacement && late.draft.raw=="2038-01-19T03:14:08Z" && late.submission==nil,"Late date touched replacement field/owner")
    let repository=APIReadRepository(transport:FixtureTransport(directory:directory)),plain=TaskListViewModel(repository:repository),unverified=TaskListViewModel(repository:repository,dateEditSubmission:fixture)
    await unverified.load(business:101,epoch:193);await unverified.open(id:1101);try expect(plain.dateEdit==nil && unverified.dateEdit?.source==nil,"GET/default composition granted date UPDATE")
    let transport=SearchTransport(directory),flow=TaskListViewModel(repository:APIReadRepository(transport:transport),commentSource:FixtureTaskCommentDraftSource(directory:directory),snoozeSubmission:FixtureTaskSnoozePort(directory:directory),targetAssignSubmission:FixtureTaskAssignPort(directory:directory),dateEditSubmission:fixture)
    await flow.load(business:101,epoch:194);await flow.open(id:1101);let dates=flow.dateEdit!,before=flow.detail!,rows=flow.items,reads=await transport.recorded().count
    let oldEntry=dates.control;flow.openTargetAssign(flow.targetAssignment?.control,parent:flow.control);flow.targetAssignment?.back(expected:flow.targetAssignment?.control);flow.openDateEdit(oldEntry,parent:flow.control);try expect(!dates.editing,"Old date entry survived another completed editor visit")
    flow.openDateEdit(dates.control,parent:flow.control);dates.select(.reminderAt,expected:dates.control);dates.choose(.setDate,expected:dates.control);dates.update("2026-10-30T17:00:00+05:00",input:dates.inputControl)
    try expect(!flow.targetAssignCurrent(flow.control) && !flow.snoozeCurrent(flow.control),"Date editor did not own peer visit")
    flow.openComment(dates.source!.read);if let c=flow.comment {c.close(expected:c.returnControl)};flow.openDateEdit(dates.control,parent:flow.control);try expect(dates.draft.field == .reminderAt && dates.draft.raw=="2026-10-30T17:00:00+05:00","Comment return lost selected date draft")
    dates.prepare(expected:dates.control);let body=try JSONSerialization.jsonObject(with:dates.review!.change.body()!) as! [String:Any];try expect(Set(body.keys)==["reminder_at"] && body["description"]==nil && body["due_at"]==nil,"Partial date serialized bounded description or untouched date")
    await dates.submit(expected:dates.control);try expect(dates.submission?.phase == .confirmed && flow.detail==before && flow.items==rows,"Date fake changed Task/read/description/other fields")
    try expect(await transport.recorded().count==reads,"Date fake caused request/reload")
    dates.acknowledge(expected:dates.control,record:dates.submission!);flow.openTargetAssign(flow.targetAssignment?.control,parent:flow.control);flow.openSnooze(flow.snoozeAction?.control,parent:flow.control);try expect(flow.targetAssignment?.editing==false && flow.snoozeAction?.editing==false && flow.taskActionOccupied,"Consumed date read bypassed peers")
    let held=ControlledTaskDateEditPort(fixture.grants),unknownFlow=TaskListViewModel(repository:repository,commentSource:FixtureTaskCommentDraftSource(directory:directory),completeSubmission:FixtureTaskCompletePort(directory:directory),selfAssignSubmission:FixtureTaskSelfAssignPort(directory:directory),startSubmission:FixtureTaskStartPort(directory:directory),reopenSubmission:FixtureTaskReopenPort(directory:directory),watcherSubmission:FixtureTaskWatcherPort(directory:directory),undoCancelSubmission:FixtureTaskUndoCancelPort(directory:directory),snoozeSubmission:FixtureTaskSnoozePort(directory:directory),targetAssignSubmission:FixtureTaskAssignPort(directory:directory),dateEditSubmission:held)
    await unknownFlow.load(business:101,epoch:197);await unknownFlow.open(id:1101);let ud=unknownFlow.dateEdit!;unknownFlow.openDateEdit(ud.control,parent:unknownFlow.control);ud.select(.dueAt,expected:ud.control);ud.choose(.clearDate,expected:ud.control);ud.prepare(expected:ud.control)
    guard let pendingControl=ud.control,ud.review != nil else {throw ViewModelCheckFailure(message:"Current date review missing before controlled wait")}
    let unknownJob=Task {await ud.submit(expected:pendingControl)};await held.wait(0);await held.resolve(0,.unknown);await unknownJob.value
    await unknownFlow.load(business:101,epoch:198);await unknownFlow.open(id:1101)
    try expect(unknownFlow.taskActionOccupied && !unknownFlow.targetAssignCurrent(unknownFlow.control) && !unknownFlow.snoozeCurrent(unknownFlow.control) && !unknownFlow.startCurrent(unknownFlow.control) && !unknownFlow.completionCurrent(unknownFlow.control) && !unknownFlow.selfAssignmentCurrent(unknownFlow.control) && !unknownFlow.reopenCurrent(unknownFlow.control) && !unknownFlow.watcherCurrent(unknownFlow.control) && !unknownFlow.undoCancelCurrent(unknownFlow.control),"Date unknown/read/epoch did not guard all eight peers")
    try expect(ud.submission==nil && ud.retainedAttemptCount==1 && ud.draft.field==nil,"Date old-owner input exposed or attempt lost")
    return count
}
