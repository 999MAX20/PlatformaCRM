import Foundation
import CRMCore

@MainActor func checkTaskCreateReminder(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let ctx=TaskDraftContext(business:101,epoch:250),p=ControlledCreateDuePort(),m=TaskDraftViewModel(port:p)
    func base(_ m:TaskDraftViewModel) {m.open(expected:m.entryControl);m.update(.title," Task ",input:m.inputControl);m.update(.description," Note ",input:m.inputControl)}
    func dates(_ m:TaskDraftViewModel) {m.chooseDue(.setDate,input:m.inputControl);m.update(.dueAt,"2026-10-30T12:00:00Z",input:m.inputControl);m.chooseReminder(.setDate,input:m.inputControl);m.update(.reminderAt,"2026-10-30T11:00:00Z",input:m.inputControl)}
    m.bind(ctx);base(m);try expect(m.session.values.dueDate==TaskDraftDueDate() && m.session.values.reminderDate==TaskDraftDueDate(),"Creation dates defaulted or copied")
    m.chooseDue(.setDate,input:m.inputControl);m.update(.dueAt,"2026-10-30T12:00:00Z",input:m.inputControl);m.chooseReminder(.setDate,input:m.inputControl);m.prepare(expected:m.control)
    try expect(m.session.issues.contains(where:{$0.field == .reminderAt}) && m.session.values.reminderDate.raw.isEmpty && m.session.values.dueDate.raw=="2026-10-30T12:00:00Z","Due supplied an implicit reminder or reminder error changed due")
    let input=m.inputControl;m.update(.reminderAt,"2026-10-30T11:00:00Z",input:input);m.chooseReminder(.omit,input:input);m.update(.dueAt,"stale other field",input:input)
    try expect(m.session.values.dueDate.raw=="2026-10-30T12:00:00Z" && m.session.values.reminderDate.raw=="2026-10-30T11:00:00Z","Old mode callback changed either date raw")
    m.prepare(expected:m.control);let omitted=m.session.review!;try expect(omitted.preview.reminderAt==nil && omitted.preview.dueAt != nil,"Omitted reminder was copied from due/claimed null")
    m.back(expected:m.returnControl);m.chooseReminder(.setDate,input:m.inputControl);m.prepare(expected:m.control);let review=m.session.review!,send=m.control!;await m.submit(omitted,expected:send);let early=await p.recorded();try expect(early.isEmpty,"Old reminder mode review submitted current dates")
    let job=Task {await m.submit(review,expected:send)};await p.wait(0);let pending=m.control!,record=m.submission!;m.chooseReminder(.omit,input:m.inputControl);m.chooseDue(.omit,input:m.inputControl);m.askClear(expected:pending);await m.submit(review,expected:pending);m.acknowledge(expected:pending,record:record)
    let calls=await p.recorded();try expect(calls.count==1 && m.session.values==review.values && m.submission==record,"Pending complete dates changed or repeated")
    let body=try JSONSerialization.jsonObject(with:calls[0].preparedBody()!) as! [String:Any];try expect(Set(body.keys)==["business","title","description","priority","due_at","reminder_at"],"Create reminder body added mode/null/unrelated fields")
    // Existing callers without selected reminder evidence cannot confirm this review.
    let task=WorkTask(id:9101,title:review.preview.title,status:"open",priority:review.preview.priority,due_at:review.preview.dueAt,business:101,updated_at:"2026-10-30T12:00:00Z",description:review.preview.description,created_by:9001,created_at:"2026-10-30T12:00:00Z")
    await p.resolve(0,.response(status:201,task:task));await job.value;let unknown=m.submission!
    try expect(unknown.phase == .unknown && unknown.reminderAt==nil && unknown.attempt.review==review,"Due-only old caller proved reminder outcome")
    m.acknowledge(expected:m.control,record:unknown);m.bind(TaskDraftContext(business:101,epoch:251));try expect(m.submissionBlocked && m.submission==nil && m.retainedAttemptCount==1,"Matching read/new epoch recovered reminder outcome")
    let np=ControlledCreateDuePort(),noWrite=TaskDraftViewModel(port:np);noWrite.bind(ctx);base(noWrite);dates(noWrite);noWrite.askClear(expected:noWrite.control);let oldClear=noWrite.clearConfirmation!;noWrite.update(.reminderAt,"2038-01-19T03:14:08Z",input:noWrite.inputControl);noWrite.confirmClear(oldClear)
    try expect(noWrite.clearConfirmation==nil && noWrite.session.values.dueDate.raw=="2026-10-30T12:00:00Z" && noWrite.session.values.reminderDate.raw=="2038-01-19T03:14:08Z","Old reset erased independently changed date")
    noWrite.prepare(expected:noWrite.control);let nr=noWrite.session.review!,nc=noWrite.control!;let nj=Task {await noWrite.submit(nr,expected:nc)};await np.wait(0);await np.resolve(0,.rejectedWithoutWrite);await nj.value;noWrite.acknowledge(expected:noWrite.control,record:noWrite.submission!);await noWrite.submit(nr,expected:nc)
    try expect(noWrite.session.phase == .editing && noWrite.session.values==nr.values && noWrite.session.review==nil,"No-write lost a date raw/mode or reused review")
    let fixture=FixtureTaskCreatePort(directory:directory),transport=SearchTransport(directory),owner=TaskListViewModel(repository:APIReadRepository(transport:transport),createSubmission:fixture)
    await owner.load(business:101,epoch:252);let rows=owner.items,reads=await transport.recorded().count,v=owner.draft;base(v);dates(v);v.prepare(expected:v.control);await v.submit(v.session.review!,expected:v.control)
    let after=await transport.recorded().count;try expect(v.submission?.phase == .confirmed && v.submission?.reminderAt=="2026-10-30T11:00:00Z" && v.submission?.task?.due_at=="2026-10-30T12:00:00Z" && rows==owner.items && reads==after,"Paired date fixture changed source or failed independent correlation")
    let lp=ControlledCreateDuePort(),late=TaskDraftViewModel(port:lp);late.bind(ctx);base(late);dates(late);late.prepare(expected:late.control);let lj=Task {await late.submit(late.session.review!,expected:late.control)};await lp.wait(0)
    late.bind(TaskDraftContext(business:202,epoch:253));base(late);late.chooseReminder(.setDate,input:late.inputControl);late.update(.reminderAt,"2038-01-19T03:14:08Z",input:late.inputControl);let replacement=late.session.values,control=late.control;await lp.resolve(0,.unknown);await lj.value
    try expect(late.session.values==replacement && late.control==control && late.submission==nil,"Late dates result touched another Business form")
    return count
}
