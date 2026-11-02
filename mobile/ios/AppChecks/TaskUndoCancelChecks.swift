import Foundation
import CRMCore

actor ControlledTaskUndoCancelPort:SyntheticTaskUndoCancelPort {
    nonisolated let grants:[SyntheticTaskUndoCancelGrant]
    private var attempts:[TaskUndoCancelAttempt]=[]
    private var pending:[Int:CheckedContinuation<SyntheticTaskUndoCancelOutcome,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    init(_ grants:[SyntheticTaskUndoCancelGrant]) {self.grants=grants}
    func execute(_ attempt:TaskUndoCancelAttempt) async throws -> SyntheticTaskUndoCancelOutcome {let i=attempts.count;attempts.append(attempt);return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ outcome:SyntheticTaskUndoCancelOutcome) {pending.removeValue(forKey:i)!.resume(returning:outcome)}
    func fail(_ i:Int) {pending.removeValue(forKey:i)!.resume(throwing:CancellationError())}
    func recorded()->[TaskUndoCancelAttempt] {attempts}
}
actor TaskUndoCancelReadFixture:TaskReadRepository {
    let base:APIReadRepository;let query:APIReadRepository
    private var selected:TaskDetails
    init(directory:URL,selected:TaskDetails) {base=APIReadRepository(transport:FixtureTransport(directory:directory));query=APIReadRepository(transport:FixtureTransport(directory:directory,taskQueries:true));self.selected=selected}
    func set(_ next:TaskDetails) {selected=next}
    func tasks(business:Int) async throws -> TaskPage {if selected.business==business && selected.task.id==3167 {return try await query.tasks(business:business,filter:TaskQueryFilter(status:"cancelled"))};return try await base.tasks(business:business)}
    func taskDetails(business:Int,id:Int) async throws -> TaskDetails {if selected.business==business && selected.task.id==id {return selected};return try await base.taskDetails(business:business,id:id)}
}
struct TaskUndoCancelFixtureOrigin:TaskCommentDraftSource {
    let allowed:[TaskDetails]
    func matchesFixture(_ detail:TaskDetails) async -> Bool {allowed.contains(detail)}
}
struct TaskUndoCancelUnknownCancelFixture:SyntheticTaskCancelPort {let grants:[SyntheticTaskCancelGrant];func execute(_ attempt:TaskCancelAttempt) async throws -> SyntheticTaskCancelOutcome {.unknown}}
@MainActor func checkTaskUndoCancel(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func data(_ name:String) throws -> Data {try Data(contentsOf:directory.appendingPathComponent(name+".json"))}
    func detail(_ name:String) throws -> TaskDetails {try JSONDecoder().decode(TaskDetails.self,from:data(name))}
    func variant(_ name:String,_ status:String) throws -> TaskDetails {var o=try JSONSerialization.jsonObject(with:data(name)) as! [String:Any];var t=o["task"] as! [String:Any];t["status"]=status;o["task"]=t;return try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:o))}
    func source(_ payload:TaskDetails,epoch:Int=200,revision:Int=1)->TaskUndoCancelSource {TaskUndoCancelSource(read:TaskCommentRead(context:TaskCommentContext(business:payload.business,task:payload.task.id,epoch:epoch),revision:revision),task:payload.task)}
    let original=try detail("task-101-3167"),foreign=try variant("task-202-1201","cancelled"),context=TaskCommentContext(business:101,task:3167,epoch:200),fixture=FixtureTaskUndoCancelPort(directory:directory),initial=source(try detail("task-101-3167"))
    let auth=fixture.grants.compactMap {$0.authorization(for:context)}.first!
    for grant in [SyntheticTaskUndoCancelGrant(business:101,task:3167,actor:9001,update:false),SyntheticTaskUndoCancelGrant(business:202,task:3167,actor:9001,update:true),SyntheticTaskUndoCancelGrant(business:101,task:3167,actor:0,update:true)] {try expect(grant.authorization(for:context)==nil,"GET/foreign/false UPDATE granted undo")}
    for status in ["open","in_progress","done","waiting",""] {var l=TaskUndoCancelLedger();let next=source(try variant("task-101-3167",status));try expect(next.identityValid && !next.valid && l.begin(TaskUndoCancelReview(source:next,visit:1),authorization:auth)==nil,"Undo accepted noncancelled read or lost retained identity")}
    let cases=(try JSONSerialization.jsonObject(with:data("task-undo-cancel-outcome")) as! [String:Any])["validation_cases"] as! [[String:Any]]
    for row in cases {
        let review=TaskUndoCancelReview(source:initial,visit:1);var l=TaskUndoCancelLedger();let a=l.begin(review,authorization:auth)!;try expect(l.begin(review,authorization:auth)==nil,"Pending keyless undo duplicated")
        l.complete(a,outcome:.response(status:row["status"] as! Int,data:try JSONSerialization.data(withJSONObject:row["response"]!)));let record=l.visible(auth)!
        try expect(record.phase == (row["expected"] as! String=="confirmed" ? .confirmed:.unknown),"Undo accepted wrong scope/status/metadata: \(row["name"]!)")
        l.complete(a,outcome:.rejectedWithoutWrite);try expect(l.visible(auth)==record && record.attempt.review==review,"Late undo replaced source/outcome")
        if record.phase == .unknown {try expect(!l.acknowledge(auth),"Unknown keyless undo acknowledged")}
        if let r=record.result {let wire=row["response"] as! [String:Any];try expect(r.status==wire["status"] as! String && r.completed_at==wire["completed_at"] as? String && r.completed_by==wire["completed_by"] as? Int,"Undo predicted target or cleared completion metadata")}
    }
    let held=ControlledTaskUndoCancelPort(fixture.grants),m=TaskUndoCancelViewModel(port:held);m.bind(initial);m.prepare(expected:m.control);let old=m.control!;try expect(m.review?.source.task.status=="cancelled" && m.submission==nil,"Review optimistically restored status")
    m.back(expected:old);m.prepare(expected:m.control);await m.submit(expected:old);try expect(await held.recorded().isEmpty,"Identical undo review revived old Submit")
    let submit=m.control!,job=Task {await m.submit(expected:submit)};FileHandle.standardError.write(Data("UNDO waiting held/0\n".utf8));await held.wait(0);FileHandle.standardError.write(Data("UNDO entered held/0\n".utf8));let pending=m.control!,pendingRecord=m.submission!;await m.submit(expected:pending);m.back(expected:pending);m.acknowledge(expected:pending,record:pendingRecord)
    try expect(await held.recorded().count==1 && m.submission==pendingRecord && m.source?.task.status=="cancelled","Pending undo duplicate/Back/ack or optimistic status changed input")
    await held.fail(0);await job.value;let unknown=m.submission!;let open=try variant("task-101-3167","open"),progress=try variant("task-101-3167","in_progress"),done=try variant("task-101-3167","done")
    for payload in [open,progress,done] {m.bind(source(payload,revision:2));try expect(m.blocked && m.submission?.attempt==unknown.attempt && m.canPresent && !m.canPrepare,"Matching restored status inferred keyless undo outcome")}
    m.bind(source(done,epoch:201,revision:3));try expect(m.submission==nil && m.blocks(context:context) && m.canPresent,"New epoch exposed/erased keyless unknown")
    m.bind(nil);try expect(m.retainedAttemptCount==1 && m.blocks(context:context),"Closing erased keyless undo")
    let latePort=ControlledTaskUndoCancelPort(fixture.grants),late=TaskUndoCancelViewModel(port:latePort);late.bind(initial);late.prepare(expected:late.control);try expect(late.review != nil,"Late undo preparation denied before controlled wait");let lateJob=Task {await late.submit(expected:late.control)};FileHandle.standardError.write(Data("UNDO waiting latePort/0\n".utf8));await latePort.wait(0);FileHandle.standardError.write(Data("UNDO entered latePort/0\n".utf8));late.bind(source(foreign,epoch:202));let replacement=late.control
    var l=TaskUndoCancelLedger();let attempt=l.begin(TaskUndoCancelReview(source:initial,visit:1),authorization:auth)!;await latePort.resolve(0,try await fixture.execute(attempt));await lateJob.value;try expect(late.control==replacement && late.submission==nil && late.canPrepare,"Late undo mutated another owner")
    late.bind(initial);let confirmed=late.submission!;try expect(confirmed.phase == .confirmed && confirmed.result?.status=="open" && original.task.status=="cancelled","Undo fixture treated reopen/default target as source mutation")
    late.acknowledge(expected:late.control,record:confirmed);late.prepare(expected:late.control);try expect(late.consumed && late.review==nil,"Confirmed undo reused current read");late.bind(source(original,revision:2));try expect(late.canPrepare,"Fresh explicit review unavailable")
    let rejected=TaskUndoCancelViewModel(port:fixture);rejected.bind(source(try variant("task-101-1401","cancelled")));rejected.prepare(expected:rejected.control);await rejected.submit(expected:rejected.control);let noWrite=rejected.submission!;rejected.acknowledge(expected:rejected.control,record:noWrite);try expect(noWrite.phase == .rejected && rejected.canPrepare && rejected.review==nil,"No-write undo auto-retried or retained preview")
    // The real DEBUG source query/filter path already contains cancelled3167; no new query/count required.
    let transport=QueryRecordingTransport(directory),repo=APIReadRepository(transport:transport),plain=TaskListViewModel(repository:repo),readOnly=TaskListViewModel(repository:repo,undoCancelSubmission:fixture)
    await readOnly.load(business:101,epoch:203);await readOnly.open(id:3167);try expect(plain.undoCancelAction==nil && readOnly.undoCancelAction?.source==nil,"GET/default composition granted undo")
    let reopenPort=ControlledTaskReopenPort([SyntheticTaskReopenGrant(business:101,task:3167,actor:9001,update:true)]),list=TaskListViewModel(repository:repo,commentSource:FixtureTaskCommentDraftSource(directory:directory),reopenSubmission:reopenPort,fileMetadataPort:FixtureTaskFileMetadataPort(directory:directory),undoCancelSubmission:fixture)
    await list.load(business:101,epoch:204);await list.applyFilter(TaskQueryFilter(status:"cancelled"),expected:list.querySelection);try expect(list.items.map(\.id)==[3167] && list.total==1,"Existing cancelled query lost reachable Task3167")
    await list.open(id:3167);let undo=list.undoCancelAction!,before=list.detail!,items=list.items,reads=await transport.recorded().count
    list.prepareUndoCancel(undo.control,parent:list.control);try expect(undo.review?.source.task.status=="cancelled" && list.detail==before,"Review predicted target or changed query detail")
    await undo.submit(expected:undo.control);let record=undo.submission!,after=await transport.recorded().count
    try expect(record.phase == .confirmed && list.detail==before && list.items==items && after==reads,"Fake undo changed source/list or caused another GET")
    if let files=list.fileMetadata {await files.load(expected:files.control);try expect(undo.submission==record && list.detail==before,"Metadata failure erased undo or changed source")}
    undo.acknowledge(expected:undo.control,record:record);list.prepareReopen(list.reopenAction?.control,parent:list.control);try expect(list.reopenAction?.review==nil && list.taskActionOccupied,"Confirmed undo bypassed via reopen")
    // Unknown undo blocks all five existing peer actions across matching target reads.
    let store=TaskUndoCancelReadFixture(directory:directory,selected:original),origin=TaskUndoCancelFixtureOrigin(allowed:[original,open,progress,done,foreign]),port=ControlledTaskUndoCancelPort(fixture.grants)
    let complete=ControlledTaskCompletePort([SyntheticTaskCompleteGrant(business:101,task:3167,actor:9001,update:true)]),assign=ControlledTaskSelfAssignPort([SyntheticTaskSelfAssignGrant(business:101,task:3167,actor:9001,update:true,activeMember:true)]),start=ControlledTaskStartPort([SyntheticTaskStartGrant(business:101,task:3167,actor:9001,update:true)]),watch=ControlledTaskWatcherPort([SyntheticTaskWatcherGrant(business:101,task:3167,actor:9001,update:true,activeMember:true)])
    let flow=TaskListViewModel(repository:store,commentSource:origin,completeSubmission:complete,selfAssignSubmission:assign,startSubmission:start,reopenSubmission:reopenPort,watcherSubmission:watch,undoCancelSubmission:port)
    await flow.load(business:101,epoch:205);await flow.open(id:3167);let active=flow.undoCancelAction!;flow.prepareUndoCancel(active.control,parent:flow.control);try expect(active.review != nil,"Current undo preparation denied before controlled wait");let run=Task {await active.submit(expected:active.control)};FileHandle.standardError.write(Data("UNDO waiting port/0\n".utf8));await port.wait(0);FileHandle.standardError.write(Data("UNDO entered port/0\n".utf8));await port.resolve(0,.unknown);await run.value
    await store.set(open);await flow.retryDetail(expected:flow.detailSelection);flow.prepareCompletion(flow.completion?.control,parent:flow.control);flow.prepareSelfAssignment(flow.selfAssignment?.control,parent:flow.control);flow.prepareStart(flow.startAction?.control,parent:flow.control);flow.prepareWatcher(flow.watcherAction?.control,parent:flow.control)
    try expect(flow.completion?.canPrepare==true && flow.selfAssignment?.canPrepare==true && flow.startAction?.canPrepare==true && flow.watcherAction?.canPrepare==true && flow.completion?.review==nil && flow.selfAssignment?.review==nil && flow.startAction?.review==nil && flow.watcherAction?.review==nil && active.submission?.phase == .unknown,"Matching open read released unknown undo to peers")
    await store.set(done);await flow.retryDetail(expected:flow.detailSelection);flow.prepareReopen(flow.reopenAction?.control,parent:flow.control);try expect(flow.reopenAction?.canPrepare==true && flow.reopenAction?.review==nil && flow.taskActionOccupied,"Done reread bypassed undo via reopen")
    await flow.load(business:202,epoch:206);await flow.open(id:1201);try expect(!flow.taskActionOccupied && active.retainedAttemptCount==1,"Undo unknown blocked unrelated Task or was erased")
    // Every old action's retained result blocks newly eligible undo-cancel after a cancelled read.
    for kind in 0..<5 {
        let name=kind==3 ? "task-101-1103":"task-101-1101",initialPayload=try detail(name),cancelled=try variant(name,"cancelled"),task=initialPayload.task.id
        let mutable=TaskUndoCancelReadFixture(directory:directory,selected:initialPayload),known=TaskUndoCancelFixtureOrigin(allowed:[initialPayload,cancelled]),c=ControlledTaskCompletePort(FixtureTaskCompletePort(directory:directory).grants),a=ControlledTaskSelfAssignPort(FixtureTaskSelfAssignPort(directory:directory).grants),s=ControlledTaskStartPort(FixtureTaskStartPort(directory:directory).grants),r=ControlledTaskReopenPort(FixtureTaskReopenPort(directory:directory).grants),w=ControlledTaskWatcherPort(FixtureTaskWatcherPort(directory:directory).grants),u=ControlledTaskUndoCancelPort([SyntheticTaskUndoCancelGrant(business:101,task:task,actor:9001,update:true)])
        let owner=TaskListViewModel(repository:mutable,commentSource:known,completeSubmission:c,selfAssignSubmission:a,startSubmission:s,reopenSubmission:r,watcherSubmission:w,undoCancelSubmission:u);await owner.load(business:101,epoch:207);await owner.open(id:task);let job:Task<Void,Never>
        if kind==0 {let m=owner.completion!;owner.prepareCompletion(m.control,parent:owner.control);try expect(m.review != nil,"Old completion preparation denied before controlled wait");job=Task {await m.submit(expected:m.control)};FileHandle.standardError.write(Data("UNDO waiting c/0\n".utf8));await c.wait(0);FileHandle.standardError.write(Data("UNDO entered c/0\n".utf8));await c.resolve(0,.unknown)}
        else if kind==1 {let m=owner.selfAssignment!;owner.prepareSelfAssignment(m.control,parent:owner.control);try expect(m.review != nil,"Old self assignment preparation denied before controlled wait");job=Task {await m.submit(expected:m.control)};FileHandle.standardError.write(Data("UNDO waiting a/0\n".utf8));await a.wait(0);FileHandle.standardError.write(Data("UNDO entered a/0\n".utf8));await a.resolve(0,.unknown)}
        else if kind==2 {let m=owner.startAction!;owner.prepareStart(m.control,parent:owner.control);try expect(m.review != nil,"Old start preparation denied before controlled wait");job=Task {await m.submit(expected:m.control)};FileHandle.standardError.write(Data("UNDO waiting s/0\n".utf8));await s.wait(0);FileHandle.standardError.write(Data("UNDO entered s/0\n".utf8));await s.resolve(0,.unknown)}
        else if kind==3 {let m=owner.reopenAction!;owner.prepareReopen(m.control,parent:owner.control);try expect(m.review != nil,"Old reopen preparation denied before controlled wait");job=Task {await m.submit(expected:m.control)};FileHandle.standardError.write(Data("UNDO waiting r/0\n".utf8));await r.wait(0);FileHandle.standardError.write(Data("UNDO entered r/0\n".utf8));await r.resolve(0,.unknown)}
        else {let m=owner.watcherAction!;owner.prepareWatcher(m.control,parent:owner.control);try expect(m.review != nil,"Old watcher preparation denied before controlled wait");job=Task {await m.submit(expected:m.control)};FileHandle.standardError.write(Data("UNDO waiting w/0\n".utf8));await w.wait(0);FileHandle.standardError.write(Data("UNDO entered w/0\n".utf8));await w.resolve(0,.unknown)}
        await job.value;await mutable.set(cancelled);await owner.retryDetail(expected:owner.detailSelection);owner.prepareUndoCancel(owner.undoCancelAction?.control,parent:owner.control)
        try expect(owner.undoCancelAction?.canPrepare==true && owner.undoCancelAction?.review==nil && owner.taskActionOccupied && owner.undoCancelAction?.retainedAttemptCount==0,"Undo bypassed previous action unknown")
    }
    let originalCancelTask=try detail("task-101-1101"),cancelled=try variant("task-101-1101","cancelled"),cancelStore=TaskUndoCancelReadFixture(directory:directory,selected:try detail("task-101-1101"))
    let canceled=TaskListViewModel(repository:cancelStore,commentSource:TaskUndoCancelFixtureOrigin(allowed:[originalCancelTask,cancelled]),cancelSubmission:TaskUndoCancelUnknownCancelFixture(grants:FixtureTaskCancelPort(directory:directory).grants),undoCancelSubmission:ControlledTaskUndoCancelPort([SyntheticTaskUndoCancelGrant(business:101,task:1101,actor:9001,update:true)]))
    await canceled.load(business:101,epoch:208);await canceled.open(id:1101);let reason=canceled.cancelReason!;canceled.openCancelReason(reason.session.read!);reason.update("Manual source reason",input:reason.inputControl);reason.prepare(expected:reason.control);await reason.submit(reason.session.review!,expected:reason.control);reason.close(expected:reason.returnControl)
    await cancelStore.set(cancelled);await canceled.retryDetail(expected:canceled.detailSelection);canceled.prepareUndoCancel(canceled.undoCancelAction?.control,parent:canceled.control);try expect(canceled.undoCancelAction?.canPrepare==true && canceled.undoCancelAction?.review==nil && reason.submissionBlocked,"Matching cancellation read turned cancellation unknown into undo permission/result proof")
    return count
}
