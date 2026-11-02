import Foundation
import CRMCore

actor ControlledTaskSelfAssignPort:SyntheticTaskSelfAssignPort {
    nonisolated let grants:[SyntheticTaskSelfAssignGrant]
    private var attempts:[TaskSelfAssignmentAttempt]=[]
    private var pending:[Int:CheckedContinuation<SyntheticTaskSelfAssignOutcome,any Error>]=[:]
    private var waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    init(_ grants:[SyntheticTaskSelfAssignGrant]) {self.grants=grants}
    func execute(_ attempt:TaskSelfAssignmentAttempt) async throws -> SyntheticTaskSelfAssignOutcome {let index=attempts.count;attempts.append(attempt);return try await withCheckedThrowingContinuation {pending[index]=$0;waiters.removeValue(forKey:index)?.resume()}}
    func wait(_ index:Int) async {if pending[index]==nil {await withCheckedContinuation {waiters[index]=$0}}}
    func resolve(_ index:Int,_ outcome:SyntheticTaskSelfAssignOutcome) {pending.removeValue(forKey:index)!.resume(returning:outcome)}
    func fail(_ index:Int) {pending.removeValue(forKey:index)!.resume(throwing:CancellationError())}
    func recorded()->[TaskSelfAssignmentAttempt] {attempts}
}
@MainActor func checkTaskSelfAssignment(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func detail(_ b:Int,_ id:Int) throws -> TaskDetails {try JSONDecoder().decode(TaskDetails.self,from:Data(contentsOf:directory.appendingPathComponent("task-\(b)-\(id).json")))}
    let a=try detail(101,1101),b=try detail(202,1201),context=TaskCommentContext(business:101,task:1101,epoch:130),source=TaskSelfAssignmentSource(read:TaskCommentRead(context:context,revision:1),task:a.task),fixture=FixtureTaskSelfAssignPort(directory:directory),auth=fixture.grants.compactMap {$0.authorization(for:context)}.first!
    try expect(source.valid && SyntheticTaskSelfAssignGrant(business:101,task:1101,actor:9001,update:false,activeMember:true).authorization(for:context)==nil,"GET or false UPDATE yielded completion authority")
    try expect(SyntheticTaskSelfAssignGrant(business:101,task:1101,actor:9001,update:true,activeMember:false).authorization(for:context)==nil,"Inactive member was inferred from GET or completion grant")
    for status in ["done","cancelled","waiting","unknown",""] {let task=WorkTask(id:1101,title:a.task.title,status:status,priority:a.task.priority,due_at:a.task.due_at);try expect(!TaskSelfAssignmentSource(read:source.read,task:task).valid,"Completion accepted unknown/terminal source status")}
    let foreignTask=WorkTask(id:1101,title:a.task.title,status:"open",priority:a.task.priority,due_at:a.task.due_at,business:202)
    try expect(!TaskSelfAssignmentSource(read:source.read,task:foreignTask).valid,"Explicit foreign Task Business accepted for completion review")
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-self-assign-outcome.json"))) as! [String:Any],cases=catalog["validation_cases"] as! [[String:Any]]
    for row in cases {
        var ledger=TaskSelfAssignmentLedger();let review=TaskSelfAssignmentReview(source:source,visit:1),attempt=ledger.begin(review,authorization:auth)!
        try expect(ledger.begin(review,authorization:auth)==nil && ledger.blocked(context),"Pending completion duplicate was admitted")
        ledger.complete(attempt,outcome:.response(status:row["status"] as! Int,data:try JSONSerialization.data(withJSONObject:row["response"]!)))
        let record=ledger.visible(auth)!;try expect(record.phase == (row["expected"] as! String == "confirmed" ? .confirmed:.unknown),"Completion result accepted malformed/foreign/missing field: \(row["name"]!)")
        ledger.complete(attempt,outcome:.rejectedWithoutWrite);try expect(ledger.visible(auth)==record,"Duplicate late result replaced retained completion outcome")
        if record.phase == .unknown {try expect(!ledger.acknowledge(auth) && ledger.blocked(context),"Unknown completion was cleared")}
    }
    var unknown=TaskSelfAssignmentLedger();let review=TaskSelfAssignmentReview(source:source,visit:1),attempt=unknown.begin(review,authorization:auth)!;unknown.complete(attempt,outcome:.unknown)
    let reread=TaskSelfAssignmentSource(read:TaskCommentRead(context:context,revision:2),task:a.task),newEpoch=TaskCommentContext(business:101,task:1101,epoch:131),newAuth=fixture.grants.compactMap {$0.authorization(for:newEpoch)}.first!
    try expect(unknown.begin(TaskSelfAssignmentReview(source:reread,visit:2),authorization:auth)==nil && unknown.blocked(newEpoch) && unknown.visible(newAuth)==nil && !unknown.acknowledge(newAuth),"Reread/new epoch proved or exposed unknown completion")
    let port=ControlledTaskSelfAssignPort(fixture.grants),model=TaskSelfAssignmentViewModel(port:port)
    model.bind(source);let entry=model.control!;model.prepare(expected:entry);let oldReview=model.control!;model.back(expected:oldReview);model.prepare(expected:model.control)
    await model.submit(expected:oldReview);try expect(await port.recorded().isEmpty,"Identical review revived old Submit")
    let submitting=model.control!,sending=Task {await model.submit(expected:submitting)};await port.wait(0);let pending=model.control!,pendingRecord=model.submission!
    await model.submit(expected:submitting);model.back(expected:pending);model.acknowledge(expected:pending,record:pendingRecord)
    try expect(await port.recorded().count==1 && model.blocked && model.submission==pendingRecord,"Pending completion duplicate/Back/ack altered attempt")
    let foreign=TaskSelfAssignmentSource(read:TaskCommentRead(context:TaskCommentContext(business:202,task:1201,epoch:132),revision:1),task:b.task);model.bind(foreign);let foreignControl=model.control
    await port.resolve(0,try await fixture.execute(attempt));await sending.value
    try expect(model.control==foreignControl && model.submission==nil && model.canPrepare && model.retainedAttemptCount==1,"Late completion changed another owner/control")
    model.bind(source);let terminal=model.submission!;try expect(terminal.phase == .confirmed,"Matching explicit fixture complete result was not retained")
    model.acknowledge(expected:model.control,record:terminal);model.prepare(expected:model.control);try expect(model.consumed && !model.canPrepare && model.review==nil && source.task.status=="open","Acknowledged completion repeated same read or changed source Task")
    model.bind(reread);try expect(model.canPrepare,"A fresh explicit source read was conflated with an old UI visit")
    let canceled=TaskSelfAssignmentViewModel(port:port);canceled.bind(source);canceled.prepare(expected:canceled.control);let failure=Task {await canceled.submit(expected:canceled.control)};await port.wait(1);await port.fail(1);await failure.value
    let retained=canceled.submission!;try expect(retained.phase == .unknown && retained.attempt.review.source==source,"Thrown/cancelled attempt lost immutable review")
    canceled.bind(nil);canceled.bind(reread);canceled.acknowledge(expected:canceled.control,record:retained);try expect(canceled.blocked && canceled.submission==retained && !canceled.canPrepare,"Unknown completion reset by close/reopen/read")
    let rejected=TaskSelfAssignmentViewModel(port:fixture);rejected.bind(foreign);rejected.prepare(expected:rejected.control);await rejected.submit(expected:rejected.control);let rejection=rejected.submission!
    try expect(rejection.phase == .rejected,"Explicit rejected-without-write fixture was classified unknown")
    rejected.acknowledge(expected:rejected.control,record:rejection);try expect(rejected.canPrepare && rejected.review==nil,"Rejected result silently replayed or failed to require a fresh review")
    // Integrated Task read -> preview -> sibling -> explicit fake result, never mutate source/list.
    let transport=SearchTransport(directory),repository=APIReadRepository(transport:transport),tasks=TaskListViewModel(repository:repository,commentSource:FixtureTaskCommentDraftSource(directory:directory),completeSubmission:FixtureTaskCompletePort(directory:directory),selfAssignSubmission:fixture)
    await tasks.load(business:101,epoch:133);await tasks.open(id:1101);let complete=tasks.selfAssignment!,original=tasks.detail!,statuses=tasks.items.map(\.status),ids=tasks.items.map(\.id),readCount=await transport.recorded().count
    try expect(complete.canPrepare && complete.source?.task==original.task,"Explicit fake completion failed to bind verified read")
    complete.prepare(expected:complete.control);let siblingReview=complete.control!;tasks.openComment(complete.source!.read)
    await complete.submit(expected:siblingReview);try expect(complete.retainedAttemptCount==0 && complete.review==nil,"Sibling visit failed to revoke old completion preview")
    if let c=tasks.comment {c.close(expected:c.returnControl)}
    complete.prepare(expected:complete.control);await complete.submit(expected:complete.control)
    try expect(complete.submission?.phase == .confirmed && tasks.detail==original && tasks.items.map(\.status)==statuses && tasks.items.map(\.id)==ids,"Fake completion changed GET task/list/status")
    try expect(await transport.recorded().count==readCount,"Fake completion started a GET or real mutation")
    let peer=tasks.completion!;tasks.prepareCompletion(peer.control,parent:tasks.control)
    try expect(peer.review==nil && !tasks.completionCurrent(tasks.control),"Pending result failed to block completion peer")
    if let record=complete.submission {complete.acknowledge(expected:complete.control,record:record)}
    tasks.prepareCompletion(peer.control,parent:tasks.control)
    try expect(peer.review==nil && !tasks.completionCurrent(tasks.control),"Consumed self-assignment read allowed stale completion")
    tasks.back();try expect(complete.source==nil && complete.retainedAttemptCount==1,"Task return lost attempt or exposed source outside parent")
    let readOnly=TaskListViewModel(repository:repository,selfAssignSubmission:fixture);await readOnly.load(business:101,epoch:134);await readOnly.open(id:1101)
    try expect(readOnly.selfAssignment?.source==nil,"GET without independent fixture provenance bound completion authority")
    for assigning in [false,true] {
        let readTransport=SearchTransport(directory),repo=APIReadRepository(transport:readTransport),assignPort=ControlledTaskSelfAssignPort(fixture.grants),completePort=ControlledTaskCompletePort(FixtureTaskCompletePort(directory:directory).grants)
        let list=TaskListViewModel(repository:repo,commentSource:FixtureTaskCommentDraftSource(directory:directory),completeSubmission:completePort,selfAssignSubmission:assignPort)
        await list.load(business:101,epoch:140);await list.open(id:1101)
        let assign=list.selfAssignment!,complete=list.completion!,read=assign.source!.read,parent=list.control!
        let actual=assign.source!
        assign.bind(TaskSelfAssignmentSource(read:TaskCommentRead(context:TaskCommentContext(business:101,task:1101,epoch:999),revision:read.revision),task:actual.task))
        try expect(!list.selfAssignmentCurrent(parent),"Current parent accepted foreign epoch source binding")
        assign.bind(actual)
        // A peer preview also consumes the old entry/control after explicit Back.
        let beforeAssign=assign.control!,beforeComplete=complete.control!
        list.prepareSelfAssignment(beforeAssign,parent:parent);list.prepareCompletion(beforeComplete,parent:parent)
        try expect(complete.review==nil && assign.review != nil,"Concurrent peer preview was admitted")
        assign.back(expected:assign.control);list.prepareCompletion(complete.control,parent:parent)
        await assign.submit(expected:beforeAssign);try expect(await assignPort.recorded().isEmpty,"Old peer preview survived completion entry")
        complete.back(expected:complete.control)
        let sending:Task<Void,Never>
        if assigning {list.prepareSelfAssignment(assign.control,parent:parent);sending=Task {await assign.submit(expected:assign.control)};await assignPort.wait(0)}
        else {list.prepareCompletion(complete.control,parent:parent);sending=Task {await complete.submit(expected:complete.control)};await completePort.wait(0)}
        list.prepareSelfAssignment(assign.control,parent:parent);list.prepareCompletion(complete.control,parent:parent);list.openCancelReason(read)
        try expect(list.cancelReason?.control==nil && (assigning ? complete.review==nil:assign.review==nil),"Pending peer/cancellation bypassed current attempt")
        if assigning {await assignPort.resolve(0,.unknown)} else {await completePort.resolve(0,.unknown)}
        await sending.value;list.back();await list.load(business:101,epoch:141);await list.open(id:1101)
        try expect(list.taskActionOccupied && !(assigning ? list.completionCurrent(list.control):list.selfAssignmentCurrent(list.control)),"Unknown attempt was bypassed through new epoch/peer action")
        try expect((assigning ? assign.retainedAttemptCount:complete.retainedAttemptCount)==1,"Peer navigation lost immutable unknown attempt")
    }
    for unknownCancel in [false,true] {
        let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),id=unknownCancel ? 1102:1101
        let list=TaskListViewModel(repository:repo,commentSource:FixtureTaskCommentDraftSource(directory:directory),cancelSubmission:FixtureTaskCancelPort(directory:directory),completeSubmission:FixtureTaskCompletePort(directory:directory),selfAssignSubmission:fixture)
        await list.load(business:101,epoch:150);await list.open(id:id);let reason=list.cancelReason!,read=reason.session.read!
        list.openCancelReason(read);reason.update("Manual source reason",input:reason.inputControl);reason.prepare(expected:reason.control);await reason.submit(reason.session.review!,expected:reason.control)
        let result=reason.submission!;reason.close(expected:reason.returnControl)
        list.prepareCompletion(list.completion?.control,parent:list.control);list.prepareSelfAssignment(list.selfAssignment?.control,parent:list.control)
        try expect(list.completion?.review==nil && list.selfAssignment?.review==nil,"Retained cancellation outcome was bypassed through a new action")
        list.openCancelReason(read);reason.acknowledge(expected:reason.control,record:result)
        try expect(unknownCancel ? reason.submissionBlocked:reason.currentReadConfirmed,"Cancellation acknowledgement erased required unknown/confirmed-read barrier")
        await list.retryDetail(expected:list.detailSelection)
        try expect(unknownCancel ? !list.selfAssignmentCurrent(list.control):list.selfAssignmentCurrent(list.control),"Cancellation reread was treated as proof or fresh known read stayed consumed")
    }
    return count
}
