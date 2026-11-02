import Foundation
import CRMCore

actor ControlledTaskAppointmentEditPort:SyntheticTaskAppointmentEditPort {
    nonisolated let grants:[SyntheticTaskAppointmentEditGrant]
    private var sent:[TaskAppointmentEditAttempt]=[],pending:[Int:CheckedContinuation<SyntheticTaskAppointmentEditOutcome,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    init(update:Bool=true) {grants=[SyntheticTaskAppointmentEditGrant(business:101,task:1101,actor:9001,update:update),SyntheticTaskAppointmentEditGrant(business:202,task:1201,actor:9002,update:update)]}
    func execute(_ attempt:TaskAppointmentEditAttempt) async throws -> SyntheticTaskAppointmentEditOutcome {let i=sent.count;sent.append(attempt);return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func lose(_ i:Int) {pending.removeValue(forKey:i)!.resume(throwing:ReadFailure.unavailable)}
    func resolve(_ i:Int,_ outcome:SyntheticTaskAppointmentEditOutcome) {pending.removeValue(forKey:i)!.resume(returning:outcome)}
    func calls()->[TaskAppointmentEditAttempt] {sent}
}
@MainActor func checkTaskAppointmentEdit(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),detail=try await repo.taskDetails(business:101,id:1101),context=TaskCommentContext(business:101,task:1101,epoch:1),read=TaskCommentRead(context:context,revision:1),source=TaskAppointmentEditSource(read:read,task:detail.task,original:detail.details.appointmentRead),port=ControlledTaskAppointmentEditPort(),reads=ControlledTaskAppointmentReads(directory),model=TaskAppointmentEditViewModel(port:port,appointments:reads)
    model.bind(source);let initialCalls=await reads.calls();try expect(model.canOpen && model.canPresent && model.draft.mode==nil && model.draft.choice==nil && model.draft.day.isEmpty && initialCalls.isEmpty,"Relation editor inferred mode/candidate/date/read/grant")
    model.open(expected:model.control);model.prepare(expected:model.control);try expect(model.review==nil && model.showsIssue,"Unset relation mode produced a null update")
    model.choose(.set,expected:model.control);let oldInput=model.inputControl!,oldControl=model.control!
    model.updateDay("2026-10-28",input:oldInput);model.choose(.clear,expected:model.control);let retained=model.draft
    model.updateDay("overwrite",input:oldInput);model.prepare(expected:oldControl);try expect(model.draft==retained && model.review==nil,"Old mode/day/review callback crossed editor visit")
    model.choose(.set,expected:model.control);let first=Task {await model.readAppointments(expected:model.control,child:model.picker.control)};await reads.waitList(0);let whileLoading=model.control!,loadingChild=model.picker.control!
    model.useAppointment(expected:whileLoading,child:loadingChild);model.back(expected:model.control);let afterBack=model.control!,saved=model.draft
    let page=try await repo.appointments(business:101,day:"2026-10-28");await reads.resolveList(0,page);await first.value
    try expect(!model.editing && model.control==afterBack && model.draft==saved && model.picker.context==nil,"Closed relation editor adopted late list or lost raw day/mode")
    model.open(expected:model.control);try expect(model.draft.day=="2026-10-28" && model.picker.day==model.draft.day && !model.picker.loaded && model.picker.items.isEmpty,"Reopened editor auto-read/defaulted/lost raw day")
    let list=Task {await model.readAppointments(expected:model.control,child:model.picker.control)};await reads.waitList(1);let pending=model.picker.control!;await reads.resolveList(1,page);await list.value
    await model.openAppointment(501,expected:model.control,child:pending);try expect(model.picker.selectedID==nil,"Pending list callback selected a ready row")
    await model.openAppointment(999999,expected:model.control,child:model.picker.control);try expect(model.picker.selectedID==nil,"Unprovided Appointment ID selected")
    let opening=Task {await model.openAppointment(501,expected:model.control,child:model.picker.control)};await reads.waitDetail(0);let pendingDetail=model.picker.control!
    model.useAppointment(expected:model.control,child:pendingDetail);try expect(model.draft.choice==nil,"Pending detail became selected Appointment")
    await reads.resolveDetail(0,try await repo.appointment(business:202,id:601));await opening.value;try expect(model.picker.failure == .invalidPayload && model.draft.choice==nil,"Foreign Appointment detail accepted")
    let retry=Task {await model.retryAppointment(expected:model.control,child:model.picker.control)};await reads.waitDetail(1);let staleChild=model.picker.control!;await reads.resolveDetail(1,try await repo.appointment(business:101,id:501));await retry.value
    model.useAppointment(expected:model.control,child:staleChild);try expect(model.draft.choice==nil,"Former pending detail callback adopted current result")
    model.useAppointment(expected:model.control,child:model.picker.control);let chosen=model.draft
    try expect(chosen.choice?.id==501 && chosen.choiceRead==source.read && chosen.day=="2026-10-28" && model.source==source,"Selected reference changed Task/source fields or lost current read")
    model.prepare(expected:model.control);let review=model.review!,reviewControl=model.control!
    try expect(review.draft==chosen && review.source==source && ((try JSONSerialization.jsonObject(with:review.change!.body()!)) as! [String:Any]).keys.count==1,"Review/body lost captured original/input")
    model.back(expected:model.control);try expect(model.review==nil && model.draft==chosen && model.editing,"Review Back lost selected Appointment/day/mode")
    model.choose(.clear,expected:model.control);model.prepare(expected:model.control);try expect(model.review?.change?.mode == .clear && ((try JSONSerialization.jsonObject(with:model.review!.change!.body()!)) as! [String:Any])["appointment"] is NSNull && model.draft.choice==chosen.choice,"Explicit clear changed/lost retained candidate or serialized another field")
    model.back(expected:model.control);model.choose(.set,expected:model.control);model.prepare(expected:model.control);try expect(model.review?.draft==chosen,"Switch back to set lost raw input/reference")
    await model.submit(expected:reviewControl);try expect(await port.calls().isEmpty,"Old review visit submitted a newer intent")
    let sending=Task {await model.submit(expected:model.control)};await port.wait(0);let attempt=await port.calls()[0],body=attempt.preparedBody()!,during=model.control!
    model.updateDay("2026-11-02",input:oldInput);model.choose(.clear,expected:during);model.askClear(expected:during);await model.submit(expected:during)
    try expect(await port.calls().count==1 && model.blocked && model.draft==chosen && model.clearConfirmation==nil,"Pending UPDATE edited/reset/replayed input")
    await port.lose(0);await sending.value;let retainedBody=model.submission!.attempt.preparedBody()
    try expect(model.submission?.phase == .unknown && retainedBody==body && model.submission?.attempt.review==attempt.review && model.draft==chosen,"Unknown UPDATE lost original/read/mode/candidate/day/body/attempt")
    let reread=TaskCommentRead(context:context,revision:2),matching=TaskAppointmentEditSource(read:reread,task:detail.task,original:.appointment(501));model.bind(matching)
    try expect(model.blocked && model.submission?.phase == .unknown && !model.canOpen && model.submission?.attempt.preparedBody()==body,"Matching reread became outcome proof or new attempt")
    model.bind(TaskAppointmentEditSource(read:TaskCommentRead(context:TaskCommentContext(business:101,task:1101,epoch:2),revision:3),task:detail.task,original:.appointment(501)))
    try expect(model.blocked && model.submission==nil && model.retainedAttemptCount==1 && !model.canOpen,"New epoch replayed old Task UPDATE")
    let other=try await repo.taskDetails(business:202,id:1201);model.bind(TaskAppointmentEditSource(read:TaskCommentRead(context:TaskCommentContext(business:202,task:1201,epoch:2),revision:4),task:other.task,original:other.details.appointmentRead));try expect(model.canOpen && !model.blocked && model.draft.mode==nil,"One unknown Task globally blocked independent Business/Task")
    let fresh=TaskAppointmentEditViewModel(port:ControlledTaskAppointmentEditPort(),appointments:repo);fresh.bind(source);fresh.open(expected:fresh.control);fresh.choose(.clear,expected:fresh.control);fresh.askClear(expected:fresh.control);let question=fresh.clearConfirmation!;fresh.dismissClear(question);fresh.choose(.set,expected:fresh.control);fresh.confirmClear(question);try expect(fresh.draft.mode == .set,"Old input reset dialog cleared new intent")
    fresh.askClear(expected:fresh.control);fresh.confirmClear(fresh.clearConfirmation!);try expect(fresh.draft==TaskAppointmentEditDraft() && fresh.picker.day.isEmpty && fresh.source==source,"Local draft reset altered original or kept implicit null/choice/date")
    let unknown=TaskAppointmentEditSource(read:read,task:detail.task,original:.unknown);fresh.bind(unknown);try expect(fresh.canPresent && !fresh.canOpen && fresh.source?.original == .unknown,"Unknown original became no relation or editable null")
    let noGrant=TaskAppointmentEditViewModel(port:ControlledTaskAppointmentEditPort(update:false),appointments:repo);noGrant.bind(source);try expect(!noGrant.canPresent && !noGrant.canOpen,"Original/picker GET granted UPDATE")
    let confirmed=TaskAppointmentEditViewModel(port:FixtureTaskAppointmentEditPort(directory:directory),appointments:repo);confirmed.bind(source);confirmed.open(expected:confirmed.control);confirmed.choose(.clear,expected:confirmed.control);confirmed.prepare(expected:confirmed.control);await confirmed.submit(expected:confirmed.control);let record=confirmed.submission!;try expect(record.phase == .confirmed && record.result?.value==nil && confirmed.source==source,"Explicit fake clear did not confirm separately or optimistically changed source")
    confirmed.acknowledge(expected:confirmed.control,record:record);try expect(confirmed.consumed && !confirmed.canOpen && confirmed.source==source,"Confirmed read repeated without fresh Task source")
    // Task-list integration: one editor, same-Task unknown barrier, separate command/read injection.
    let ownerPort=ControlledTaskAppointmentEditPort(),owner=TaskListViewModel(repository:repo,commentSource:FixtureTaskCommentDraftSource(directory:directory),dateEditSubmission:FixtureTaskDateEditPort(directory:directory),titleEditSubmission:FixtureTaskTitleEditPort(directory:directory),appointmentEditSubmission:ownerPort,appointmentEditReads:repo)
    await owner.load(business:101,epoch:1);await owner.open(id:1101);let action=owner.appointmentEdit!,ownerControl=owner.control!,dateControl=owner.dateEdit!.control!
    try expect(action.source?.original == .notSet && action.canOpen && owner.appointmentEditCurrent(ownerControl),"Task detail did not bind same-response original + separate fake UPDATE context")
    owner.openAppointmentEdit(action.control,parent:ownerControl);owner.openDateEdit(dateControl,parent:ownerControl)
    try expect(action.editing && owner.dateEdit?.editing==false && !owner.dateEditCurrent(ownerControl) && !owner.titleEditCurrent(ownerControl),"Sibling editor bypassed active relation input")
    action.choose(.clear,expected:action.control);action.prepare(expected:action.control);let submit=Task {await action.submit(expected:action.control)};await ownerPort.wait(0);await ownerPort.lose(0);await submit.value
    let rows=owner.items,total=owner.total,sourceDetail=owner.detail;try expect(owner.taskActionOccupied && !owner.dateEditCurrent(owner.control) && !owner.titleEditCurrent(owner.control) && action.submission?.phase == .unknown,"Unknown relation write did not occupy Task action lane")
    if let commentRead=owner.comment?.session.read {owner.openComment(commentRead)}
    try expect(owner.comment?.session.selection==nil && owner.items==rows && owner.total==total && owner.detail==sourceDetail,"Unknown permitted raw comment bypass/optimistic Task mutation")
    await owner.load(business:101,epoch:2);await owner.open(id:1101);try expect(owner.taskActionOccupied && !owner.hasHiddenRetainedAction && action.canPresent && action.blocked && owner.appointmentEditCurrent(owner.control) && !owner.dateEditCurrent(owner.control) && !owner.titleEditCurrent(owner.control) && action.submission==nil && action.retainedAttemptCount==1,"Task-list epoch hid or bypassed retained unknown barrier")
    let defaultOwner=TaskListViewModel(repository:repo,commentSource:FixtureTaskCommentDraftSource(directory:directory));await defaultOwner.load(business:101,epoch:1);await defaultOwner.open(id:1101);try expect(defaultOwner.appointmentEdit==nil,"Default GET consumer invented command/read port")
    // Parent source/mode visit and child input visit must both remain current.
    let rawReads=ControlledTaskAppointmentReads(directory),raw=TaskAppointmentEditViewModel(port:ControlledTaskAppointmentEditPort(),appointments:rawReads)
    raw.bind(source);raw.open(expected:raw.control);raw.choose(.set,expected:raw.control);let rawInput=raw.inputControl!,rawRead=raw.picker.control!
    for value in ["2","20","2026-10-28"] {raw.updateDay(value,input:rawInput);try expect(raw.draft.day==value && raw.inputControl==rawInput,"Parent partial editor dropped consecutive date callbacks")}
    await raw.readAppointments(expected:raw.control,child:rawRead);try expect(await rawReads.calls().isEmpty,"Parent raw input relaxed child read generation")
    let rawLoad=Task {await raw.readAppointments(expected:raw.control,child:raw.picker.control)};await rawReads.waitList(0)
    raw.updateDay("overwrite",input:rawInput);try expect(raw.inputControl==nil && raw.draft.day=="2026-10-28","Parent pending read accepted raw input")
    await rawReads.resolveList(0,page);await rawLoad.value;raw.updateDay("overwrite",input:rawInput);try expect(raw.draft.day=="2026-10-28" && raw.inputControl != rawInput,"Parent completed read revived old input")
    let beforeMode=raw.inputControl!;raw.choose(.clear,expected:raw.control);raw.choose(.set,expected:raw.control);raw.updateDay("overwrite",input:beforeMode);try expect(raw.draft.day=="2026-10-28" && raw.inputControl != beforeMode,"Mode round-trip revived parent input visit")
    let beforeSource=raw.inputControl!;raw.bind(TaskAppointmentEditSource(read:reread,task:detail.task,original:.notSet));raw.open(expected:raw.control);raw.choose(.set,expected:raw.control);raw.updateDay("overwrite",input:beforeSource);try expect(raw.draft.day=="2026-10-28" && raw.draft.choiceRead==nil && raw.inputControl != beforeSource,"Fresh Task read accepted old raw source input")
    return count
}
