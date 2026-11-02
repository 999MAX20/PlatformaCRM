import Foundation
import CRMCore

actor ControlledTaskWatcherPort:SyntheticTaskWatcherPort {
    nonisolated let grants:[SyntheticTaskWatcherGrant]
    private var attempts:[TaskWatcherAttempt]=[]
    private var pending:[Int:CheckedContinuation<SyntheticTaskWatcherOutcome,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    init(_ grants:[SyntheticTaskWatcherGrant]) {self.grants=grants}
    func execute(_ attempt:TaskWatcherAttempt) async throws -> SyntheticTaskWatcherOutcome {let i=attempts.count;attempts.append(attempt);return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ outcome:SyntheticTaskWatcherOutcome) {pending.removeValue(forKey:i)!.resume(returning:outcome)}
    func fail(_ i:Int) {pending.removeValue(forKey:i)!.resume(throwing:CancellationError())}
    func recorded()->[TaskWatcherAttempt] {attempts}
}
actor TaskWatcherReadFixture:TaskReadRepository {
    let base:APIReadRepository
    private var selected:TaskDetails
    init(directory:URL,selected:TaskDetails) {base=APIReadRepository(transport:FixtureTransport(directory:directory));self.selected=selected}
    func set(_ next:TaskDetails) {selected=next}
    func tasks(business:Int) async throws -> TaskPage {try await base.tasks(business:business)}
    func taskDetails(business:Int,id:Int) async throws -> TaskDetails {if selected.business==business && selected.task.id==id {return selected};return try await base.taskDetails(business:business,id:id)}
}
struct TaskWatcherFixtureOrigin:TaskCommentDraftSource {
    let allowed:[TaskDetails]
    func matchesFixture(_ detail:TaskDetails) async -> Bool {allowed.contains(detail)}
}
struct TaskWatcherUnknownCancelFixture:SyntheticTaskCancelPort {let grants:[SyntheticTaskCancelGrant];func execute(_ attempt:TaskCancelAttempt) async throws -> SyntheticTaskCancelOutcome {.unknown}}
@MainActor func checkTaskWatcher(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func data(_ name:String) throws -> Data {try Data(contentsOf:directory.appendingPathComponent(name+".json"))}
    func detail(_ name:String) throws -> TaskDetails {try JSONDecoder().decode(TaskDetails.self,from:data(name))}
    func variant(_ name:String,_ status:String) throws -> TaskDetails {var o=try JSONSerialization.jsonObject(with:data(name)) as! [String:Any];var task=o["task"] as! [String:Any];task["status"]=status;o["task"]=task;return try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:o))}
    func source(_ payload:TaskDetails,epoch:Int=190,revision:Int=1)->TaskWatcherSource {TaskWatcherSource(read:TaskCommentRead(context:TaskCommentContext(business:payload.business,task:payload.task.id,epoch:epoch),revision:revision),task:payload.task)}
    let original=try detail("task-101-1101"),foreign=try detail("task-202-1201"),fixture=FixtureTaskWatcherPort(directory:directory),context=TaskCommentContext(business:101,task:1101,epoch:190),initial=source(try detail("task-101-1101"))
    let auth=fixture.grants.compactMap {$0.authorization(for:context)}.first!
    for grant in [SyntheticTaskWatcherGrant(business:101,task:1101,actor:9001,update:false,activeMember:true),SyntheticTaskWatcherGrant(business:101,task:1101,actor:9001,update:true,activeMember:false),SyntheticTaskWatcherGrant(business:202,task:1101,actor:9001,update:true,activeMember:true),SyntheticTaskWatcherGrant(business:101,task:1101,actor:0,update:true,activeMember:true)] {try expect(grant.authorization(for:context)==nil,"GET/inactive/missing UPDATE/foreign grant permitted watcher")}
    for status in ["done","cancelled","waiting",""] {var l=TaskWatcherLedger();let next=source(try variant("task-101-1101",status));try expect(next.identityValid && !next.valid && l.begin(TaskWatcherReview(source:next,visit:1),authorization:auth)==nil,"Watcher accepted ineligible status or lost identity")}
    let progress=try variant("task-101-1101","in_progress"),done=try variant("task-101-1101","done");try expect(source(progress).valid,"Watcher rejected in_progress")
    let cases=(try JSONSerialization.jsonObject(with:data("task-watcher-outcome")) as! [String:Any])["validation_cases"] as! [[String:Any]]
    for row in cases {
        let snap=source(try variant("task-101-1101",row["source_status"] as? String ?? "open")),review=TaskWatcherReview(source:snap,visit:1);var l=TaskWatcherLedger();let a=l.begin(review,authorization:auth)!
        try expect(l.begin(review,authorization:auth)==nil,"Duplicate pending watch attempt")
        l.complete(a,outcome:.response(status:row["status"] as! Int,data:try JSONSerialization.data(withJSONObject:row["response"]!)));let result=l.visible(auth)!
        try expect(result.phase == (row["expected"] as! String=="confirmed" ? .confirmed:.unknown),"Watcher source/result mismatch: \(row["name"]!)")
        l.complete(a,outcome:.rejectedWithoutWrite);try expect(l.visible(auth)==result && result.attempt.review==review,"Late watch reply changed immutable attempt/result")
        if result.phase == .unknown {try expect(!l.acknowledge(auth),"Unknown watch cleared")}
        if let r=result.result {let text=String(decoding:try JSONEncoder().encode(r),as:UTF8.self);try expect(!text.contains("watchers_count") && !text.contains("actor") && r.status==snap.task.status,"Watcher retained count/actor echo or changed status")}
    }
    let held=ControlledTaskWatcherPort(fixture.grants),m=TaskWatcherViewModel(port:held);m.bind(initial);m.prepare(expected:m.control);let old=m.control!;m.back(expected:old);m.prepare(expected:m.control);await m.submit(expected:old);try expect(await held.recorded().isEmpty,"Identical watcher review revived stale Submit")
    let submit=m.control!,job=Task {await m.submit(expected:submit)};await held.wait(0);let pending=m.control!,pendingRecord=m.submission!;await m.submit(expected:pending);m.back(expected:pending);m.acknowledge(expected:pending,record:pendingRecord)
    try expect(await held.recorded().count==1 && m.submission==pendingRecord,"Pending watcher duplicate/Back/ack changed attempt")
    await held.fail(0);await job.value;let unknown=m.submission!;m.bind(source(progress,revision:2));try expect(m.blocked && m.submission?.attempt==unknown.attempt && !m.canPrepare,"Matching watcher read cleared/proved unknown")
    m.bind(source(done,epoch:191,revision:3));try expect(m.submission==nil && m.blocks(context:context) && m.canPresent && !m.canPrepare,"Epoch/ineligible source discarded or exposed watcher outcome")
    m.bind(nil);try expect(m.retainedAttemptCount==1 && m.blocks(context:context),"Closing watch discarded attempt")
    let latePort=ControlledTaskWatcherPort(fixture.grants),late=TaskWatcherViewModel(port:latePort);late.bind(initial);late.prepare(expected:late.control);let lateJob=Task {await late.submit(expected:late.control)};await latePort.wait(0);late.bind(source(foreign,epoch:192));let replacement=late.control
    var l=TaskWatcherLedger();let a=l.begin(TaskWatcherReview(source:initial,visit:1),authorization:auth)!;await latePort.resolve(0,try await fixture.execute(a));await lateJob.value
    try expect(late.control==replacement && late.submission==nil && late.canPrepare,"Late watcher reply mutated another owner")
    late.bind(initial);let confirmed=late.submission!;try expect(confirmed.phase == .confirmed && confirmed.result?.watchers.contains(9001)==true && confirmed.result?.status=="open","Watcher response inferred start/assignment/current count")
    late.acknowledge(expected:late.control,record:confirmed);late.prepare(expected:late.control);try expect(late.consumed && late.review==nil,"Confirmed watcher read reused")
    late.bind(source(original,revision:2));try expect(late.canPrepare,"Explicit fresh watch review unavailable")
    let rejected=TaskWatcherViewModel(port:fixture);rejected.bind(source(try detail("task-101-1401")));rejected.prepare(expected:rejected.control);await rejected.submit(expected:rejected.control);let noWrite=rejected.submission!
    rejected.acknowledge(expected:rejected.control,record:noWrite);try expect(noWrite.phase == .rejected && rejected.canPrepare && rejected.review==nil,"No-write watcher auto-replayed or retained preview")
    let transport=SearchTransport(directory),repo=APIReadRepository(transport:transport),plain=TaskListViewModel(repository:repo),readOnly=TaskListViewModel(repository:repo,watcherSubmission:fixture)
    await readOnly.load(business:101,epoch:193);await readOnly.open(id:1101);try expect(plain.watcherAction==nil && readOnly.watcherAction?.source==nil,"Default/GET-only composition granted watch/member authority")
    let list=TaskListViewModel(repository:repo,commentSource:FixtureTaskCommentDraftSource(directory:directory),cancelSubmission:FixtureTaskCancelPort(directory:directory),completeSubmission:FixtureTaskCompletePort(directory:directory),selfAssignSubmission:FixtureTaskSelfAssignPort(directory:directory),startSubmission:FixtureTaskStartPort(directory:directory),reopenSubmission:FixtureTaskReopenPort(directory:directory),fileMetadataPort:FixtureTaskFileMetadataPort(directory:directory),watcherSubmission:fixture)
    await list.load(business:101,epoch:194);await list.open(id:1101);let watch=list.watcherAction!,before=list.detail!,items=list.items,reads=await transport.recorded().count
    list.prepareWatcher(watch.control,parent:list.control);let stale=watch.control!;list.openComment(watch.source!.read);await watch.submit(expected:stale);try expect(watch.retainedAttemptCount==0,"Comment visit revived old watcher review");if let comment=list.comment {comment.close(expected:comment.returnControl)}
    list.prepareWatcher(watch.control,parent:list.control);await watch.submit(expected:watch.control);let record=watch.submission!;try expect(record.phase == .confirmed && list.detail==before && list.items==items,"Fake watcher changed GET/list/status/assignee/comments")
    let afterReads=await transport.recorded().count;try expect(afterReads==reads,"Watcher caused another GET/actual command")
    if let files=list.fileMetadata {await files.load(expected:files.control);files.select(files.items[0],expected:files.control);files.back(expected:files.control);try expect(watch.submission==record && list.detail==before,"Metadata navigation erased watch or changed Task")}
    watch.acknowledge(expected:watch.control,record:record);list.prepareCompletion(list.completion?.control,parent:list.control);list.prepareSelfAssignment(list.selfAssignment?.control,parent:list.control);list.prepareStart(list.startAction?.control,parent:list.control);list.openCancelReason(watch.source!.read)
    try expect(list.completion?.review==nil && list.selfAssignment?.review==nil && list.startAction?.review==nil && list.cancelReason?.control==nil,"Consumed watcher read bypassed by peer")
    let store=TaskWatcherReadFixture(directory:directory,selected:original),origin=TaskWatcherFixtureOrigin(allowed:[original,progress,done,foreign]),heldWatch=ControlledTaskWatcherPort(fixture.grants)
    let flow=TaskListViewModel(repository:store,commentSource:origin,completeSubmission:FixtureTaskCompletePort(directory:directory),selfAssignSubmission:FixtureTaskSelfAssignPort(directory:directory),startSubmission:FixtureTaskStartPort(directory:directory),reopenSubmission:ControlledTaskReopenPort([SyntheticTaskReopenGrant(business:101,task:1101,actor:9001,update:true)]),watcherSubmission:heldWatch)
    await flow.load(business:101,epoch:195);await flow.open(id:1101);let active=flow.watcherAction!;flow.prepareWatcher(active.control,parent:flow.control);let run=Task {await active.submit(expected:active.control)};await heldWatch.wait(0);await heldWatch.resolve(0,.unknown);await run.value
    await store.set(progress);await flow.retryDetail(expected:flow.detailSelection);flow.prepareCompletion(flow.completion?.control,parent:flow.control);flow.prepareSelfAssignment(flow.selfAssignment?.control,parent:flow.control)
    try expect(active.submission?.phase == .unknown && flow.completion?.review==nil && flow.selfAssignment?.review==nil && flow.taskActionOccupied,"Matching progress read released watch barrier")
    await store.set(original);await flow.retryDetail(expected:flow.detailSelection);flow.prepareStart(flow.startAction?.control,parent:flow.control);try expect(flow.startAction?.review==nil,"Start bypassed unknown watch")
    await store.set(done);await flow.retryDetail(expected:flow.detailSelection);flow.prepareReopen(flow.reopenAction?.control,parent:flow.control);try expect(flow.reopenAction?.canPrepare==true && flow.reopenAction?.review==nil && active.submission?.phase == .unknown,"Reopen bypassed watch after ineligible read")
    await flow.load(business:202,epoch:196);await flow.open(id:1201);try expect(!flow.taskActionOccupied && active.canPrepare && active.retainedAttemptCount==1,"Watch unknown blocked unrelated Business/Task or disappeared")
    // All four previous action ledgers must symmetrically block self-watch after a fresh eligible read.
    for kind in 0..<4 {
        let name=kind==3 ? "task-101-1103":"task-101-1101",initialPayload=try detail(name),open=try variant(name,"open"),task=initialPayload.task.id
        let mutable=TaskWatcherReadFixture(directory:directory,selected:initialPayload),known=TaskWatcherFixtureOrigin(allowed:[initialPayload,open]),complete=ControlledTaskCompletePort(FixtureTaskCompletePort(directory:directory).grants),assign=ControlledTaskSelfAssignPort(FixtureTaskSelfAssignPort(directory:directory).grants),start=ControlledTaskStartPort(FixtureTaskStartPort(directory:directory).grants),reopen=ControlledTaskReopenPort(FixtureTaskReopenPort(directory:directory).grants),port=ControlledTaskWatcherPort([SyntheticTaskWatcherGrant(business:101,task:task,actor:9001,update:true,activeMember:true)])
        let owner=TaskListViewModel(repository:mutable,commentSource:known,completeSubmission:complete,selfAssignSubmission:assign,startSubmission:start,reopenSubmission:reopen,watcherSubmission:port);await owner.load(business:101,epoch:197);await owner.open(id:task);let job:Task<Void,Never>
        if kind==0 {let m=owner.completion!;owner.prepareCompletion(m.control,parent:owner.control);job=Task {await m.submit(expected:m.control)};await complete.wait(0);await complete.resolve(0,.unknown)}
        else if kind==1 {let m=owner.selfAssignment!;owner.prepareSelfAssignment(m.control,parent:owner.control);job=Task {await m.submit(expected:m.control)};await assign.wait(0);await assign.resolve(0,.unknown)}
        else if kind==2 {let m=owner.startAction!;owner.prepareStart(m.control,parent:owner.control);job=Task {await m.submit(expected:m.control)};await start.wait(0);await start.resolve(0,.unknown)}
        else {let m=owner.reopenAction!;owner.prepareReopen(m.control,parent:owner.control);job=Task {await m.submit(expected:m.control)};await reopen.wait(0);await reopen.resolve(0,.unknown)}
        await job.value;await mutable.set(open);await owner.retryDetail(expected:owner.detailSelection);owner.prepareWatcher(owner.watcherAction?.control,parent:owner.control)
        try expect(owner.watcherAction?.canPrepare==true && owner.watcherAction?.review==nil && owner.taskActionOccupied && owner.watcherAction?.retainedAttemptCount==0,"Watch bypassed another retained action")
    }
    let cancelStore=TaskWatcherReadFixture(directory:directory,selected:original),canceled=TaskListViewModel(repository:cancelStore,commentSource:origin,cancelSubmission:TaskWatcherUnknownCancelFixture(grants:FixtureTaskCancelPort(directory:directory).grants),watcherSubmission:fixture)
    await canceled.load(business:101,epoch:198);await canceled.open(id:1101);let reason=canceled.cancelReason!;canceled.openCancelReason(reason.session.read!);reason.update("Manual source reason",input:reason.inputControl);reason.prepare(expected:reason.control);await reason.submit(reason.session.review!,expected:reason.control);reason.close(expected:reason.returnControl)
    canceled.prepareWatcher(canceled.watcherAction?.control,parent:canceled.control);try expect(canceled.watcherAction?.review==nil && reason.submissionBlocked,"Watch bypassed retained cancellation")
    return count
}
