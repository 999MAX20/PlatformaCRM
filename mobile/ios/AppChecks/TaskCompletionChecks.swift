import Foundation
import CRMCore

actor ControlledTaskCompletePort:SyntheticTaskCompletePort {
    nonisolated let grants:[SyntheticTaskCompleteGrant]
    private var attempts:[TaskCompletionAttempt]=[]
    private var pending:[Int:CheckedContinuation<SyntheticTaskCompleteOutcome,any Error>]=[:]
    private var waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    init(_ grants:[SyntheticTaskCompleteGrant]) {self.grants=grants}
    func execute(_ attempt:TaskCompletionAttempt) async throws -> SyntheticTaskCompleteOutcome {let index=attempts.count;attempts.append(attempt);return try await withCheckedThrowingContinuation {pending[index]=$0;waiters.removeValue(forKey:index)?.resume()}}
    func wait(_ index:Int) async {if pending[index]==nil {await withCheckedContinuation {waiters[index]=$0}}}
    func resolve(_ index:Int,_ outcome:SyntheticTaskCompleteOutcome) {pending.removeValue(forKey:index)!.resume(returning:outcome)}
    func fail(_ index:Int) {pending.removeValue(forKey:index)!.resume(throwing:CancellationError())}
    func recorded()->[TaskCompletionAttempt] {attempts}
}
@MainActor func checkTaskCompletion(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func detail(_ b:Int,_ id:Int) throws -> TaskDetails {try JSONDecoder().decode(TaskDetails.self,from:Data(contentsOf:directory.appendingPathComponent("task-\(b)-\(id).json")))}
    let a=try detail(101,1101),b=try detail(202,1201),context=TaskCommentContext(business:101,task:1101,epoch:130),source=TaskCompletionSource(read:TaskCommentRead(context:context,revision:1),task:a.task),fixture=FixtureTaskCompletePort(directory:directory),auth=fixture.grants.compactMap {$0.authorization(for:context)}.first!
    try expect(source.valid && SyntheticTaskCompleteGrant(business:101,task:1101,actor:9001,update:false).authorization(for:context)==nil,"GET or false UPDATE yielded completion authority")
    for status in ["done","cancelled","waiting","unknown",""] {let task=WorkTask(id:1101,title:a.task.title,status:status,priority:a.task.priority,due_at:a.task.due_at);try expect(!TaskCompletionSource(read:source.read,task:task).valid,"Completion accepted unknown/terminal source status")}
    let foreignTask=WorkTask(id:1101,title:a.task.title,status:"open",priority:a.task.priority,due_at:a.task.due_at,business:202)
    try expect(!TaskCompletionSource(read:source.read,task:foreignTask).valid,"Explicit foreign Task Business accepted for completion review")
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-complete-outcome.json"))) as! [String:Any],cases=catalog["validation_cases"] as! [[String:Any]]
    for row in cases {
        var ledger=TaskCompletionLedger();let review=TaskCompletionReview(source:source,visit:1),attempt=ledger.begin(review,authorization:auth)!
        try expect(ledger.begin(review,authorization:auth)==nil && ledger.blocked(context),"Pending completion duplicate was admitted")
        ledger.complete(attempt,outcome:.response(status:row["status"] as! Int,data:try JSONSerialization.data(withJSONObject:row["response"]!)))
        let record=ledger.visible(auth)!;try expect(record.phase == (row["expected"] as! String == "confirmed" ? .confirmed:.unknown),"Completion result accepted malformed/foreign/missing field: \(row["name"]!)")
        ledger.complete(attempt,outcome:.rejectedWithoutWrite);try expect(ledger.visible(auth)==record,"Duplicate late result replaced retained completion outcome")
        if record.phase == .unknown {try expect(!ledger.acknowledge(auth) && ledger.blocked(context),"Unknown completion was cleared")}
    }
    var unknown=TaskCompletionLedger();let review=TaskCompletionReview(source:source,visit:1),attempt=unknown.begin(review,authorization:auth)!;unknown.complete(attempt,outcome:.unknown)
    let reread=TaskCompletionSource(read:TaskCommentRead(context:context,revision:2),task:a.task),newEpoch=TaskCommentContext(business:101,task:1101,epoch:131),newAuth=fixture.grants.compactMap {$0.authorization(for:newEpoch)}.first!
    try expect(unknown.begin(TaskCompletionReview(source:reread,visit:2),authorization:auth)==nil && unknown.blocked(newEpoch) && unknown.visible(newAuth)==nil && !unknown.acknowledge(newAuth),"Reread/new epoch proved or exposed unknown completion")
    let port=ControlledTaskCompletePort(fixture.grants),model=TaskCompletionViewModel(port:port)
    model.bind(source);let entry=model.control!;model.prepare(expected:entry);let oldReview=model.control!;model.back(expected:oldReview);model.prepare(expected:model.control)
    await model.submit(expected:oldReview);try expect(await port.recorded().isEmpty,"Identical review revived old Submit")
    let submitting=model.control!,sending=Task {await model.submit(expected:submitting)};await port.wait(0);let pending=model.control!,pendingRecord=model.submission!
    await model.submit(expected:submitting);model.back(expected:pending);model.acknowledge(expected:pending,record:pendingRecord)
    try expect(await port.recorded().count==1 && model.blocked && model.submission==pendingRecord,"Pending completion duplicate/Back/ack altered attempt")
    let foreign=TaskCompletionSource(read:TaskCommentRead(context:TaskCommentContext(business:202,task:1201,epoch:132),revision:1),task:b.task);model.bind(foreign);let foreignControl=model.control
    await port.resolve(0,try await fixture.execute(attempt));await sending.value
    try expect(model.control==foreignControl && model.submission==nil && model.canPrepare && model.retainedAttemptCount==1,"Late completion changed another owner/control")
    model.bind(source);let terminal=model.submission!;try expect(terminal.phase == .confirmed,"Matching explicit fixture complete result was not retained")
    model.acknowledge(expected:model.control,record:terminal);model.prepare(expected:model.control);try expect(model.consumed && !model.canPrepare && model.review==nil && source.task.status=="open","Acknowledged completion repeated same read or changed source Task")
    model.bind(reread);try expect(model.canPrepare,"A fresh explicit source read was conflated with an old UI visit")
    let canceled=TaskCompletionViewModel(port:port);canceled.bind(source);canceled.prepare(expected:canceled.control);let failure=Task {await canceled.submit(expected:canceled.control)};await port.wait(1);await port.fail(1);await failure.value
    let retained=canceled.submission!;try expect(retained.phase == .unknown && retained.attempt.review.source==source,"Thrown/cancelled attempt lost immutable review")
    canceled.bind(nil);canceled.bind(reread);canceled.acknowledge(expected:canceled.control,record:retained);try expect(canceled.blocked && canceled.submission==retained && !canceled.canPrepare,"Unknown completion reset by close/reopen/read")
    let rejected=TaskCompletionViewModel(port:fixture);rejected.bind(foreign);rejected.prepare(expected:rejected.control);await rejected.submit(expected:rejected.control);let rejection=rejected.submission!
    try expect(rejection.phase == .rejected,"Explicit rejected-without-write fixture was classified unknown")
    rejected.acknowledge(expected:rejected.control,record:rejection);try expect(rejected.canPrepare && rejected.review==nil,"Rejected result silently replayed or failed to require a fresh review")
    // Integrated Task read -> preview -> sibling -> explicit fake result, never mutate source/list.
    let transport=SearchTransport(directory),repository=APIReadRepository(transport:transport),tasks=TaskListViewModel(repository:repository,commentSource:FixtureTaskCommentDraftSource(directory:directory),completeSubmission:fixture)
    await tasks.load(business:101,epoch:133);await tasks.open(id:1101);let complete=tasks.completion!,original=tasks.detail!,statuses=tasks.items.map(\.status),ids=tasks.items.map(\.id),readCount=await transport.recorded().count
    try expect(complete.canPrepare && complete.source?.task==original.task,"Explicit fake completion failed to bind verified read")
    complete.prepare(expected:complete.control);let siblingReview=complete.control!;tasks.openComment(complete.source!.read)
    await complete.submit(expected:siblingReview);try expect(complete.retainedAttemptCount==0 && complete.review==nil,"Sibling visit failed to revoke old completion preview")
    if let c=tasks.comment {c.close(expected:c.returnControl)}
    complete.prepare(expected:complete.control);await complete.submit(expected:complete.control)
    try expect(complete.submission?.phase == .confirmed && tasks.detail==original && tasks.items.map(\.status)==statuses && tasks.items.map(\.id)==ids,"Fake completion changed GET task/list/status")
    try expect(await transport.recorded().count==readCount,"Fake completion started a GET or real mutation")
    tasks.back();try expect(complete.source==nil && complete.retainedAttemptCount==1,"Task return lost attempt or exposed source outside parent")
    let readOnly=TaskListViewModel(repository:repository,completeSubmission:fixture);await readOnly.load(business:101,epoch:134);await readOnly.open(id:1101)
    try expect(readOnly.completion?.source==nil,"GET without independent fixture provenance bound completion authority")
    return count
}
