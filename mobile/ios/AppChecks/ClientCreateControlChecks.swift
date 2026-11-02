import Foundation
import CRMCore

@MainActor func checkClientCreateControls(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let context=ClientDraftContext(business:101,epoch:100),port=ControlledClientCreatePort(),model=ClientDraftViewModel(port:FixtureClientCreatePort(directory:directory))
    func values(_ m:ClientDraftViewModel,_ name:String="  Manual client  \n") {let input=m.inputControl;for (field,value) in [(ClientDraftField.fullName,name),(.phone,"  +7 123\n"),(.email,"alpha@example.invalid"),(.source,"telegram"),(.notes,"  Manual notes  \n")] {m.update(field,value,input:input)}}
    func response(_ a:ClientCreateAttempt)->SyntheticClientCreateOutcome {let v=a.review.preview;return .response(status:201,client:ClientContact(id:87001,title:nil,phone:v.phone,email:v.email,business:a.authorization.context.business,full_name:v.fullName,source:v.source,notes:v.notes,created_at:"2026-10-30T12:00:00Z",updated_at:"2026-10-30T12:00:00Z"))}
    model.open(expected:nil);try expect(model.control==nil,"Nil entry opened create composer")
    model.bind(context);let entry=model.entryControl!;model.open(expected:entry);let initial=model.control!,input=model.inputControl!
    model.open(expected:entry);model.prepare(expected:initial)
    try expect(model.control==initial && model.session.issues.contains(where:{$0.field == .fullName && $0.problem == .name}),"Duplicate entry/required validation lost editor visit")
    model.update(.fullName,String(repeating:"x",count:256),input:input);model.update(.phone,String(repeating:"1",count:33),input:input);model.update(.email,"bad address",input:input);model.update(.notes,"ab\0cd",input:input);model.update(.source,"unsupported",input:input);model.prepare(expected:initial)
    try expect(model.control==initial && model.inputControl==input && Set(model.session.issues.map(\.field))==Set([ClientDraftField.fullName,.phone,.email,.source,.notes]),"Field validation dropped raw input or changed visit")
    values(model);model.update(.email," alpha@example.invalid ",input:input);model.prepare(expected:initial)
    try expect(model.control==initial && model.session.issues.contains(where:{$0.field == .email}),"Raw web email validation was silently replaced by preview trimming")
    model.update(.email,"alpha@example.invalid",input:input);let raw=model.session.values;model.bind(context)
    try expect(model.inputControl==input && model.session.values==raw,"Same context bind reset continuous input")
    model.prepare(expected:initial);let review=model.session.review!,oldReview=model.control!
    model.update(.source,"instagram",input:input);model.back(expected:ClientDraftReturnControl(editor:initial,clear:nil))
    try expect(model.control==oldReview && model.session.review==review && review.values==raw && review.preview.fullName=="Manual client" && review.preview.notes=="Manual notes","Old field/editor action changed exact preview")
    model.back(expected:model.returnControl);model.prepare(expected:model.control);let currentReview=model.control!
    try expect(model.session.review==review && currentReview != oldReview,"Identical field review lost distinct UI visit")
    await model.submit(review,expected:oldReview);try expect(model.retainedAttemptCount==0,"Old identical-review Submit created an attempt")
    model.back(expected:model.returnControl);let editing=model.control!,typing=model.inputControl!
    model.askClear(expected:editing);let question=model.clearConfirmation!;model.update(.notes,"New own description",input:typing);model.confirmClear(question)
    try expect(model.clearConfirmation==nil && model.session.values.notes=="New own description","Old clear erased a newer field edit")
    model.askClear(expected:editing);let previous=model.clearConfirmation!;model.dismissClear(previous);model.askClear(expected:editing);let active=model.clearConfirmation!
    model.dismissClear(previous);model.confirmClear(previous);model.back(expected:ClientDraftReturnControl(editor:editing,clear:nil))
    try expect(model.clearConfirmation==active && model.control==editing,"Old dialog/Back consumed replacement consent")
    model.back(expected:model.returnControl);model.close(expected:model.returnControl);model.open(expected:entry)
    try expect(model.control==nil && model.session.values.notes=="New own description","Close erased own fields or old entry reopened composer")
    model.open(expected:model.entryControl);model.confirmClear(active);try expect(model.session.values.notes=="New own description","Old closed-composer consent erased reopened input")
    model.askClear(expected:model.control);model.confirmClear(model.clearConfirmation!)
    try expect(model.control==nil && model.session.values==ClientDraftValues(),"Current explicit clear failed to restore existing empty values/manual source")
    let m=ClientDraftViewModel(port:port);m.bind(context);m.open(expected:m.entryControl);values(m);m.prepare(expected:m.control)
    let submitControl=m.control!,submitReview=m.session.review!;m.askClear(expected:submitControl);let oldClear=m.clearConfirmation!
    let job=Task {await m.submit(submitReview)};await port.wait(0);let pending=m.control!,record=m.submission!
    m.confirmClear(oldClear);m.askClear(expected:pending);m.update(.fullName,"overwrite",input:ClientDraftInputControl(control:submitControl));await m.submit(submitReview,expected:submitControl)
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
    m.bind(ClientDraftContext(business:101,epoch:101));m.open(expected:m.entryControl)
    try expect(m.submission==nil && m.submissionBlocked && m.inputControl==nil && m.retainedAttemptCount==2,"New epoch exposed or released prior create attempt")
    // A late other-Business completion cannot revoke the current local input visit.
    let otherPort=ControlledClientCreatePort(),other=ClientDraftViewModel(port:otherPort);other.bind(context);other.open(expected:other.entryControl);values(other);other.prepare(expected:other.control)
    let olderReview=other.session.review!,olderControl=other.control!,older=Task {await other.submit(olderReview,expected:olderControl)};await otherPort.wait(0)
    other.bind(ClientDraftContext(business:202,epoch:102));other.open(expected:other.entryControl);let otherInput=other.inputControl!,otherControl=other.control!
    other.update(.fullName,"Other Business raw",input:otherInput);await otherPort.resolve(0,.unknown);await older.value
    try expect(other.control==otherControl && other.inputControl==otherInput && other.session.values.fullName=="Other Business raw" && !other.submissionBlocked && other.retainedAttemptCount==1,"Foreign completion revoked current unrelated form")
    // List-only UI controls cannot switch a current draft/search/profile; raw switches remain trusted.
    let transport=SearchTransport(directory),parentPort=ControlledClientCreatePort(),parent=ClientDirectoryViewModel(repository:APIReadRepository(transport:transport),createSubmission:parentPort)
    await parent.load(business:101,epoch:100);let list=parent.listControl!,rows=parent.items,total=parent.total,before=await transport.recorded(),draft=parent.draft,opening=parent.draft.entryControl!
    try expect(parent.openDraft(expected:opening,list:list),"Current list entry failed to open Client composer");values(draft)
    let currentParent=parent.control!,forged=ClientDirectoryListControl(parent:parent.control!),composer=draft.control!
    parent.search("hidden search",list:forged);await parent.retry(list:forged)
    try expect(!parent.openSearch(list:forged) && !parent.open(id:701,list:forged) && !parent.openDraft(expected:opening,list:forged),"List callback switched/reopened current composer")
    let afterHidden=await transport.recorded();try expect(parent.control==currentParent && parent.listControl==nil && parent.selectedID==nil && parent.query.isEmpty && afterHidden==before && draft.control==composer,"Hidden list actions changed active Client draft or transport")
    draft.prepare(expected:composer);let prepared=draft.session.review!,preparedControl=draft.control!,creating=Task {await draft.submit(prepared,expected:preparedControl)};await parentPort.wait(0)
    let attempt=await parentPort.recorded()[0];await parentPort.resolve(0,response(attempt));await creating.value;let result=draft.submission!,resultControl=draft.control!
    draft.acknowledge(expected:preparedControl,record:result);try expect(draft.submissionBlocked,"Old submit control acknowledged later confirmed Client result")
    draft.acknowledge(expected:resultControl,record:result);let afterCreate=await transport.recorded()
    try expect(draft.control==nil && draft.session.values==ClientDraftValues() && draft.retainedAttemptCount==1 && parent.items==rows && parent.total==total && afterCreate==before,"Fake Client success changed Directory/read or failed explicit local acknowledgement")
    try expect(!parent.open(id:701,list:list) && !parent.openSearch(list:list) && !parent.openDraft(expected:opening,list:list),"Pre-composer list/entry became valid after return")
    let searchList=parent.listControl!;try expect(parent.openSearch(list:searchList),"Current list failed to open manual search")
    let search=parent.serverSearch!.session.selection!,searchParent=parent.control!
    try expect(!parent.openDraft(expected:draft.entryControl,list:ClientDirectoryListControl(parent:searchParent)) && parent.serverSearch?.session.selection==search,"Create list entry closed current search")
    // Preserve the explicitly trusted current-parent switch behavior from source158.
    try expect(parent.openDraft(expected:searchParent) && parent.serverSearch?.session.selection==nil && draft.control != nil,"Trusted search/create switch semantics changed")
    let draftParent=parent.control!;try expect(parent.openSearch(expected:draftParent) && draft.control==nil,"Trusted create/search switch lost own buffer semantics")
    let endSearch=parent.control!;try expect(parent.back(expected:endSearch),"Current trusted search Back failed")
    let profileList=parent.listControl!;try expect(parent.open(id:701,list:profileList),"Current list profile entry failed")
    let profileParent=parent.control!;try expect(!parent.openSearch(list:ClientDirectoryListControl(parent:profileParent)) && !parent.openDraft(expected:draft.entryControl,list:ClientDirectoryListControl(parent:profileParent)) && parent.selectedID==701,"List control overrode independently selected Client profile")
    let readsAfterSwitches=await transport.recorded();try expect(readsAfterSwitches==before,"Local list/draft/search switches issued a read")
    for noGrant in [ClientDraftViewModel(),ClientDraftViewModel(port:ControlledClientCreatePort(create:false))] {
        noGrant.bind(context);noGrant.open(expected:noGrant.entryControl);values(noGrant);noGrant.prepare(expected:noGrant.control);await noGrant.submit(noGrant.session.review!,expected:noGrant.control)
        try expect(!noGrant.canSubmit && noGrant.retainedAttemptCount==0,"Read context inferred CREATE actor authority")
    }
    return count
}
