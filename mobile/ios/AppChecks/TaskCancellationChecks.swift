import Foundation
import CRMCore

actor ControlledTaskCancelPort: SyntheticTaskCancelPort {
    nonisolated let grants: [SyntheticTaskCancelGrant]
    private var attempts: [TaskCancelAttempt]=[]
    private var pending: [Int:CheckedContinuation<SyntheticTaskCancelOutcome,any Error>]=[:]
    private var waiters: [Int:CheckedContinuation<Void,Never>]=[:]
    init(update: Bool=true) {grants=[SyntheticTaskCancelGrant(business:101,task:1101,actor:9001,update:update),SyntheticTaskCancelGrant(business:202,task:1201,actor:9002,update:update)]}
    func execute(_ attempt: TaskCancelAttempt) async throws -> SyntheticTaskCancelOutcome {
        let id=attempts.count;attempts.append(attempt)
        return try await withCheckedThrowingContinuation {pending[id]=$0;waiters.removeValue(forKey:id)?.resume()}
    }
    func wait(_ id: Int) async {if pending[id]==nil {await withCheckedContinuation {waiters[id]=$0}}}
    func recorded() -> [TaskCancelAttempt] {attempts}
    func resolve(_ id: Int,_ outcome: SyntheticTaskCancelOutcome) {pending.removeValue(forKey:id)!.resume(returning:outcome)}
    func loseReply(_ id: Int) {pending.removeValue(forKey:id)!.resume(throwing:ReadFailure.unavailable)}
}

@MainActor func checkTaskCancellation(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let fixture=FixtureTaskCommentDraftSource(directory:directory),transport=SearchTransport(directory),repo=APIReadRepository(transport:transport)
    func review(_ model: TaskCancelReasonViewModel,_ raw: String="  Manual reason\n") -> TaskCancelReasonReview {model.open(model.session.read!);let selection=model.session.selection!;model.update(raw,selection);model.prepare(selection);return model.session.review!}
    func response(_ attempt: TaskCancelAttempt) -> SyntheticTaskCancelOutcome {.response(status:200,task:WorkTask(id:attempt.authorization.context.task,title:"Synthetic task",status:"cancelled",priority:"normal",due_at:nil,business:attempt.authorization.context.business,cancelled_at:"2026-10-30T12:00:00Z",cancelled_by:attempt.authorization.actor,cancel_reason:attempt.review.text,updated_at:"2026-10-30T12:00:00Z"))}
    let port=ControlledTaskCancelPort(),owner=TaskListViewModel(repository:repo,commentSource:fixture,cancelSubmission:port)
    await owner.load(business:101,epoch:1);await owner.open(id:1101);let model=owner.cancelReason!,first=review(model),detail=owner.detail,rows=owner.items,reads=await transport.recorded()
    try expect(model.canSubmit && owner.comment?.canSubmit==false,"Cancel capability leaked into comment port or missing positive scope")
    model.back(first.selection);model.update("Changed review",first.selection);model.prepare(first.selection);await model.submit(first)
    try expect(await port.recorded().isEmpty,"Old review sent newly changed reason")
    let current=model.session.review!,sending=Task {await model.submit(current)};await port.wait(0)
    await model.submit(current);model.update("overwrite",current.selection);model.discard(current.selection)
    try expect(await port.recorded().count==1 && model.submission?.phase == .pending && model.session.text=="Changed review","Pending cancellation allowed duplicate/change/clear")
    model.back(current.selection);model.open(model.session.read!);let reopened=model.session.selection!
    let attempt=await port.recorded()[0];await port.resolve(0,response(attempt));await sending.value
    try expect(model.submission?.phase == .confirmed && model.submission?.task?.business==101,"Validated200 cancellation did not become synthetic result")
    try expect(await transport.recorded()==reads && owner.detail==detail && owner.items==rows && owner.detail?.task.status=="open","Fake cancellation mutated actual Task/read/history or issued GET")
    model.acknowledge(current.selection,attemptID:attempt.localID);try expect(model.submission?.phase == .confirmed,"Stale result sheet acknowledged current result")
    model.acknowledge(reopened,attemptID:attempt.localID);try expect(model.session.text.isEmpty && model.session.selection==nil && model.retainedAttemptCount==1,"Explicit fake result close did not preserve attempt/clear composer")

    let rejection=review(model),rejecting=Task {await model.submit(rejection)};await port.wait(1);await port.resolve(1,.rejectedWithoutWrite);await rejecting.value
    model.close(rejection.selection);model.open(model.session.read!);let errorReturn=model.session.selection!
    model.acknowledge(errorReturn,attemptID:2)
    try expect(model.session.phase == .editing && model.session.selection==errorReturn && model.session.text=="  Manual reason\n","Reopened no-write error failed to return to current retained editor")
    await model.submit(rejection);try expect(await port.recorded().count==2,"Old review/reopen retried after no-write error")
    model.prepare(errorReturn);let unknownReview=model.session.review!,unknown=Task {await model.submit(unknownReview)};await port.wait(2);await port.loseReply(2);await unknown.value
    try expect(model.submission?.phase == .unknown && model.submissionBlocked && model.session.text=="  Manual reason\n","Lost cancellation reply lost input or inferred failure/success")
    model.acknowledge(errorReturn,attemptID:2);model.acknowledge(errorReturn,attemptID:3);model.discard(errorReturn);await model.submit(unknownReview)
    try expect(await port.recorded().count==3 && model.submission?.phase == .unknown,"Unknown cancellation cleared/replayed by stale/fresh buttons")
    owner.back();try expect(model.submission==nil && model.session.text.isEmpty,"Parent Back exposed old cancellation text/result")
    await owner.open(id:1101);model.open(model.session.read!)
    try expect(model.submission?.phase == .unknown && model.session.text=="  Manual reason\n" && !model.canSubmit,"Fresh same task read proved/replayed unknown cancellation")

    let racePort=ControlledTaskCancelPort(),raceOwner=TaskListViewModel(repository:repo,commentSource:fixture,cancelSubmission:racePort)
    await raceOwner.load(business:101,epoch:10);await raceOwner.open(id:1101);let race=raceOwner.cancelReason!,old=review(race),racing=Task {await race.submit(old)};await racePort.wait(0);let oldAttempt=await racePort.recorded()[0]
    raceOwner.reconcileCommentOwner(business:202,epoch:11);await raceOwner.load(business:202,epoch:11);await raceOwner.open(id:1201)
    await racePort.resolve(0,response(oldAttempt));await racing.value
    try expect(race.submission==nil && race.session.text.isEmpty && race.retainedAttemptCount==1,"Late old Business cancellation result leaked")
    await raceOwner.load(business:101,epoch:12);await raceOwner.open(id:1101);race.open(race.session.read!)
    try expect(race.submission==nil && race.submissionBlocked && !race.canSubmit,"New epoch exposed result/replayed same target cancellation")

    let cancelPort=ControlledTaskCancelPort(),cancelOwner=TaskListViewModel(repository:repo,commentSource:fixture,cancelSubmission:cancelPort)
    await cancelOwner.load(business:101,epoch:20);await cancelOwner.open(id:1101);let cancelled=cancelOwner.cancelReason!,c=review(cancelled),cancelling=Task {await cancelled.submit(c)};await cancelPort.wait(0);cancelling.cancel();let cancelAttempt=await cancelPort.recorded()[0];await cancelPort.resolve(0,response(cancelAttempt));await cancelling.value
    try expect(cancelled.submission?.phase == .unknown && cancelled.submissionBlocked,"Cancelled await inferred definite cancellation outcome")
    for candidate in [TaskListViewModel(repository:repo,commentSource:fixture),TaskListViewModel(repository:repo,commentSource:fixture,cancelSubmission:ControlledTaskCancelPort(update:false))] {
        await candidate.load(business:101,epoch:30);await candidate.open(id:1101);let local=candidate.cancelReason!,r=review(local);await local.submit(r)
        try expect(!local.canSubmit && local.retainedAttemptCount==0,"Read/default dependency granted cancellation UPDATE")
        await candidate.open(id:1103);try expect(candidate.cancelReason?.session.available==false,"Closed source task acquired cancellation editor")
    }
    let fixtureOwner=TaskListViewModel(repository:repo,commentSource:fixture,cancelSubmission:FixtureTaskCancelPort(directory:directory))
    for (business,id,phase) in [(101,1101,TaskCancelAttemptPhase.confirmed),(101,1102,.unknown),(202,1201,.rejected)] {
        await fixtureOwner.load(business:business,epoch:40);await fixtureOwner.open(id:id);let local=fixtureOwner.cancelReason!,r=review(local);await local.submit(r)
        try expect(local.submission?.phase==phase,"DEBUG fixture cancellation path unavailable \(id)")
    }
    // Same reopen/error transition in the existing comment flow must keep its current editor too.
    let commentPort=ControlledCommentSubmitPort(),commentOwner=TaskListViewModel(repository:repo,commentSource:fixture,commentSubmission:commentPort)
    await commentOwner.load(business:101,epoch:50);await commentOwner.open(id:1101);let comment=commentOwner.comment!;comment.open(comment.session.read!);let cs=comment.session.selection!;comment.update("Manual comment",cs);comment.prepare(cs);let cr=comment.session.review!,commenting=Task {await comment.submit(cr)};await commentPort.wait(0);await commentPort.resolve(0,.rejectedWithoutWrite);await commenting.value
    comment.close(cs);comment.open(comment.session.read!);let fresh=comment.session.selection!;comment.acknowledge(fresh,attemptID:1)
    try expect(comment.session.phase == .editing && comment.session.selection==fresh && comment.session.text=="Manual comment","Reopened comment no-write result closed/lost retained editor")
    return count
}
