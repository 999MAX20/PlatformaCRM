import Foundation
import CRMCore

actor ControlledTaskStartPort:SyntheticTaskStartPort {
    nonisolated let grants:[SyntheticTaskStartGrant]
    private var attempts:[TaskStartAttempt]=[]
    private var pending:[Int:CheckedContinuation<SyntheticTaskStartOutcome,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    init(_ grants:[SyntheticTaskStartGrant]) {self.grants=grants}
    func execute(_ attempt:TaskStartAttempt) async throws -> SyntheticTaskStartOutcome {let i=attempts.count;attempts.append(attempt);return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ outcome:SyntheticTaskStartOutcome) {pending.removeValue(forKey:i)!.resume(returning:outcome)}
    func fail(_ i:Int) {pending.removeValue(forKey:i)!.resume(throwing:CancellationError())}
    func recorded()->[TaskStartAttempt] {attempts}
}
actor TaskStartReadFixture:TaskReadRepository {
    let base:APIReadRepository
    private var selected:TaskDetails
    init(directory:URL,selected:TaskDetails) {base=APIReadRepository(transport:FixtureTransport(directory:directory));self.selected=selected}
    func set(_ next:TaskDetails) {selected=next}
    func tasks(business:Int) async throws -> TaskPage {try await base.tasks(business:business)}
    func taskDetails(business:Int,id:Int) async throws -> TaskDetails {if selected.business==business && selected.task.id==id {return selected};return try await base.taskDetails(business:business,id:id)}
}
struct TaskStartFixtureOrigin:TaskCommentDraftSource {
    let allowed:[TaskDetails]
    func matchesFixture(_ detail:TaskDetails) async -> Bool {allowed.contains(detail)}
}
struct TaskStartUnknownCancelFixture:SyntheticTaskCancelPort {let grants:[SyntheticTaskCancelGrant];func execute(_ attempt:TaskCancelAttempt) async throws -> SyntheticTaskCancelOutcome {.unknown}}
@MainActor func checkTaskStart(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func data(_ name:String) throws -> Data {try Data(contentsOf:directory.appendingPathComponent(name+".json"))}
    func detail(_ name:String) throws -> TaskDetails {try JSONDecoder().decode(TaskDetails.self,from:data(name))}
    let original=try detail("task-101-1101"),foreign=try detail("task-202-1201"),context=TaskCommentContext(business:101,task:1101,epoch:160),fixture=FixtureTaskStartPort(directory:directory)
    func source(_ payload:TaskDetails,epoch:Int=160,revision:Int=1)->TaskStartSource {TaskStartSource(read:TaskCommentRead(context:TaskCommentContext(business:payload.business,task:payload.task.id,epoch:epoch),revision:revision),task:payload.task,assignee:payload.details.assignee)}
    func variant(_ status:String) throws -> TaskDetails {var o=try JSONSerialization.jsonObject(with:data("task-101-1101")) as! [String:Any];var t=o["task"] as! [String:Any];t["status"]=status;o["task"]=t;return try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:o))}
    let initial=source(original),auth=fixture.grants.compactMap {$0.authorization(for:context)}.first!
    try expect(initial.valid && SyntheticTaskStartGrant(business:101,task:1101,actor:9001,update:false).authorization(for:context)==nil,"GET or false UPDATE granted start")
    for status in ["in_progress","done","cancelled","waiting",""] {let next=source(try variant(status));var ledger=TaskStartLedger();try expect(next.identityValid && !next.valid && ledger.begin(TaskStartReview(source:next,visit:1),authorization:auth)==nil,"Start accepted non-open status or discarded valid identity")}
    let cases=(try JSONSerialization.jsonObject(with:data("task-start-outcome")) as! [String:Any])["validation_cases"] as! [[String:Any]]
    for row in cases {
        var o=try JSONSerialization.jsonObject(with:data("task-101-1101")) as! [String:Any],fields:[String:Any]=[:];fields=o["details"] as! [String:Any]
        if let value=row["source_assignee"] {fields["assignee"]=value};if row["omit_source_assignee"] as? Bool==true {fields.removeValue(forKey:"assignee")};o["details"]=fields
        let payload=try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:o)),snapshot=source(payload),review=TaskStartReview(source:snapshot,visit:1)
        var ledger=TaskStartLedger();let attempt=ledger.begin(review,authorization:auth)!;try expect(ledger.begin(review,authorization:auth)==nil,"Duplicate pending start admitted")
        ledger.complete(attempt,outcome:.response(status:row["status"] as! Int,data:try JSONSerialization.data(withJSONObject:row["response"]!)));let record=ledger.visible(auth)!
        try expect(record.phase == (row["expected"] as! String=="confirmed" ? .confirmed:.unknown),"Start accepted wrong scope/status/assignee/shape: \(row["name"]!)")
        ledger.complete(attempt,outcome:.rejectedWithoutWrite);try expect(ledger.visible(auth)==record && record.attempt.review==review,"Late result replaced immutable start snapshot/outcome")
        if record.phase == .unknown {try expect(!ledger.acknowledge(auth),"Unknown start was acknowledged")}
    }
    let controlPort=ControlledTaskStartPort(fixture.grants),model=TaskStartViewModel(port:controlPort);model.bind(initial);model.prepare(expected:model.control);let old=model.control!;model.back(expected:old);model.prepare(expected:model.control)
    await model.submit(expected:old);try expect(await controlPort.recorded().isEmpty,"Identical preview revived old start Submit")
    let submit=model.control!,sending=Task {await model.submit(expected:submit)};await controlPort.wait(0);let pending=model.control!,pendingRecord=model.submission!
    await model.submit(expected:submit);await model.submit(expected:pending);model.back(expected:pending);model.acknowledge(expected:pending,record:pendingRecord)
    try expect(await controlPort.recorded().count==1 && model.submission==pendingRecord,"Pending start duplicate/Back/ack changed attempt")
    await controlPort.fail(0);await sending.value;let unknown=model.submission!
    let progress=try variant("in_progress"),done=try variant("done")
    model.bind(source(progress,revision:2));try expect(model.source?.valid==false && model.blocked && model.canPresent && model.submission?.attempt==unknown.attempt,"Matching in-progress reread erased or proved unknown start")
    model.bind(source(done,epoch:161,revision:3));try expect(model.submission==nil && model.blocks(context:context) && !model.canPrepare && model.canPresent,"New epoch/terminal status exposed or cleared retained start")
    let latePort=ControlledTaskStartPort(fixture.grants),late=TaskStartViewModel(port:latePort);late.bind(initial);late.prepare(expected:late.control);let job=Task {await late.submit(expected:late.control)};await latePort.wait(0);late.bind(source(foreign,epoch:162));let newControl=late.control
    var ledger=TaskStartLedger();let attempt=ledger.begin(TaskStartReview(source:initial,visit:1),authorization:auth)!
    await latePort.resolve(0,try await fixture.execute(attempt));await job.value;try expect(late.control==newControl && late.submission==nil && late.canPrepare,"Late start mutated replacement owner/input")
    late.bind(initial);let result=late.submission!;try expect(result.phase == .confirmed && result.result?.assignee==nil,"Start did not preserve explicit no-assignee result")
    late.acknowledge(expected:late.control,record:result);late.prepare(expected:late.control);try expect(late.consumed && late.review==nil && original.task.status=="open","Confirmed start reused current read or mutated GET")
    let rejection=TaskStartViewModel(port:fixture);rejection.bind(source(try detail("task-101-1401")));rejection.prepare(expected:rejection.control);await rejection.submit(expected:rejection.control);let noWrite=rejection.submission!
    try expect(noWrite.phase == .rejected,"Explicit no-write start was not rejected");rejection.acknowledge(expected:rejection.control,record:noWrite);try expect(rejection.canPrepare && rejection.review==nil,"No-write start automatically replayed or retained old preview")
    // Source GET, no independent provenance/port: no authority or action.
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),readOnly=TaskListViewModel(repository:repo,startSubmission:fixture),plain=TaskListViewModel(repository:repo)
    await readOnly.load(business:101,epoch:163);await readOnly.open(id:1101);try expect(readOnly.startAction?.source==nil && plain.startAction==nil,"GET/default composition granted start")
    // Source list/detail remain unchanged; peer prepare/result cannot consume the same read.
    let transport=SearchTransport(directory),list=TaskListViewModel(repository:APIReadRepository(transport:transport),commentSource:FixtureTaskCommentDraftSource(directory:directory),cancelSubmission:FixtureTaskCancelPort(directory:directory),completeSubmission:FixtureTaskCompletePort(directory:directory),selfAssignSubmission:FixtureTaskSelfAssignPort(directory:directory),startSubmission:fixture)
    await list.load(business:101,epoch:164);await list.open(id:1101);let start=list.startAction!,before=list.detail!,items=list.items,readCount=await transport.recorded().count
    list.prepareStart(start.control,parent:list.control);let stale=start.control!;list.openComment(start.source!.read);await start.submit(expected:stale);try expect(start.retainedAttemptCount==0,"Comment visit retained old start preview")
    if let comment=list.comment {comment.close(expected:comment.returnControl)}
    list.prepareStart(start.control,parent:list.control);await start.submit(expected:start.control);try expect(start.submission?.phase == .confirmed && list.detail==before && list.items==items,"Fake start changed source/list/assignee/status/comments")
    try expect(await transport.recorded().count==readCount,"Fake start caused another GET or real command")
    let known=start.submission!;start.acknowledge(expected:start.control,record:known);list.prepareCompletion(list.completion?.control,parent:list.control);list.prepareSelfAssignment(list.selfAssignment?.control,parent:list.control);list.openCancelReason(start.source!.read)
    try expect(list.completion?.review==nil && list.selfAssignment?.review==nil && list.cancelReason?.control==nil,"Consumed start read bypassed through another action")
    // Matching reread is not result recovery even when independent fixture provenance is valid.
    let origin=TaskStartFixtureOrigin(allowed:[original,progress,done,foreign]),mutable=TaskStartReadFixture(directory:directory,selected:original),held=ControlledTaskStartPort(fixture.grants)
    let flow=TaskListViewModel(repository:mutable,commentSource:origin,completeSubmission:FixtureTaskCompletePort(directory:directory),selfAssignSubmission:FixtureTaskSelfAssignPort(directory:directory),startSubmission:held)
    await flow.load(business:101,epoch:165);await flow.open(id:1101);let active=flow.startAction!;flow.prepareStart(active.control,parent:flow.control);let run=Task {await active.submit(expected:active.control)};await held.wait(0);await held.resolve(0,.unknown);await run.value
    await mutable.set(progress);await flow.retryDetail(expected:flow.detailSelection);flow.prepareCompletion(flow.completion?.control,parent:flow.control);flow.prepareSelfAssignment(flow.selfAssignment?.control,parent:flow.control)
    try expect(active.source?.task.status=="in_progress" && active.submission?.phase == .unknown && flow.taskActionOccupied && flow.completion?.review==nil && flow.selfAssignment?.review==nil,"Matching progress read released unknown start barrier")
    await mutable.set(done);await flow.retryDetail(expected:flow.detailSelection);try expect(flow.taskActionOccupied && active.submission?.phase == .unknown,"Terminal reread erased retained start context")
    await flow.load(business:202,epoch:166);await flow.open(id:1201)
    try expect(!flow.taskActionOccupied && active.canPrepare && flow.startCurrent(flow.control) && active.retainedAttemptCount==1,"Unknown start blocked an unrelated Business/Task")
    // Existing actions also retain their context when a new source status hides their UI.
    for assigning in [false,true] {
        await mutable.set(original);let completePort=ControlledTaskCompletePort(FixtureTaskCompletePort(directory:directory).grants),assignPort=ControlledTaskSelfAssignPort(FixtureTaskSelfAssignPort(directory:directory).grants)
        let owner=TaskListViewModel(repository:mutable,commentSource:origin,completeSubmission:completePort,selfAssignSubmission:assignPort,startSubmission:fixture)
        await owner.load(business:101,epoch:166);await owner.open(id:1101);let operation:Task<Void,Never>
        if assigning {let m=owner.selfAssignment!;owner.prepareSelfAssignment(m.control,parent:owner.control);operation=Task {await m.submit(expected:m.control)};await assignPort.wait(0);await assignPort.resolve(0,.unknown)}
        else {let m=owner.completion!;owner.prepareCompletion(m.control,parent:owner.control);operation=Task {await m.submit(expected:m.control)};await completePort.wait(0);await completePort.resolve(0,.unknown)}
        await operation.value;await mutable.set(done);await owner.retryDetail(expected:owner.detailSelection)
        try expect(owner.completion?.source==nil && owner.selfAssignment?.source==nil && owner.taskActionOccupied && owner.hasHiddenRetainedAction,"Ineligible reread hid and released an existing unknown action")
        owner.prepareStart(owner.startAction?.control,parent:owner.control);try expect(owner.startAction?.review==nil,"Start bypassed an existing hidden retained attempt")
    }
    await mutable.set(original)
    let canceled=TaskListViewModel(repository:mutable,commentSource:origin,cancelSubmission:TaskStartUnknownCancelFixture(grants:FixtureTaskCancelPort(directory:directory).grants),completeSubmission:FixtureTaskCompletePort(directory:directory),selfAssignSubmission:FixtureTaskSelfAssignPort(directory:directory),startSubmission:fixture)
    await canceled.load(business:101,epoch:168);await canceled.open(id:1101);let reason=canceled.cancelReason!
    canceled.openCancelReason(reason.session.read!);reason.update("Manual source reason",input:reason.inputControl);reason.prepare(expected:reason.control);await reason.submit(reason.session.review!,expected:reason.control);reason.close(expected:reason.returnControl)
    canceled.prepareStart(canceled.startAction?.control,parent:canceled.control);try expect(canceled.startAction?.review==nil,"Start bypassed retained cancellation")
    await mutable.set(done);await canceled.retryDetail(expected:canceled.detailSelection)
    try expect(reason.submissionBlocked && canceled.hasHiddenRetainedAction && !canceled.startCurrent(canceled.control) && reason.retainedAttemptCount==1,"Changed read status erased hidden cancellation input/attempt")
    return count
}
