import Foundation
import CRMCore

actor ControlledTaskDescriptionEditPort:SyntheticTaskDescriptionEditPort {
    nonisolated let grants:[SyntheticTaskDescriptionEditGrant]
    private var attempts:[TaskDescriptionEditAttempt]=[]
    private var pending:[Int:CheckedContinuation<SyntheticTaskDescriptionEditOutcome,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    init(_ grants:[SyntheticTaskDescriptionEditGrant]) {self.grants=grants}
    func execute(_ attempt:TaskDescriptionEditAttempt) async throws -> SyntheticTaskDescriptionEditOutcome {let i=attempts.count;attempts.append(attempt);return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ value:SyntheticTaskDescriptionEditOutcome) {pending.removeValue(forKey:i)!.resume(returning:value)}
    func fail(_ i:Int) {pending.removeValue(forKey:i)!.resume(throwing:ReadFailure.unavailable)}
    func recorded()->[TaskDescriptionEditAttempt] {attempts}
}
@MainActor func checkTaskDescriptionEdit(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func detail(_ b:Int=101,_ id:Int=1101) throws -> TaskDetails {try JSONDecoder().decode(TaskDetails.self,from:Data(contentsOf:directory.appendingPathComponent("task-\(b)-\(id).json")))}
    func source(_ d:TaskDetails,epoch:Int=210,revision:Int=1)->TaskDescriptionEditSource {TaskDescriptionEditSource(read:TaskCommentRead(context:TaskCommentContext(business:d.business,task:d.task.id,epoch:epoch),revision:revision),task:d.task)}
    let original=try detail(),initial=source(original),fixture=FixtureTaskDescriptionEditPort(directory:directory),port=ControlledTaskDescriptionEditPort(fixture.grants),m=TaskDescriptionEditViewModel(port:port)
    m.bind(initial);m.open(expected:m.control);m.prepare(expected:m.control);try expect(m.raw.isEmpty && m.review==nil && m.showsIssue,"Title defaulted from bounded/other source")
    m.choose(.replaceText,expected:m.control);let input=m.inputControl;m.update("  e\u{0301}  ",input:input);m.update(" \u{FEFF}New title  ",input:input);try expect(m.raw==" \u{FEFF}New title  ","Continuous title input control became stale")
    m.prepare(expected:m.control);let old=m.control!;try expect(m.review?.value.description=="\u{FEFF}New title" && m.review?.value.raw==m.raw,"Review lost raw or normalized title")
    m.back(expected:old);m.update("stale",input:input);await m.submit(expected:old);let callsAfterBack=await port.recorded();try expect(m.review==nil && m.raw==" \u{FEFF}New title  " && callsAfterBack.isEmpty,"Old raw/review callback acted after Back")
    // Swift String equivalence must not make a stale raw control match another wire spelling.
    m.update("e\u{0301}",input:m.inputControl);let decomposed=m.control!;m.update("é",input:m.inputControl);m.prepare(expected:decomposed);try expect(m.review==nil && !decomposed.raw.utf8.elementsEqual(m.raw.utf8),"Canonical-equivalent old raw control acted")
    m.askClear(expected:m.control);let oldReset=m.clearConfirmation!;m.dismissClear(oldReset);m.update("Keep replacement",input:m.inputControl);m.confirmClear(oldReset);try expect(m.raw=="Keep replacement","Old title reset erased newer raw")
    m.askClear(expected:m.control);m.confirmClear(m.clearConfirmation!);m.prepare(expected:m.control);try expect(m.raw.isEmpty && m.review==nil && m.showsIssue,"Local title reset became empty/null command")
    m.choose(.replaceText,expected:m.control);let exact="\u{001C}\u{FEFF} New title \u{FEFF}\u{001C}"
    m.update(exact,input:m.inputControl);m.prepare(expected:m.control);let send=m.control!,review=m.review!,job=Task {await m.submit(expected:send)};await port.wait(0);let pending=m.control!,record=m.submission!
    m.update("lost",input:m.inputControl);m.askClear(expected:pending);m.back(expected:pending);m.acknowledge(expected:pending,record:record);await m.submit(expected:send);await m.submit(expected:pending);let attempts=await port.recorded()
    try expect(m.raw.utf8.elementsEqual(exact.utf8) && m.submission==record && attempts.count==1 && attempts[0].review==review,"Pending title lost raw/normalization/source or repeated")
    await port.fail(0);await job.value;let unknown=m.submission!;m.bind(source(original,epoch:211,revision:2));try expect(m.blocked && m.submission==nil && m.raw.isEmpty && !m.canOpen,"New epoch proved title outcome")
    m.bind(initial);m.acknowledge(expected:m.control,record:unknown);try expect(m.blocked && unknown.attempt.review==review,"Unknown title lost raw/review or acknowledged")
    let ok=TaskDescriptionEditViewModel(port:fixture);ok.bind(initial);ok.open(expected:ok.control);ok.choose(.replaceText,expected:ok.control);ok.update(exact,input:ok.inputControl);ok.prepare(expected:ok.control);let prior=ok.control!;await ok.submit(expected:prior);let accepted=ok.submission!
    try expect(accepted.phase == .confirmed && accepted.result?.description.utf8.elementsEqual(review.value.description.utf8)==true && ok.source==initial,"Fake title normalized twice or changed GET")
    ok.acknowledge(expected:ok.control,record:accepted);ok.open(expected:ok.control);ok.choose(.replaceText,expected:ok.control);await ok.submit(expected:prior);try expect(ok.consumed && !ok.editing && ok.raw.isEmpty && ok.retainedAttemptCount==1,"Confirmed title reused read")
    let noWrite=TaskDescriptionEditViewModel(port:fixture);noWrite.bind(source(try detail(101,1401)));noWrite.open(expected:noWrite.control);noWrite.choose(.replaceText,expected:noWrite.control);noWrite.update("  Keep exact raw  ",input:noWrite.inputControl);noWrite.prepare(expected:noWrite.control);let rc=noWrite.control!;await noWrite.submit(expected:rc);let rr=noWrite.submission!;noWrite.acknowledge(expected:noWrite.control,record:rr);await noWrite.submit(expected:rc)
    try expect(noWrite.editing && noWrite.raw=="  Keep exact raw  " && noWrite.review==nil && noWrite.retainedAttemptCount==1,"No-write title repeated/lost raw")
    let lp=ControlledTaskDescriptionEditPort(fixture.grants),late=TaskDescriptionEditViewModel(port:lp);late.bind(initial);late.open(expected:late.control);late.choose(.replaceText,expected:late.control);late.update("First",input:late.inputControl);late.prepare(expected:late.control);let lj=Task {await late.submit(expected:late.control)};await lp.wait(0)
    late.bind(source(try detail(202,1201),epoch:212));late.open(expected:late.control);late.choose(.replaceText,expected:late.control);late.update("  Other owner  ",input:late.inputControl);let replacement=late.control,a=await lp.recorded()[0];await lp.resolve(0,try await fixture.execute(a));await lj.value
    try expect(late.control==replacement && late.raw=="  Other owner  " && late.submission==nil,"Late title result touched replacement raw/owner")
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),plain=TaskListViewModel(repository:repo),unverified=TaskListViewModel(repository:repo,descriptionEditSubmission:fixture)
    await unverified.load(business:101,epoch:213);await unverified.open(id:1101);try expect(plain.descriptionEdit==nil && unverified.descriptionEdit?.source==nil,"Default/GET inferred title UPDATE")
    let transport=SearchTransport(directory),flow=TaskListViewModel(repository:APIReadRepository(transport:transport),commentSource:FixtureTaskCommentDraftSource(directory:directory),priorityEditSubmission:FixtureTaskPriorityEditPort(directory:directory),descriptionEditSubmission:fixture)
    await flow.load(business:101,epoch:214);await flow.open(id:1101);let v=flow.descriptionEdit!,before=flow.detail!,items=flow.items,reads=await transport.recorded().count
    let oldEntry=v.control;flow.openPriorityEdit(flow.priorityEdit?.control,parent:flow.control);flow.priorityEdit?.back(expected:flow.priorityEdit?.control);flow.openDescriptionEdit(oldEntry,parent:flow.control);try expect(!v.editing,"Old title entry survived priority visit")
    flow.openDescriptionEdit(v.control,parent:flow.control);v.choose(.replaceText,expected:v.control);v.update("  Reviewed title  ",input:v.inputControl);try expect(!flow.priorityEditCurrent(flow.control),"Title editor failed peer ownership")
    flow.openComment(v.source!.read);if let c=flow.comment {c.close(expected:c.returnControl)};flow.openDescriptionEdit(v.control,parent:flow.control);try expect(v.raw=="  Reviewed title  ","Comment return lost title raw")
    v.prepare(expected:v.control);let body=try JSONSerialization.jsonObject(with:v.review!.value.body()!) as! [String:Any];try expect(Set(body.keys)==["description"] && body["description"] as? String=="Reviewed title","Title resubmitted untouched/bounded description")
    await v.submit(expected:v.control);let afterReads=await transport.recorded().count;try expect(v.submission?.phase == .confirmed && flow.detail==before && flow.items==items && afterReads==reads,"Fake title changed GET or caused read/write")
    v.acknowledge(expected:v.control,record:v.submission!);flow.openPriorityEdit(flow.priorityEdit?.control,parent:flow.control);try expect(flow.priorityEdit?.editing==false && flow.taskActionOccupied,"Consumed title bypassed priority")
    // Retained unknown for description blocks every existing peer after owner replacement.
    let qp=ControlledTaskDescriptionEditPort(fixture.grants),quarantined=TaskListViewModel(repository:repo,commentSource:FixtureTaskCommentDraftSource(directory:directory),completeSubmission:FixtureTaskCompletePort(directory:directory),selfAssignSubmission:FixtureTaskSelfAssignPort(directory:directory),startSubmission:FixtureTaskStartPort(directory:directory),reopenSubmission:FixtureTaskReopenPort(directory:directory),watcherSubmission:FixtureTaskWatcherPort(directory:directory),undoCancelSubmission:FixtureTaskUndoCancelPort(directory:directory),snoozeSubmission:FixtureTaskSnoozePort(directory:directory),targetAssignSubmission:FixtureTaskAssignPort(directory:directory),dateEditSubmission:FixtureTaskDateEditPort(directory:directory),priorityEditSubmission:FixtureTaskPriorityEditPort(directory:directory),titleEditSubmission:FixtureTaskTitleEditPort(directory:directory),descriptionEditSubmission:qp)
    await quarantined.load(business:101,epoch:215);await quarantined.open(id:1101);let q=quarantined.descriptionEdit!;quarantined.openDescriptionEdit(q.control,parent:quarantined.control);q.choose(.replaceText,expected:q.control);q.update("  Retained raw  ",input:q.inputControl);q.prepare(expected:q.control);let qj=Task {await q.submit(expected:q.control)};await qp.wait(0);await qp.resolve(0,.unknown);await qj.value
    await quarantined.load(business:101,epoch:216);await quarantined.open(id:1101);let parent=quarantined.control
    try expect(quarantined.taskActionOccupied && q.submission==nil && q.canPresent && q.retainedAttemptCount==1,"Matching read released title quarantine")
    for current in [quarantined.completionCurrent(parent),quarantined.selfAssignmentCurrent(parent),quarantined.startCurrent(parent),quarantined.reopenCurrent(parent),quarantined.watcherCurrent(parent),quarantined.undoCancelCurrent(parent),quarantined.snoozeCurrent(parent),quarantined.targetAssignCurrent(parent),quarantined.dateEditCurrent(parent),quarantined.priorityEditCurrent(parent),quarantined.titleEditCurrent(parent)] {try expect(!current,"Unknown title bypassed existing peer")}
    let dp=ControlledTaskDateEditPort(FixtureTaskDateEditPort(directory:directory).grants),opposite=TaskListViewModel(repository:repo,commentSource:FixtureTaskCommentDraftSource(directory:directory),dateEditSubmission:dp,descriptionEditSubmission:fixture)
    await opposite.load(business:101,epoch:217);await opposite.open(id:1101);let d=opposite.dateEdit!;opposite.openDateEdit(d.control,parent:opposite.control);d.select(.dueAt,expected:d.control);d.choose(.clearDate,expected:d.control);d.prepare(expected:d.control);let dj=Task {await d.submit(expected:d.control)};await dp.wait(0);await dp.resolve(0,.unknown);await dj.value
    await opposite.load(business:101,epoch:218);await opposite.open(id:1101);opposite.openDescriptionEdit(opposite.descriptionEdit?.control,parent:opposite.control)
    try expect(opposite.descriptionEdit?.editing==false && opposite.taskActionOccupied && !opposite.descriptionEditCurrent(opposite.control),"Unknown date bypassed independent title")
    let clear=TaskDescriptionEditViewModel(port:fixture);clear.bind(initial);clear.open(expected:clear.control);clear.choose(.replaceText,expected:clear.control);clear.update("Unsent replacement",input:clear.inputControl);let staleInput=clear.inputControl
    clear.choose(.clearText,expected:clear.control);clear.update("stale",input:staleInput);clear.prepare(expected:clear.control)
    try expect(clear.review?.value.mode == .clearText && clear.review?.value.description=="" && clear.raw=="Unsent replacement","Clear intention lost mode/raw or accepted old input")
    let nullBody=try JSONSerialization.jsonObject(with:clear.review!.value.body()!) as! [String:Any];try expect(Set(nullBody.keys)==["description"] && nullBody["description"] as? String=="","Explicit description clear became null or whole DTO")
    await clear.submit(expected:clear.control);try expect(clear.submission?.phase == .confirmed && clear.submission?.result?.description=="" && clear.source==initial,"Explicit empty-string clear changed source or failed correlation")
    return count
}
