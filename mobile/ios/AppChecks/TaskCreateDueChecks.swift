import Foundation
import CRMCore

actor ControlledCreateDuePort:SyntheticTaskCreatePort {
    nonisolated let grants=[SyntheticTaskCreateGrant(business:101,actor:9001,create:true),SyntheticTaskCreateGrant(business:202,actor:9002,create:true)]
    private var attempts:[TaskCreateAttempt]=[]
    private var pending:[Int:CheckedContinuation<SyntheticTaskCreateOutcome,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    func execute(_ attempt:TaskCreateAttempt) async throws -> SyntheticTaskCreateOutcome {let i=attempts.count;attempts.append(attempt);return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ value:SyntheticTaskCreateOutcome) {pending.removeValue(forKey:i)!.resume(returning:value)}
    func recorded()->[TaskCreateAttempt] {attempts}
}
@MainActor func checkTaskCreateDue(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let ctx=TaskDraftContext(business:101,epoch:240),p=ControlledCreateDuePort(),m=TaskDraftViewModel(port:p)
    func base(_ m:TaskDraftViewModel) {m.open(expected:m.entryControl);m.update(.title," Task ",input:m.inputControl);m.update(.description," Note ",input:m.inputControl)}
    m.bind(ctx);base(m);try expect(m.session.values.dueDate.mode == .omit && m.session.values.dueDate.raw.isEmpty,"Create invented date")
    m.chooseDue(.setDate,input:m.inputControl);m.prepare(expected:m.control);try expect(m.session.phase == .editing && m.session.issues.contains(where:{$0.field == .dueAt}),"Empty set date became implicit omission/null")
    let input=m.inputControl;m.update(.dueAt,"2000-02-29T00:00:00Z",input:input);m.update(.dueAt,"2026-10-30T17:00:00+05:00",input:input);let raw=m.session.values
    m.chooseDue(.omit,input:input);m.update(.dueAt,"stale date",input:input);try expect(m.session.values.dueDate.raw==raw.dueDate.raw && m.session.values.dueDate.mode == .omit,"Old date mode input changed omitted buffer")
    m.prepare(expected:m.control);let omitted=m.session.review!;try expect(omitted.preview.dueAt==nil && omitted.values.dueDate.raw==raw.dueDate.raw,"Omit discarded raw or previewed a server default")
    m.back(expected:m.returnControl);m.chooseDue(.setDate,input:m.inputControl);m.prepare(expected:m.control);let review=m.session.review!,send=m.control!;await m.submit(omitted,expected:send);let early=await p.recorded();try expect(early.isEmpty,"Old omitted review submitted selected date")
    let job=Task {await m.submit(review,expected:send)};await p.wait(0);let pending=m.control!,record=m.submission!;m.chooseDue(.omit,input:m.inputControl);m.update(.dueAt,"lost",input:m.inputControl);m.askClear(expected:pending);await m.submit(review,expected:pending);m.acknowledge(expected:pending,record:record)
    let calls=await p.recorded();try expect(calls.count==1 && m.session.values==review.values && m.submission==record,"Pending date changed/repeated/lost complete form")
    let body=try JSONSerialization.jsonObject(with:calls[0].preparedBody()!) as! [String:Any];try expect(Set(body.keys)==["business","title","description","priority","due_at"] && body["due_at"] as? String==raw.dueDate.raw,"Create date body added fields/null/default")
    await p.resolve(0,.unknown);await job.value;let unknown=m.submission!;m.acknowledge(expected:m.control,record:unknown);m.bind(TaskDraftContext(business:101,epoch:241));try expect(m.submissionBlocked && m.submission==nil && unknown.attempt.review.values.dueDate==review.values.dueDate && m.retainedAttemptCount==1,"New owner/reread lost selected create date attempt")
    let np=ControlledCreateDuePort(),noWrite=TaskDraftViewModel(port:np);noWrite.bind(ctx);base(noWrite);noWrite.chooseDue(.setDate,input:noWrite.inputControl);noWrite.update(.dueAt,"2000-02-29T00:00:00Z",input:noWrite.inputControl);noWrite.prepare(expected:noWrite.control);let nr=noWrite.session.review!,nc=noWrite.control!;let nj=Task {await noWrite.submit(nr,expected:nc)};await np.wait(0);await np.resolve(0,.rejectedWithoutWrite);await nj.value;noWrite.acknowledge(expected:noWrite.control,record:noWrite.submission!);await noWrite.submit(nr,expected:nc)
    try expect(noWrite.session.phase == .editing && noWrite.session.values==nr.values && noWrite.session.review==nil,"No-write date lost raw/mode or reused review")
    let fixture=FixtureTaskCreatePort(directory:directory),transport=SearchTransport(directory),owner=TaskListViewModel(repository:APIReadRepository(transport:transport),createSubmission:fixture)
    await owner.load(business:101,epoch:242);let rows=owner.items,reads=await transport.recorded().count,v=owner.draft;v.open(expected:v.entryControl);v.update(.title," Task ",input:v.inputControl);v.chooseDue(.setDate,input:v.inputControl);v.update(.dueAt,"2000-02-29T00:00:00Z",input:v.inputControl);v.prepare(expected:v.control);await v.submit(v.session.review!,expected:v.control)
    let after=await transport.recorded().count;try expect(v.submission?.phase == .confirmed && v.submission?.task?.due_at=="2000-02-29T00:00:00Z" && owner.items==rows && reads==after,"Date fake failed exact selected result or mutated source/read")
    let lp=ControlledCreateDuePort(),late=TaskDraftViewModel(port:lp);late.bind(ctx);base(late);late.chooseDue(.setDate,input:late.inputControl);late.update(.dueAt,"2026-10-30T12:00:00Z",input:late.inputControl);late.prepare(expected:late.control);let lj=Task {await late.submit(late.session.review!,expected:late.control)};await lp.wait(0)
    late.bind(TaskDraftContext(business:202,epoch:243));base(late);late.chooseDue(.setDate,input:late.inputControl);late.update(.dueAt,"2038-01-19T03:14:08Z",input:late.inputControl);let replacement=late.session.values,control=late.control;await lp.resolve(0,.unknown);await lj.value
    try expect(late.session.values==replacement && late.control==control && late.submission==nil,"Late create date touched replacement form")
    return count
}
