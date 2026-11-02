import Foundation
import CRMCore

@MainActor func checkTaskCancelControls(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let context=TaskCommentContext(business:101,task:1101,epoch:90),read=TaskCommentRead(context:TaskCommentContext(business:101,task:1101,epoch:90),revision:1)
    func bind(_ model:TaskCancelReasonViewModel,_ next:TaskCommentRead=TaskCommentRead(context:TaskCommentContext(business:101,task:1101,epoch:90),revision:1)) {model.begin(next);model.receive(true,status:"open",next)}
    func response(_ attempt:TaskCancelAttempt)->SyntheticTaskCancelOutcome {.response(status:200,task:WorkTask(id:attempt.authorization.context.task,title:"Synthetic task",status:"cancelled",priority:"normal",due_at:nil,business:attempt.authorization.context.business,cancelled_at:"2026-10-30T12:00:00Z",cancelled_by:attempt.authorization.actor,cancel_reason:attempt.review.text,updated_at:"2026-10-30T12:00:00Z"))}
    let port=ControlledTaskCancelPort(),model=TaskCancelReasonViewModel(port:port)
    model.open(expected:nil);model.askClear(expected:nil);try expect(model.control==nil && model.clearConfirmation==nil,"Nil UI controls opened editor or question")
    model.begin(read);model.open(expected:model.entryControl);try expect(model.control==nil,"Unverified independent read enabled editor")
    model.receive(true,status:"open",read);let entry=model.entryControl!;model.open(expected:entry);let first=model.control!,input=model.inputControl!
    model.open(expected:entry);model.prepare(expected:first)
    try expect(model.control==first && model.session.problem == .minimum,"Duplicate entry/empty preview replaced editable visit")
    for (raw,problem) in [("ab",TaskCancelReasonProblem.minimum),(String(repeating:"x",count:2001),.maximum),("ab\0cd",.characters)] {
        model.update(raw,input:input);model.prepare(expected:first)
        try expect(model.control==first && model.session.problem==problem && model.session.text==raw,"Reason validation changed stage or lost raw input")
    }
    model.update("  Same raw comment  \n",input:input);model.update("  Same raw comment  \n",input:input)
    try expect(model.inputControl==input && model.session.text=="  Same raw comment  \n","Continuous input changed visit or raw text")
    model.prepare(expected:first);let review=model.session.review!,reviewControl=model.control!
    model.update("old typing",input:input);model.back(expected:TaskCancelReasonReturnControl(editor:first,clear:nil))
    try expect(model.control==reviewControl && model.session.review==review && review.text=="Same raw comment","Stale editing Back/input changed exact preview")
    model.back(expected:model.returnControl);model.prepare(expected:model.control);let current=model.control!
    try expect(model.session.review==review && current != reviewControl,"Same-text review did not retain distinct UI phase")
    await model.submit(review,expected:reviewControl);try expect(await port.recorded().isEmpty,"Old same-text review submitted on a newer visit")
    model.back(expected:model.returnControl);let editing=model.control!,typing=model.inputControl!
    model.askClear(expected:editing);let question=model.clearConfirmation!;model.update("New own text",input:typing);model.confirmClear(question)
    try expect(model.clearConfirmation==nil && model.session.text=="New own text","Old clear consent erased new input")
    model.askClear(expected:editing);let replaced=model.clearConfirmation!;model.dismissClear(replaced);model.askClear(expected:editing);let active=model.clearConfirmation!
    model.dismissClear(replaced);model.confirmClear(replaced)
    try expect(model.clearConfirmation==active && model.session.text=="New own text","Old dialog consumed replacement clear consent")
    model.back(expected:TaskCancelReasonReturnControl(editor:editing,clear:nil));try expect(model.clearConfirmation==active,"Old parent Back bypassed question")
    model.back(expected:model.returnControl);model.close(expected:model.returnControl);model.open(expected:model.entryControl);model.confirmClear(active)
    try expect(model.session.text=="New own text" && model.control != nil,"Close/reopen lost raw buffer or accepted old consent")
    model.askClear(expected:model.control);model.confirmClear(model.clearConfirmation!)
    try expect(model.control==nil && model.session.text.isEmpty,"Current explicit clear did not remove own local buffer")
    model.open(expected:model.entryControl);model.update("  Immutable raw attempt  \n",input:model.inputControl);model.prepare(expected:model.control)
    let sendingControl=model.control!,sendingReview=model.session.review!;model.askClear(expected:sendingControl);let beforeSubmit=model.clearConfirmation!
    // Trusted raw submission can start while an old question is queued; it must revoke consent.
    let sending=Task {await model.submit(sendingReview)};await port.wait(0);let pending=model.control!,pendingRecord=model.submission!
    model.confirmClear(beforeSubmit);model.askClear(expected:pending);model.update("overwrite",input:typing);await model.submit(sendingReview,expected:sendingControl)
    try expect(model.clearConfirmation==nil && model.submissionBlocked && model.inputControl==nil && model.submission==pendingRecord && model.session.text=="  Immutable raw attempt  \n","Pending submit did not revoke clear/edit actions or retain raw attempt")
    try expect(await port.recorded().count==1,"Queued duplicate submitted twice")
    model.back(expected:model.returnControl);model.open(expected:model.entryControl);let reopened=model.control!
    await port.resolve(0,.rejectedWithoutWrite);await sending.value;let rejected=model.control!,record=model.submission!
    model.acknowledge(expected:pending,record:record);model.acknowledge(expected:reopened,record:record)
    try expect(model.submission==record && record.phase == .rejected && rejected != reopened,"Old pending/reopened UI acknowledged new terminal result")
    model.acknowledge(expected:rejected,record:record)
    try expect(!model.submissionBlocked && model.session.text=="  Immutable raw attempt  \n" && model.session.phase == .editing && model.retainedAttemptCount==1,"Current no-write acknowledgement lost raw input or retained active blocker")
    await model.submit(sendingReview,expected:sendingControl);try expect(await port.recorded().count==1,"Acknowledgement blindly replayed old review")
    model.prepare(expected:model.control);let unknownControl=model.control!,unknownReview=model.session.review!
    let lost=Task {await model.submit(unknownReview,expected:unknownControl)};await port.wait(1);await port.loseReply(1);await lost.value
    let unknown=model.submission!,nextRead=TaskCommentRead(context:context,revision:2)
    bind(model,nextRead);model.open(expected:model.entryControl);let afterRead=model.control!
    model.askClear(expected:afterRead);model.discard(afterRead.selection);model.acknowledge(expected:afterRead,record:unknown);await model.submit(unknownReview,expected:afterRead)
    try expect(model.submission==unknown && unknown.phase == .unknown && model.submissionBlocked && model.clearConfirmation==nil && model.session.text==unknown.attempt.raw && model.retainedAttemptCount==2,"Matching reread resolved unknown or allowed destructive clear/ack/replay")
    let closedRead=TaskCommentRead(context:context,revision:3);model.begin(closedRead);model.receive(true,status:"cancelled",closedRead);model.open(expected:model.entryControl)
    try expect(!model.session.available && model.entryControl==nil && model.submissionBlocked && model.submission==nil && model.retainedAttemptCount==2,"Matching cancelled status was treated as attempt proof or enabled editor")
    bind(model,TaskCommentRead(context:context,revision:4));model.open(expected:model.entryControl)
    try expect(model.submission==unknown && model.submissionBlocked && model.inputControl==nil,"Fresh actionable status released an unknown cancellation")
    let newEpoch=TaskCommentRead(context:TaskCommentContext(business:101,task:1101,epoch:91),revision:5);bind(model,newEpoch);model.open(expected:model.entryControl)
    try expect(model.submission==nil && model.submissionBlocked && model.inputControl==nil && model.retainedAttemptCount==2,"New epoch exposed or discarded old-owner unknown attempt")
    model.confirmClear(beforeSubmit);model.acknowledge(expected:afterRead,record:unknown)
    try expect(model.submissionBlocked && model.retainedAttemptCount==2,"Old owner consent released quarantined attempt")
    // Completion of a different Task cannot invalidate the current local input visit.
    let foreignPort=ControlledTaskCancelPort(),foreign=TaskCancelReasonViewModel(port:foreignPort);bind(foreign);foreign.open(expected:foreign.entryControl);foreign.update("Old Task raw",input:foreign.inputControl);foreign.prepare(expected:foreign.control)
    let foreignReview=foreign.session.review!,foreignControl=foreign.control!
    let older=Task {await foreign.submit(foreignReview,expected:foreignControl)};await foreignPort.wait(0)
    let otherRead=TaskCommentRead(context:TaskCommentContext(business:101,task:1102,epoch:90),revision:4);bind(foreign,otherRead);foreign.open(expected:foreign.entryControl);let otherInput=foreign.inputControl!,otherControl=foreign.control!
    foreign.update("Other Task own text",input:otherInput);await foreignPort.resolve(0,.unknown);await older.value
    try expect(foreign.control==otherControl && foreign.inputControl==otherInput && foreign.session.text=="Other Task own text" && !foreign.submissionBlocked && foreign.retainedAttemptCount==1,"Foreign completion advanced/erased unrelated current editor")
    // End-to-end fixture parent ownership, exact confirmed result and no Task projection mutation.
    let transport=SearchTransport(directory),parentPort=ControlledTaskCancelPort(),parent=TaskListViewModel(repository:APIReadRepository(transport:transport),commentSource:FixtureTaskCommentDraftSource(directory:directory),cancelSubmission:parentPort)
    await parent.load(business:101,epoch:90);await parent.open(id:1101);let editor=parent.cancelReason!,detail=parent.detail,rows=parent.items,detailSelection=parent.detailSelection,before=await transport.recorded(),parentBack=editor.returnControl
    parent.openCancelReason(editor.session.read!);editor.update("  Parent local comment  ",input:editor.inputControl);editor.prepare(expected:editor.control)
    parent.back(expected:detailSelection,comment:parent.comment?.returnControl,reason:parentBack)
    try expect(parent.selectedID==1101 && editor.control != nil,"Old parent pop closed current comment editor")
    let submitControl=editor.control!,submitReview=editor.session.review!,submitTask=Task {await editor.submit(submitReview,expected:submitControl)};await parentPort.wait(0)
    let attempt=await parentPort.recorded()[0];await parentPort.resolve(0,response(attempt));await submitTask.value;let result=editor.submission!,resultControl=editor.control!
    editor.acknowledge(expected:submitControl,record:result);try expect(editor.submissionBlocked,"Old submit control acknowledged its later confirmed result")
    editor.acknowledge(expected:resultControl,record:result)
    try expect(editor.control==nil && editor.session.text.isEmpty && !editor.submissionBlocked && editor.retainedAttemptCount==1,"Current confirmed fake acknowledgement failed to close/clear while retaining attempt")
    let after=await transport.recorded();try expect(parent.detail==detail && parent.items==rows && after==before,"Local synthetic result appended history/changed Task/list or issued GET")
    parent.back(expected:detailSelection,comment:parent.comment?.returnControl,reason:editor.returnControl);try expect(parent.selectedID==nil,"Current child-free parent Back failed")
    for noGrant in [TaskCancelReasonViewModel(),TaskCancelReasonViewModel(port:ControlledTaskCancelPort(update:false))] {
        bind(noGrant);noGrant.open(expected:noGrant.entryControl);noGrant.update("Readable only",input:noGrant.inputControl);noGrant.prepare(expected:noGrant.control)
        await noGrant.submit(noGrant.session.review!,expected:noGrant.control)
        try expect(!noGrant.canSubmit && noGrant.retainedAttemptCount==0,"Readable fixture inferred UPDATE/actor grant")
    }
    for status in [nil,"","open","in_progress","done","cancelled","future"] as [String?] {
        let statusModel=TaskCancelReasonViewModel();statusModel.begin(read);statusModel.receive(true,status:status,read)
        try expect(statusModel.session.available==["open","in_progress"].contains(status ?? ""),"Read source status invented cancellability")
        statusModel.receive(false,status:status,read);try expect(statusModel.entryControl==nil,"Unverified read enabled cancellation entry")
    }
    return count
}
