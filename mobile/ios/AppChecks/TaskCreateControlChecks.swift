import Foundation
import CRMCore

@MainActor func checkTaskCreateControls(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let context=TaskDraftContext(business:101,epoch:100),port=ControlledTaskCreatePort(),model=TaskDraftViewModel(port:FixtureTaskCreatePort(directory:directory))
    func values(_ m:TaskDraftViewModel,_ title:String="  Manual title  \n") {let input=m.inputControl;m.update(.title,title,input:input);m.update(.description,"  Manual description  \n",input:input);m.update(.priority,"high",input:input)}
    func response(_ a:TaskCreateAttempt)->SyntheticTaskCreateOutcome {let v=a.review.preview;return .response(status:201,task:WorkTask(id:88001,title:v.title,status:"open",priority:v.priority,due_at:nil,business:a.authorization.context.business,updated_at:"2026-10-30T12:00:00Z",description:v.description,created_by:a.authorization.actor,created_at:"2026-10-30T12:00:00Z"))}
    model.open(expected:nil);try expect(model.control==nil,"Nil entry opened create composer")
    model.bind(context);let entry=model.entryControl!;model.open(expected:entry);let initial=model.control!,input=model.inputControl!
    model.open(expected:entry);model.prepare(expected:initial)
    try expect(model.control==initial && model.session.issues.contains(where:{$0.field == .title && $0.problem == .required}),"Duplicate entry/required validation lost editor visit")
    model.update(.title,String(repeating:"x",count:256),input:input);model.update(.description,"ab\0cd",input:input);model.update(.priority,"unsupported",input:input);model.prepare(expected:initial)
    try expect(model.control==initial && model.inputControl==input && Set(model.session.issues.map(\.field))==Set([TaskDraftField.title,.description,.priority]),"Field validation dropped raw input or changed visit")
    values(model);let raw=model.session.values;model.bind(context)
    try expect(model.inputControl==input && model.session.values==raw,"Same context bind reset continuous input")
    model.prepare(expected:initial);let review=model.session.review!,oldReview=model.control!
    model.update(.priority,"urgent",input:input);model.back(expected:TaskDraftReturnControl(editor:initial,clear:nil))
    try expect(model.control==oldReview && model.session.review==review && review.values==raw && review.preview.title=="Manual title" && review.preview.description=="Manual description","Old field/editor action changed exact preview")
    model.back(expected:model.returnControl);model.prepare(expected:model.control);let currentReview=model.control!
    try expect(model.session.review==review && currentReview != oldReview,"Identical field review lost distinct UI visit")
    await model.submit(review,expected:oldReview);try expect(model.retainedAttemptCount==0,"Old identical-review Submit created an attempt")
    model.back(expected:model.returnControl);let editing=model.control!,typing=model.inputControl!
    model.askClear(expected:editing);let question=model.clearConfirmation!;model.update(.description,"New own description",input:typing);model.confirmClear(question)
    try expect(model.clearConfirmation==nil && model.session.values.description=="New own description","Old clear erased a newer field edit")
    model.askClear(expected:editing);let previous=model.clearConfirmation!;model.dismissClear(previous);model.askClear(expected:editing);let active=model.clearConfirmation!
    model.dismissClear(previous);model.confirmClear(previous);model.back(expected:TaskDraftReturnControl(editor:editing,clear:nil))
    try expect(model.clearConfirmation==active && model.control==editing,"Old dialog/Back consumed replacement consent")
    model.back(expected:model.returnControl);model.close(expected:model.returnControl);model.open(expected:entry)
    try expect(model.control==nil && model.session.values.description=="New own description","Close erased own fields or old entry reopened composer")
    model.open(expected:model.entryControl);model.confirmClear(active);try expect(model.session.values.description=="New own description","Old closed-composer consent erased reopened input")
    model.askClear(expected:model.control);model.confirmClear(model.clearConfirmation!)
    try expect(model.control==nil && model.session.values==TaskDraftValues(),"Current explicit clear failed to restore existing empty values/normal priority")
    let m=TaskDraftViewModel(port:port);m.bind(context);m.open(expected:m.entryControl);values(m);m.prepare(expected:m.control)
    let submitControl=m.control!,submitReview=m.session.review!;m.askClear(expected:submitControl);let oldClear=m.clearConfirmation!
    let job=Task {await m.submit(submitReview)};await port.wait(0);let pending=m.control!,record=m.submission!
    m.confirmClear(oldClear);m.askClear(expected:pending);m.update(.title,"overwrite",input:TaskDraftInputControl(control:submitControl));await m.submit(submitReview,expected:submitControl)
    try expect(m.submission==record && m.clearConfirmation==nil && m.inputControl==nil && m.session.values==submitReview.values,"Pending create did not revoke clear/field actions or retain exact attempt")
    try expect(await port.recorded().count==1,"Queued duplicate started two create attempts")
    m.back(expected:m.returnControl);m.open(expected:m.entryControl);let reopened=m.control!
    await port.resolve(0,.rejectedWithoutWrite);await job.value;let rejected=m.control!,rejection=m.submission!
    m.acknowledge(expected:pending,record:rejection);m.acknowledge(expected:reopened,record:rejection)
    try expect(m.submission==rejection && rejection.phase == .rejected && rejected != reopened,"Old pending/reopened UI acknowledged terminal result")
    m.acknowledge(expected:rejected,record:rejection)
    try expect(!m.submissionBlocked && m.session.phase == .editing && m.session.values==submitReview.values && m.retainedAttemptCount==1,"No-write acknowledgement lost raw fields or auto-cleared attempt history")
    await m.submit(submitReview,expected:submitControl);try expect(await port.recorded().count==1,"No-write acknowledgement blindly retried")
    m.prepare(expected:m.control);let uncertain=m.session.review!,uncertainControl=m.control!,lost=Task {await m.submit(uncertain,expected:uncertainControl)};await port.wait(1);await port.loseReply(1);await lost.value
    let unknown=m.submission!,unknownControl=m.control!;m.bind(context);m.askClear(expected:unknownControl);m.discard(unknownControl.selection);m.acknowledge(expected:unknownControl,record:unknown);await m.submit(uncertain,expected:unknownControl)
    try expect(m.submission==unknown && unknown.phase == .unknown && m.submissionBlocked && m.session.values==uncertain.values && m.clearConfirmation==nil && m.retainedAttemptCount==2,"Same binding or queued actions released unknown create")
    m.bind(TaskDraftContext(business:101,epoch:101));m.open(expected:m.entryControl)
    try expect(m.submission==nil && m.submissionBlocked && m.inputControl==nil && m.retainedAttemptCount==2,"New epoch exposed or released prior create attempt")
    // A late other-Business completion cannot revoke the current local input visit.
    let otherPort=ControlledTaskCreatePort(),other=TaskDraftViewModel(port:otherPort);other.bind(context);other.open(expected:other.entryControl);values(other);other.prepare(expected:other.control)
    let olderReview=other.session.review!,olderControl=other.control!,older=Task {await other.submit(olderReview,expected:olderControl)};await otherPort.wait(0)
    other.bind(TaskDraftContext(business:202,epoch:102));other.open(expected:other.entryControl);let otherInput=other.inputControl!,otherControl=other.control!
    other.update(.title,"Other Business raw",input:otherInput);await otherPort.resolve(0,.unknown);await older.value
    try expect(other.control==otherControl && other.inputControl==otherInput && other.session.values.title=="Other Business raw" && !other.submissionBlocked && other.retainedAttemptCount==1,"Foreign completion revoked current unrelated form")
    // Fixture list composition: hidden list callbacks cannot close/refresh an active composer.
    let transport=SearchTransport(directory),parentPort=ControlledTaskCreatePort(),parent=TaskListViewModel(repository:APIReadRepository(transport:transport),createSubmission:parentPort)
    await parent.load(business:101,epoch:100);parent.query="";let list=parent.control!,query=parent.querySelection,rows=parent.items,total=parent.total,before=await transport.recorded(),draft=parent.draft,opening=parent.draft.entryControl!
    parent.openDraft(expected:opening,parent:list);values(draft);let composer=draft.control!,activeList=parent.control!
    parent.search("hidden search",expected:list);parent.filterStatus("done",previous:nil,expected:list);await parent.applyFilter(TaskQueryFilter(status:"done",due:.today),expected:query);await parent.refreshFilter(expected:query);await parent.retryList(expected:list);await parent.open(id:1101,expected:list)
    let afterHidden=await transport.recorded();try expect(parent.control==activeList && activeList != list && parent.selectedID==nil && parent.query.isEmpty && parent.appliedFilter==TaskQueryFilter() && afterHidden==before && draft.control==composer,"Captured hidden list actions affected active create form")
    draft.prepare(expected:composer);let prepared=draft.session.review!,preparedControl=draft.control!,creating=Task {await draft.submit(prepared,expected:preparedControl)};await parentPort.wait(0)
    let attempt=await parentPort.recorded()[0];await parentPort.resolve(0,response(attempt));await creating.value;let result=draft.submission!,resultControl=draft.control!
    draft.acknowledge(expected:preparedControl,record:result);try expect(draft.submissionBlocked,"Old submit control acknowledged later confirmed create")
    draft.acknowledge(expected:resultControl,record:result);let afterCreate=await transport.recorded()
    try expect(draft.control==nil && draft.session.values==TaskDraftValues() && draft.retainedAttemptCount==1 && parent.items==rows && parent.total==total && parent.query.isEmpty && afterCreate==before,"Fake success mutated list/count/query or failed explicit local acknowledgement")
    parent.openDraft(expected:opening,parent:list);try expect(draft.control==nil,"Old list entry reopened composer after result")
    await parent.open(id:1101,expected:list);try expect(parent.selectedID==nil,"Old pre-composer list callback survived return")
    await parent.open(id:1101,expected:parent.control);let detail=parent.detailSelection;parent.openDraft(expected:draft.entryControl,parent:activeList)
    try expect(parent.detailSelection==detail && parent.selectedID==1101 && draft.control==nil,"Stale list/entry opened create over Task detail")
    for noGrant in [TaskDraftViewModel(),TaskDraftViewModel(port:ControlledTaskCreatePort(create:false))] {
        noGrant.bind(context);noGrant.open(expected:noGrant.entryControl);values(noGrant);noGrant.prepare(expected:noGrant.control);await noGrant.submit(noGrant.session.review!,expected:noGrant.control)
        try expect(!noGrant.canSubmit && noGrant.retainedAttemptCount==0,"Read context inferred CREATE actor authority")
    }
    return count
}
