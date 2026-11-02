import Foundation
import CRMCore

actor ControlledTaskCreatePort: SyntheticTaskCreatePort {
    nonisolated let grants:[SyntheticTaskCreateGrant]
    private var attempts:[TaskCreateAttempt]=[]
    private var pending:[Int:CheckedContinuation<SyntheticTaskCreateOutcome,any Error>]=[:]
    private var waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    init(create:Bool=true) {grants=[SyntheticTaskCreateGrant(business:101,actor:9001,create:create),SyntheticTaskCreateGrant(business:202,actor:9002,create:create)]}
    func execute(_ attempt:TaskCreateAttempt) async throws -> SyntheticTaskCreateOutcome {let id=attempts.count;attempts.append(attempt);return try await withCheckedThrowingContinuation {pending[id]=$0;waiters.removeValue(forKey:id)?.resume()}}
    func wait(_ id:Int) async {if pending[id]==nil {await withCheckedContinuation {waiters[id]=$0}}}
    func recorded()->[TaskCreateAttempt] {attempts}
    func resolve(_ id:Int,_ outcome:SyntheticTaskCreateOutcome) {pending.removeValue(forKey:id)!.resume(returning:outcome)}
    func loseReply(_ id:Int) {pending.removeValue(forKey:id)!.resume(throwing:ReadFailure.unavailable)}
}

@MainActor func checkTaskCreation(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let transport=SearchTransport(directory),repo=APIReadRepository(transport:transport),context=TaskDraftContext(business:101,epoch:1)
    func review(_ model:TaskDraftViewModel,_ context:TaskDraftContext)->TaskDraftReview {model.open(context);let s=model.session.selection!;model.update(.title,"  Manual task\n",s);model.update(.description,"  Manual description\n",s);model.update(.priority,"high",s);model.prepare(s);return model.session.review!}
    func response(_ attempt:TaskCreateAttempt)->SyntheticTaskCreateOutcome {let v=attempt.review.preview;return .response(status:201,task:WorkTask(id:88001,title:v.title,status:"open",priority:v.priority,due_at:nil,business:attempt.authorization.context.business,updated_at:"2026-10-30T12:00:00Z",description:v.description,created_by:attempt.authorization.actor,created_at:"2026-10-30T12:00:00Z"))}
    let port=ControlledTaskCreatePort(),owner=TaskListViewModel(repository:repo,createSubmission:port)
    await owner.load(business:101,epoch:1);owner.query="Own filter";let model=owner.draft,old=review(model,context),rows=owner.items,reads=await transport.recorded()
    model.back(old.selection);model.update(.title,"Changed",old.selection);model.prepare(old.selection);await model.submit(old)
    try expect(await port.recorded().isEmpty,"Old preview click submitted new title")
    let current=model.session.review!,sending=Task {await model.submit(current)};await port.wait(0)
    await model.submit(current);model.update(.description,"overwrite",current.selection);model.discard(current.selection)
    try expect(await port.recorded().count==1 && model.submission?.phase == .pending && model.session.values.description=="  Manual description\n","Pending CREATE allowed repeat/edit/clear")
    model.back(current.selection);model.open(context);let fresh=model.session.selection!,sent=await port.recorded()[0];await port.resolve(0,response(sent));await sending.value
    try expect(model.submission?.phase == .confirmed && model.submission?.task?.created_by==9001,"Validated201 CREATE did not reach explicit synthetic result")
    try expect(await transport.recorded()==reads && owner.items==rows && owner.total==rows.count && owner.query=="Own filter","Fake create inserted/changed real list or requested data")
    model.acknowledge(current.selection,attemptID:1);try expect(model.submission?.phase == .confirmed,"Old result sheet acknowledged reopened result")
    model.acknowledge(fresh,attemptID:1);try expect(model.session.values==TaskDraftValues() && model.session.selection==nil && model.retainedAttemptCount==1,"Explicit synthetic result close did not retain attempt/clear form")

    let rejectingReview=review(model,context),rejecting=Task {await model.submit(rejectingReview)};await port.wait(1);await port.resolve(1,.rejectedWithoutWrite);await rejecting.value
    model.close(rejectingReview.selection);model.open(context);let errorSelection=model.session.selection!;model.acknowledge(errorSelection,attemptID:2)
    try expect(model.session.phase == .editing && model.session.selection==errorSelection && model.session.values==rejectingReview.values,"Reopened no-write error closed/rewrote raw form")
    await model.submit(rejectingReview);try expect(await port.recorded().count==2,"No-write error auto/replayed before fresh review")
    model.prepare(errorSelection);let unknownReview=model.session.review!,unknown=Task {await model.submit(unknownReview)};await port.wait(2);await port.loseReply(2);await unknown.value
    model.acknowledge(errorSelection,attemptID:2);model.acknowledge(errorSelection,attemptID:3);model.discard(errorSelection);await model.submit(unknownReview)
    try expect(await port.recorded().count==3 && model.submission?.phase == .unknown && model.session.values==unknownReview.values,"Lost response lost input or permitted blind CREATE replay")
    await owner.open(id:1101);try expect(model.session.selection==nil && model.retainedAttemptCount==3,"Parent detail navigation erased attempt or kept create sheet visible")
    owner.back();model.open(context)
    try expect(model.submission?.phase == .unknown && !model.canSubmit && model.session.values==unknownReview.values,"Back/reopen/reread proved unknown CREATE outcome")

    let racePort=ControlledTaskCreatePort(),raceOwner=TaskListViewModel(repository:repo,createSubmission:racePort)
    await raceOwner.load(business:101,epoch:10);let race=raceOwner.draft,oldContext=TaskDraftContext(business:101,epoch:10),r=review(race,oldContext),racing=Task {await race.submit(r)};await racePort.wait(0);let oldAttempt=await racePort.recorded()[0]
    raceOwner.reconcileCommentOwner(business:202,epoch:11);await raceOwner.load(business:202,epoch:11);await racePort.resolve(0,response(oldAttempt));await racing.value
    try expect(race.submission==nil && race.session.values==TaskDraftValues() && race.retainedAttemptCount==1,"Late old Business CREATE leaked old form/result")
    await raceOwner.load(business:101,epoch:12);let nextContext=TaskDraftContext(business:101,epoch:12);race.open(nextContext)
    try expect(race.submission==nil && race.submissionBlocked && !race.canSubmit,"New epoch exposed/replayed same-Business attempt")
    let cancelPort=ControlledTaskCreatePort(),cancelOwner=TaskListViewModel(repository:repo,createSubmission:cancelPort)
    await cancelOwner.load(business:101,epoch:20);let cancelled=cancelOwner.draft,c=review(cancelled,TaskDraftContext(business:101,epoch:20)),cancelling=Task {await cancelled.submit(c)};await cancelPort.wait(0);cancelling.cancel();let cancelAttempt=await cancelPort.recorded()[0];await cancelPort.resolve(0,response(cancelAttempt));await cancelling.value
    try expect(cancelled.submission?.phase == .unknown && cancelled.submissionBlocked,"Cancelled CREATE await inferred definite failure/success")
    for candidate in [TaskListViewModel(repository:repo),TaskListViewModel(repository:repo,createSubmission:ControlledTaskCreatePort(create:false)),TaskListViewModel(repository:repo,commentSource:FixtureTaskCommentDraftSource(directory:directory),commentSubmission:FixtureTaskCommentSubmitPort(directory:directory))] {
        await candidate.load(business:101,epoch:30);let local=candidate.draft,v=review(local,TaskDraftContext(business:101,epoch:30));await local.submit(v)
        try expect(!local.canSubmit && local.retainedAttemptCount==0,"VIEW/UPDATE/default dependency granted CREATE")
    }
    let fixtureOwner=TaskListViewModel(repository:repo,createSubmission:FixtureTaskCreatePort(directory:directory))
    for (business,phase) in [(101,TaskCreateAttemptPhase.confirmed),(202,.unknown)] {await fixtureOwner.load(business:business,epoch:40);let local=fixtureOwner.draft,v=review(local,TaskDraftContext(business:business,epoch:40));await local.submit(v);try expect(local.submission?.phase==phase,"Explicit DEBUG CREATE composition could not reach configured outcome")}
    return count
}
