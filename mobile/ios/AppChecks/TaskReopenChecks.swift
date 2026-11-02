import Foundation
import CRMCore

actor ControlledTaskReopenPort:SyntheticTaskReopenPort {
    nonisolated let grants:[SyntheticTaskReopenGrant]
    private var attempts:[TaskReopenAttempt]=[]
    private var pending:[Int:CheckedContinuation<SyntheticTaskReopenOutcome,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    init(_ grants:[SyntheticTaskReopenGrant]) {self.grants=grants}
    func execute(_ attempt:TaskReopenAttempt) async throws -> SyntheticTaskReopenOutcome {let i=attempts.count;attempts.append(attempt);return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ outcome:SyntheticTaskReopenOutcome) {pending.removeValue(forKey:i)!.resume(returning:outcome)}
    func fail(_ i:Int) {pending.removeValue(forKey:i)!.resume(throwing:CancellationError())}
    func recorded()->[TaskReopenAttempt] {attempts}
}
actor TaskReopenReadFixture:TaskReadRepository {
    let base:APIReadRepository
    private var selected:TaskDetails
    init(directory:URL,selected:TaskDetails) {base=APIReadRepository(transport:FixtureTransport(directory:directory));self.selected=selected}
    func set(_ next:TaskDetails) {selected=next}
    func tasks(business:Int) async throws -> TaskPage {try await base.tasks(business:business)}
    func taskDetails(business:Int,id:Int) async throws -> TaskDetails {if selected.business==business && selected.task.id==id {return selected};return try await base.taskDetails(business:business,id:id)}
}
struct TaskReopenFixtureOrigin:TaskCommentDraftSource {
    let allowed:[TaskDetails]
    func matchesFixture(_ detail:TaskDetails) async -> Bool {allowed.contains(detail)}
}
struct TaskReopenUnknownCancelFixture:SyntheticTaskCancelPort {let grants:[SyntheticTaskCancelGrant];func execute(_ attempt:TaskCancelAttempt) async throws -> SyntheticTaskCancelOutcome {.unknown}}
@MainActor func checkTaskReopen(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func data(_ name:String) throws -> Data {try Data(contentsOf:directory.appendingPathComponent(name+".json"))}
    func detail(_ name:String) throws -> TaskDetails {try JSONDecoder().decode(TaskDetails.self,from:data(name))}
    func variant(_ payload:TaskDetails,status:String) throws -> TaskDetails {var o=try JSONSerialization.jsonObject(with:data(payload.task.id==1103 ? "task-101-1103":"task-101-1101")) as! [String:Any];var t=o["task"] as! [String:Any];t["status"]=status;o["task"]=t;return try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:o))}
    func source(_ payload:TaskDetails,epoch:Int=170,revision:Int=1)->TaskReopenSource {TaskReopenSource(read:TaskCommentRead(context:TaskCommentContext(business:payload.business,task:payload.task.id,epoch:epoch),revision:revision),task:payload.task,assignee:payload.details.assignee)}
    let original=try detail("task-101-1103"),foreign=try detail("task-202-1201"),fixture=FixtureTaskReopenPort(directory:directory),context=TaskCommentContext(business:101,task:1103,epoch:170)
    let initial=source(original),auth=fixture.grants.compactMap {$0.authorization(for:context)}.first!
    try expect(initial.valid && SyntheticTaskReopenGrant(business:101,task:1103,actor:9001,update:false).authorization(for:context)==nil,"GET/false UPDATE granted reopen")
    for status in ["open","in_progress","waiting",""] {var ledger=TaskReopenLedger();let next=source(try variant(original,status:status));try expect(next.identityValid && !next.valid && ledger.begin(TaskReopenReview(source:next,visit:1),authorization:auth)==nil,"Reopen accepted source status or discarded retained identity")}
    let cancelled=try variant(original,status:"cancelled");try expect(source(cancelled).valid,"Reopen rejected source cancelled")
    let cases=(try JSONSerialization.jsonObject(with:data("task-reopen-outcome")) as! [String:Any])["validation_cases"] as! [[String:Any]]
    for row in cases {
        var o=try JSONSerialization.jsonObject(with:data("task-101-1103")) as! [String:Any],fields=o["details"] as! [String:Any]
        if let value=row["source_assignee"] {fields["assignee"]=value};if row["omit_source_assignee"] as? Bool==true {fields.removeValue(forKey:"assignee")};o["details"]=fields
        let payload=try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:o)),snapshot=source(payload),review=TaskReopenReview(source:snapshot,visit:1)
        var ledger=TaskReopenLedger();let attempt=ledger.begin(review,authorization:auth)!
        try expect(ledger.begin(review,authorization:auth)==nil,"Duplicate reopen attempt")
        ledger.complete(attempt,outcome:.response(status:row["status"] as! Int,data:try JSONSerialization.data(withJSONObject:row["response"]!)))
        let record=ledger.visible(auth)!;try expect(record.phase == (row["expected"] as! String=="confirmed" ? .confirmed:.unknown),"Reopen accepted wrong metadata/status/scope/shape: \(row["name"]!)")
        ledger.complete(attempt,outcome:.rejectedWithoutWrite);try expect(ledger.visible(auth)==record && record.attempt.review==review,"Late reply changed reopen outcome/snapshot")
        if record.phase == .unknown {try expect(!ledger.acknowledge(auth),"Unknown reopen cleared")}
    }
    let held=ControlledTaskReopenPort(fixture.grants),model=TaskReopenViewModel(port:held);model.bind(initial);model.prepare(expected:model.control);let stale=model.control!;model.back(expected:stale);model.prepare(expected:model.control)
    await model.submit(expected:stale);try expect(await held.recorded().isEmpty,"Identical review revived stale reopen Submit")
    let submit=model.control!,job=Task {await model.submit(expected:submit)};await held.wait(0);let pending=model.control!,record=model.submission!
    await model.submit(expected:pending);model.back(expected:pending);model.acknowledge(expected:pending,record:record);try expect(await held.recorded().count==1 && model.submission==record,"Pending duplicate/Back/ack changed reopen attempt")
    await held.fail(0);await job.value;let unknown=model.submission!
    let open=try variant(original,status:"open");model.bind(source(open,revision:2));try expect(model.source?.valid==false && model.canPresent && model.submission?.attempt==unknown.attempt && model.blocked,"Matching open reread cleared/proved reopen")
    model.bind(source(open,epoch:171,revision:3));try expect(model.submission==nil && model.blocks(context:context) && model.canPresent && !model.canPrepare,"Owner epoch exposed or cleared reopen result")
    model.bind(nil);try expect(model.retainedAttemptCount==1 && model.blocks(context:context),"Closing detail discarded unknown reopen")
    let latePort=ControlledTaskReopenPort(fixture.grants),late=TaskReopenViewModel(port:latePort);late.bind(initial);late.prepare(expected:late.control);let lateJob=Task {await late.submit(expected:late.control)};await latePort.wait(0);late.bind(source(foreign,epoch:172));let replacement=late.control
    var ledger=TaskReopenLedger();let attempt=ledger.begin(TaskReopenReview(source:initial,visit:1),authorization:auth)!;let outcome=try await fixture.execute(attempt)
    await latePort.resolve(0,outcome);await lateJob.value;try expect(late.control==replacement && late.submission==nil && late.retainedAttemptCount==1,"Late reopen callback mutated foreign owner")
    late.bind(initial);let confirmed=late.submission!;try expect(confirmed.phase == .confirmed,"Fixture reopen not confirmed")
    late.acknowledge(expected:late.control,record:confirmed);late.prepare(expected:late.control);try expect(late.consumed && late.review==nil && original.task.status=="done","Ack reused consumed read or changed GET status")
    late.bind(source(original,revision:2));try expect(late.canPrepare,"Fresh explicit read could not review after confirmed ack")
    let noWritePort=ControlledTaskReopenPort(fixture.grants),noWrite=TaskReopenViewModel(port:noWritePort);noWrite.bind(initial);noWrite.prepare(expected:noWrite.control);let rejectedJob=Task {await noWrite.submit(expected:noWrite.control)};await noWritePort.wait(0);await noWritePort.resolve(0,.rejectedWithoutWrite);await rejectedJob.value
    let rejected=noWrite.submission!;noWrite.acknowledge(expected:noWrite.control,record:rejected);try expect(rejected.phase == .rejected && noWrite.canPrepare && noWrite.review==nil,"No-write reopen auto-retried or kept old preview")
    let transport=SearchTransport(directory),repo=APIReadRepository(transport:transport),readOnly=TaskListViewModel(repository:repo,reopenSubmission:fixture),plain=TaskListViewModel(repository:repo)
    await readOnly.load(business:101,epoch:173);await readOnly.open(id:1103);try expect(readOnly.reopenAction?.source==nil && plain.reopenAction==nil,"GET/default composition authorized reopen")
    let list=TaskListViewModel(repository:repo,commentSource:FixtureTaskCommentDraftSource(directory:directory),reopenSubmission:fixture)
    await list.load(business:101,epoch:174);await list.open(id:1103);let action=list.reopenAction!,before=list.detail!,items=list.items,reads=await transport.recorded().count
    list.prepareReopen(action.control,parent:list.control);await action.submit(expected:action.control)
    let afterReads=await transport.recorded().count
    try expect(action.submission?.phase == .confirmed && list.detail==before && list.items==items && afterReads==reads,"Fake reopen changed GET/list/status/metadata or caused read")
    action.acknowledge(expected:action.control,record:action.submission!);try expect(list.taskActionOccupied,"Confirmed read not consumed in parent")
    // Retained reopen blocks the other lifecycle actions even when matching open read makes them eligible.
    let origin=TaskReopenFixtureOrigin(allowed:[original,open,cancelled,foreign]),mutable=TaskReopenReadFixture(directory:directory,selected:original),flowPort=ControlledTaskReopenPort(fixture.grants)
    let peers:[SyntheticTaskStartGrant]=[SyntheticTaskStartGrant(business:101,task:1103,actor:9001,update:true)]
    let flow=TaskListViewModel(repository:mutable,commentSource:origin,completeSubmission:FixtureTaskCompletePort(directory:directory),selfAssignSubmission:FixtureTaskSelfAssignPort(directory:directory),startSubmission:ControlledTaskStartPort(peers),reopenSubmission:flowPort)
    await flow.load(business:101,epoch:175);await flow.open(id:1103);let retained=flow.reopenAction!;flow.prepareReopen(retained.control,parent:flow.control);let run=Task {await retained.submit(expected:retained.control)};await flowPort.wait(0);await flowPort.resolve(0,.unknown);await run.value
    await mutable.set(open);await flow.retryDetail(expected:flow.detailSelection);flow.prepareStart(flow.startAction?.control,parent:flow.control);flow.prepareCompletion(flow.completion?.control,parent:flow.control);flow.prepareSelfAssignment(flow.selfAssignment?.control,parent:flow.control);flow.openCancelReason(retained.source!.read)
    try expect(retained.submission?.phase == .unknown && flow.taskActionOccupied && flow.startAction?.review==nil && flow.completion?.review==nil && flow.selfAssignment?.review==nil && flow.cancelReason?.control==nil,"Matching open read bypassed retained reopen")
    await flow.load(business:202,epoch:176);await flow.open(id:1201);try expect(!flow.taskActionOccupied && retained.retainedAttemptCount==1,"Reopen attempt blocked unrelated Business/Task or was lost")
    // Conversely existing open-action unknown attempts must block newly eligible reopen.
    let old=try detail("task-101-1101"),done=try variant(old,status:"done"),oldContext=TaskCommentContext(business:101,task:1101,epoch:177)
    for kind in 0..<3 {
        let store=TaskReopenReadFixture(directory:directory,selected:old),known=TaskReopenFixtureOrigin(allowed:[old,done]),c=ControlledTaskCompletePort(FixtureTaskCompletePort(directory:directory).grants),a=ControlledTaskSelfAssignPort(FixtureTaskSelfAssignPort(directory:directory).grants),s=ControlledTaskStartPort(FixtureTaskStartPort(directory:directory).grants),r=ControlledTaskReopenPort([SyntheticTaskReopenGrant(business:101,task:1101,actor:9001,update:true)])
        let owner=TaskListViewModel(repository:store,commentSource:known,completeSubmission:c,selfAssignSubmission:a,startSubmission:s,reopenSubmission:r);await owner.load(business:101,epoch:oldContext.epoch);await owner.open(id:1101)
        let pending:Task<Void,Never>
        if kind==0 {let m=owner.completion!;owner.prepareCompletion(m.control,parent:owner.control);pending=Task {await m.submit(expected:m.control)};await c.wait(0);await c.resolve(0,.unknown)}
        else if kind==1 {let m=owner.selfAssignment!;owner.prepareSelfAssignment(m.control,parent:owner.control);pending=Task {await m.submit(expected:m.control)};await a.wait(0);await a.resolve(0,.unknown)}
        else {let m=owner.startAction!;owner.prepareStart(m.control,parent:owner.control);pending=Task {await m.submit(expected:m.control)};await s.wait(0);await s.resolve(0,.unknown)}
        await pending.value;await store.set(done);await owner.retryDetail(expected:owner.detailSelection);owner.prepareReopen(owner.reopenAction?.control,parent:owner.control)
        try expect(owner.reopenAction?.canPrepare==true && owner.reopenAction?.review==nil && owner.taskActionOccupied && owner.hasHiddenRetainedAction==((kind==0)||(kind==1)),"Reopen bypassed old retained lifecycle action")
    }
    return count
}
