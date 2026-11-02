import Foundation
import CRMCore

actor ControlledCommentSubmitPort: SyntheticTaskCommentPort {
    nonisolated let grants: [SyntheticTaskCommentGrant]
    private var attempts: [TaskCommentAttempt]=[]
    private var pending: [Int:CheckedContinuation<SyntheticTaskCommentOutcome,any Error>]=[:]
    private var waiters: [Int:CheckedContinuation<Void,Never>]=[:]
    init(update: Bool=true) {grants=[SyntheticTaskCommentGrant(business:101,task:1101,actor:9001,update:update),SyntheticTaskCommentGrant(business:202,task:1201,actor:9002,update:update)]}
    func execute(_ attempt: TaskCommentAttempt) async throws -> SyntheticTaskCommentOutcome {
        let id=attempts.count;attempts.append(attempt)
        return try await withCheckedThrowingContinuation {pending[id]=$0;waiters.removeValue(forKey:id)?.resume()}
    }
    func wait(_ id: Int) async {if pending[id]==nil {await withCheckedContinuation {waiters[id]=$0}}}
    func recorded() -> [TaskCommentAttempt] {attempts}
    func resolve(_ id: Int,_ outcome: SyntheticTaskCommentOutcome) {pending.removeValue(forKey:id)!.resume(returning:outcome)}
    func loseReply(_ id: Int) {pending.removeValue(forKey:id)!.resume(throwing:ReadFailure.unavailable)}
}

@MainActor private func submitCommentForCheck(_ model: TaskCommentViewModel,_ selection: TaskCommentSelection) async {
    guard let review=model.session.review,review.selection==selection else {return};await model.submit(review)
}
@MainActor private func ackCommentForCheck(_ model: TaskCommentViewModel,_ selection: TaskCommentSelection) {
    if let id=model.submission?.attempt.localID {model.acknowledge(selection,attemptID:id)}
}

@MainActor func checkTaskCommentSubmission(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let source=FixtureTaskCommentDraftSource(directory:directory),transport=SearchTransport(directory),repo=APIReadRepository(transport:transport)
    func review(_ model: TaskCommentViewModel,_ raw: String="  Manual comment\n") -> TaskCommentSelection {
        model.open(model.session.read!);let selection=model.session.selection!;model.update(raw,selection);model.prepare(selection);return selection
    }
    func response(_ attempt: TaskCommentAttempt) -> SyntheticTaskCommentOutcome {
        .response(status:201,comment:TaskComment(id:8801,text:attempt.text,created_at:"2026-10-30T12:00:00Z",task:attempt.authorization.context.task,author:attempt.authorization.actor,author_name:"Synthetic employee",author_email:"fixture@example.invalid"))
    }
    let stalePort=ControlledCommentSubmitPort(),staleOwner=TaskListViewModel(repository:repo,commentSource:source,commentSubmission:stalePort)
    await staleOwner.load(business:101,epoch:9);await staleOwner.open(id:1101);let stale=staleOwner.comment!,staleSelection=review(stale),oldReview=stale.session.review!
    stale.back(staleSelection);stale.update("Changed review",staleSelection);stale.prepare(staleSelection)
    await stale.submit(oldReview);try expect(await stalePort.recorded().isEmpty,"Old review button submitted newly edited text")
    let port=ControlledCommentSubmitPort(),owner=TaskListViewModel(repository:repo,commentSource:source,commentSubmission:port)
    await owner.load(business:101,epoch:10);await owner.open(id:1101)
    let comment=owner.comment!,selection=review(comment),detail=owner.detail!,rows=owner.items,before=await transport.recorded()
    let sending=Task {await submitCommentForCheck(comment,selection)};await port.wait(0)
    try expect(comment.submission?.phase == .pending && !comment.canSubmit,"Pending state missing or submit enabled")
    await submitCommentForCheck(comment,selection);comment.update("overwrite",selection);comment.discard(selection)
    try expect(await port.recorded().count==1 && comment.session.text=="  Manual comment\n" && comment.retainedAttemptCount==1,"Double click/clear/editor changed pending attempt")
    comment.back(selection);try expect(comment.session.selection==nil && comment.submission?.phase == .pending,"Back cancelled or forgot pending outcome")
    comment.open(comment.session.read!);let reopened=comment.session.selection!;ackCommentForCheck(comment,selection)
    try expect(comment.session.selection==reopened,"Stale modal acknowledged current pending result")
    let sent=await port.recorded()[0];await port.resolve(0,response(sent));await sending.value
    try expect(comment.submission?.phase == .confirmed && comment.submission?.comment?.author==9001,"Validated fake response did not reach explicit synthetic result")
    try expect(await transport.recorded()==before && owner.detail==detail && owner.items==rows,"Fake submit touched GET transport/Task comments/status/rows")
    ackCommentForCheck(comment,selection);try expect(comment.submission?.phase == .confirmed,"Old sheet cleared current result")
    ackCommentForCheck(comment,reopened);try expect(comment.session.selection==nil && comment.session.text.isEmpty && !comment.submissionBlocked && comment.retainedAttemptCount==1,"Explicit success close did not clear composer or preserve attempt")

    let rejected=review(comment,"  Preserve no-write input  "),rejectTask=Task {await submitCommentForCheck(comment,rejected)};await port.wait(1)
    await port.resolve(1,.rejectedWithoutWrite);await rejectTask.value
    await submitCommentForCheck(comment,rejected);try expect(await port.recorded().count==2 && comment.submission?.phase == .rejected,"No-write error automatically retried")
    ackCommentForCheck(comment,rejected);try expect(comment.session.phase == .editing && comment.session.text=="  Preserve no-write input  " && comment.submission==nil,"Confirmed no-write failure lost input or skipped review")
    await submitCommentForCheck(comment,rejected);try expect(await port.recorded().count==2,"Edit retried without explicit review")
    let oldRejectionID=comment.retainedAttemptCount
    comment.prepare(rejected);let unknownTask=Task {await submitCommentForCheck(comment,rejected)};await port.wait(2);await port.loseReply(2);await unknownTask.value
    comment.acknowledge(rejected,attemptID:oldRejectionID)
    try expect(comment.submission?.phase == .unknown && comment.session.text=="  Preserve no-write input  ","Lost response became failure/success or erased raw text")
    ackCommentForCheck(comment,rejected);comment.discard(rejected);await submitCommentForCheck(comment,rejected)
    try expect(await port.recorded().count==3 && comment.submission?.phase == .unknown && comment.retainedAttemptCount==3,"Unknown allowed acknowledge/discard/replay")
    owner.back();await owner.open(id:1101);let afterRead=comment.session.read!;comment.open(afterRead)
    try expect(comment.submission?.phase == .unknown && comment.session.text=="  Preserve no-write input  ","Fresh same-task read incorrectly proved/retried unknown outcome")
    await submitCommentForCheck(comment,comment.session.selection!);try expect(await port.recorded().count==3,"Reread replayed unknown")

    let racePort=ControlledCommentSubmitPort(),raceOwner=TaskListViewModel(repository:repo,commentSource:source,commentSubmission:racePort)
    await raceOwner.load(business:101,epoch:20);await raceOwner.open(id:1101);let race=raceOwner.comment!,old=review(race,"Private old context")
    let racing=Task {await submitCommentForCheck(race,old)};await racePort.wait(0);let oldAttempt=await racePort.recorded()[0]
    raceOwner.reconcileCommentOwner(business:202,epoch:21)
    await raceOwner.load(business:202,epoch:21);await raceOwner.open(id:1201)
    await racePort.resolve(0,response(oldAttempt));await racing.value
    try expect(race.submission==nil && race.session.text.isEmpty && race.session.read?.context.business==202 && race.retainedAttemptCount==1,"Late old Business success leaked into current composer")
    await raceOwner.load(business:101,epoch:22);await raceOwner.open(id:1101);let newSelection=review(race,"New epoch")
    try expect(race.submission==nil && race.submissionBlocked && !race.canSubmit,"New epoch exposed old success/attempt or allowed blind resubmit")
    await submitCommentForCheck(race,newSelection);try expect(await racePort.recorded().count==1,"Old target attempt replayed in new epoch")

    let cancelPort=ControlledCommentSubmitPort(),cancelOwner=TaskListViewModel(repository:repo,commentSource:source,commentSubmission:cancelPort)
    await cancelOwner.load(business:101,epoch:30);await cancelOwner.open(id:1101);let cancelled=cancelOwner.comment!,cancelSelection=review(cancelled)
    let cancelling=Task {await submitCommentForCheck(cancelled,cancelSelection)};await cancelPort.wait(0);cancelling.cancel();let cancelledAttempt=await cancelPort.recorded()[0];await cancelPort.resolve(0,response(cancelledAttempt));await cancelling.value
    try expect(cancelled.submission?.phase == .unknown && cancelled.submissionBlocked,"Cancelled await inferred write failure/success or enabled repeat")

    for candidate in [TaskListViewModel(repository:repo,commentSource:source),TaskListViewModel(repository:repo,commentSource:source,commentSubmission:ControlledCommentSubmitPort(update:false))] {
        await candidate.load(business:101,epoch:40);await candidate.open(id:1101);let local=candidate.comment!,s=review(local)
        await submitCommentForCheck(local,s);try expect(!local.canSubmit && local.retainedAttemptCount==0 && local.session.phase == .review,"Read permission/default dependency enabled synthetic UPDATE")
    }
    let fixturePort=FixtureTaskCommentSubmitPort(directory:directory)
    let fixtureOwner=TaskListViewModel(repository:repo,commentSource:source,commentSubmission:fixturePort)
    for (business,id,expected) in [(101,1101,TaskCommentAttemptPhase.confirmed),(101,1102,.unknown),(101,1103,.rejected),(202,1201,.confirmed)] {
        await fixtureOwner.load(business:business,epoch:50);await fixtureOwner.open(id:id);let fixtureComment=fixtureOwner.comment!,s=review(fixtureComment)
        await submitCommentForCheck(fixtureComment,s);try expect(fixtureComment.submission?.phase==expected,"DEBUG fixture composition cannot reach action outcome \(id)")
    }
    count += try await checkTaskCommentExactText(directory:directory)
    return count
}

@MainActor private func checkTaskCommentExactText(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let cases=(try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-comment-exact-text-cases.json"))) as! [String:Any])["cases"] as! [[String:Any]]
    for (index,row) in cases.enumerated() {
        let before=row["before"] as! String,after=row["after"] as! String,changed=row["changed"] as! Bool,source=FixtureTaskCommentDraftSource(directory:directory),transport=SearchTransport(directory),port=ControlledCommentSubmitPort(),owner=TaskListViewModel(repository:APIReadRepository(transport:transport),commentSource:source,commentSubmission:port),epoch=3100+index
        await owner.load(business:101,epoch:epoch);await owner.open(id:1101);let model=owner.comment!,detail=owner.detail,rows=owner.items,reads=await transport.recorded();owner.openComment(model.session.read!);let input=model.inputControl!
        model.update(before,input:input);model.askClear(expected:model.control);let oldQuestion=model.clearConfirmation!;model.update(after,input:input)
        if changed {try expect(model.clearConfirmation==nil,"Raw Unicode change retained stale destructive Clear consent");model.confirmClear(oldQuestion);try expect(model.session.text.utf8.elementsEqual(after.utf8) && model.inputControl==input,"Old Clear erased byte-different current input");model.askClear(expected:model.control)}
        else {try expect(model.clearConfirmation==oldQuestion,"Identical raw callback revoked unchanged Clear consent")}
        model.confirmClear(model.clearConfirmation!);try expect(model.session.text.isEmpty && model.session.selection==nil,"Current explicit Clear failed")
        owner.openComment(model.session.read!);model.update(before,input:model.inputControl);var alternate=model.session;alternate.update(after,expected:alternate.selection!);_=alternate.prepare(expected:alternate.selection!);model.prepare(expected:model.control);let review=model.session.review!,control=model.control!
        if changed {await model.submit(alternate.review!,expected:control);try expect(await port.recorded().isEmpty && model.canSubmit,"Byte-different same-selection review passed UI/ledger gate")}
        let sending=Task {await model.submit(review,expected:control)};await port.wait(0);let attempt=await port.recorded()[0]
        model.update(after,input:input);model.askClear(expected:model.control);model.confirmClear(oldQuestion);await model.submit(review,expected:control)
        try expect(model.submission?.phase == .pending && model.submissionBlocked && model.clearConfirmation==nil && model.session.text.utf8.elementsEqual(before.utf8),"Pending fake attempt lost raw text or allowed Clear/overwrite")
        let echo=try JSONDecoder().decode(TaskComment.self,from:Data((row["after_response_json"] as! String).utf8));await port.resolve(0,.response(status:201,comment:echo));await sending.value
        let record=model.submission!,phase:TaskCommentAttemptPhase=changed ? .unknown:.confirmed
        try expect(record.phase==phase && record.attempt==attempt && record.attempt.raw.utf8.elementsEqual(before.utf8) && record.attempt.text.utf8.elementsEqual(review.text.utf8),"Typed201 echo changed exact attempt identity or wrong outcome")
        try expect(await transport.recorded()==reads && owner.detail==detail && owner.items==rows,"Fake outcome altered GET transport, Task rows/comments/status")
        if changed {
            model.acknowledge(expected:model.control,record:record);model.discard(model.session.selection!);await model.submit(review,expected:model.control)
            try expect(model.submission==record && model.submissionBlocked && model.session.text.utf8.elementsEqual(before.utf8) && model.retainedAttemptCount==1,"Unknown echo mismatch allowed destructive acknowledge/discard/replay")
            owner.back();await owner.open(id:1101);owner.openComment(model.session.read!);try expect(model.submission==record && model.session.text.utf8.elementsEqual(before.utf8),"Fresh same-task GET changed unknown or dropped raw input")
            await model.submit(review,expected:model.control);try expect(await port.recorded().count==1,"Reread replayed unknown comment")
            await owner.load(business:101,epoch:epoch+100);await owner.open(id:1101);owner.openComment(model.session.read!)
            try expect(model.submission==nil && model.submissionBlocked && model.inputControl==nil && model.retainedAttemptCount==1,"New epoch exposed/forgot old attempt or permitted blind repeat")
        }
        let positiveTransport=SearchTransport(directory),positivePort=ControlledCommentSubmitPort(),positiveOwner=TaskListViewModel(repository:APIReadRepository(transport:positiveTransport),commentSource:source,commentSubmission:positivePort)
        await positiveOwner.load(business:101,epoch:epoch+500);await positiveOwner.open(id:1101);let positive=positiveOwner.comment!;positiveOwner.openComment(positive.session.read!);positive.update(before,input:positive.inputControl);positive.prepare(expected:positive.control);let acceptedReview=positive.session.review!,submittedControl=positive.control!,positiveDetail=positiveOwner.detail,positiveRows=positiveOwner.items,positiveReads=await positiveTransport.recorded()
        let exactSending=Task {await positive.submit(acceptedReview,expected:submittedControl)};await positivePort.wait(0);let exact=try JSONDecoder().decode(TaskComment.self,from:Data((row["before_response_json"] as! String).utf8));await positivePort.resolve(0,.response(status:201,comment:exact));await exactSending.value
        let accepted=positive.submission!;try expect(accepted.phase == .confirmed && accepted.comment?.text?.utf8.elementsEqual(acceptedReview.text.utf8)==true,"Exact Unicode201 failed real controller positive receipt")
        positive.acknowledge(expected:submittedControl,record:accepted);try expect(positive.submissionBlocked,"Old submit control acknowledged later result")
        positive.acknowledge(expected:positive.control,record:accepted);try expect(positive.session.text.isEmpty && !positive.submissionBlocked && positive.retainedAttemptCount==1,"Current explicit exact201 result close failed")
        try expect(await positiveTransport.recorded()==positiveReads && positiveOwner.detail==positiveDetail && positiveOwner.items==positiveRows,"Exact fake201 optimistically appended Task comment or changed GET state")
    }
    return count
}
