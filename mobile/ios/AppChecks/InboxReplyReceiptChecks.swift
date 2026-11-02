import Foundation
import CRMCore

actor ControlledInboxReplyPort:SyntheticInboxReplyPort {
    nonisolated let grants:[SyntheticInboxReplyGrant]
    private var attempts:[InboxReplyAttempt]=[]
    private var pending:[Int:CheckedContinuation<SyntheticInboxReplyOutcome,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    init(_ grants:[SyntheticInboxReplyGrant]) {self.grants=grants}
    func execute(_ a:InboxReplyAttempt) async throws -> SyntheticInboxReplyOutcome {let i=attempts.count;attempts.append(a);return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ value:SyntheticInboxReplyOutcome) {pending.removeValue(forKey:i)!.resume(returning:value)}
    func fail(_ i:Int) {pending.removeValue(forKey:i)!.resume(throwing:ReadFailure.unavailable)}
    func recorded()->[InboxReplyAttempt] {attempts}
}
@MainActor func checkInboxReplyReceipt(directory:URL) async throws -> Int {
    var count=0
    func expect(_ v:Bool,_ message:String) throws {guard v else {throw ViewModelCheckFailure(message:message)};count += 1}
    func thread(_ b:Int=101,_ id:Int=901) throws -> InboxThread {try JSONDecoder().decode(InboxThread.self,from:Data(contentsOf:directory.appendingPathComponent("inbox-\(b)-\(id).json")))}
    let original=try thread(),fixture=FixtureInboxReplyPort(directory:directory),p=ControlledInboxReplyPort(fixture.grants),m=ReplyDraftViewModel(submission:p)
    func prepare(_ m:ReplyDraftViewModel,_ raw:String=" Reply ",epoch:Int=270) {m.verified(original,business:101,id:901,epoch:epoch);m.open(expected:m.entryControl);m.update(raw,input:m.inputControl);m.prepare(expected:m.control)}
    let plain=ReplyDraftViewModel();prepare(plain);try expect(!plain.canSubmit && !plain.hasTestPort,"GET/default composition granted reply UPDATE/key")
    let denied=ReplyDraftViewModel(submission:ControlledInboxReplyPort([SyntheticInboxReplyGrant(business:101,conversation:901,actor:9001,update:false,keys:["k"])]));prepare(denied);try expect(!denied.canSubmit,"VIEW became reply UPDATE")
    prepare(m," e\u{0301} ");let oldReview=m.session.review!,oldControl=m.control!;m.back(expected:m.returnControl);m.update(" é ",input:m.inputControl);m.prepare(expected:m.control);let current=m.session.review!;await m.submit(oldReview,expected:m.control);await m.submit(current,expected:oldControl);let before=await p.recorded();try expect(before.isEmpty,"Old raw/review/visit submitted current reply")
    let send=m.control!,job=Task {await m.submit(current,expected:send)};await p.wait(0);let pending=m.control!,record=m.submission!;m.update("lost",input:m.inputControl);m.askClear(expected:pending);m.discard(pending.selection);m.acknowledge(expected:pending,record:record);await m.submit(current,expected:pending)
    let calls=await p.recorded();try expect(calls.count==1 && m.session.text.utf8.elementsEqual(current.raw.utf8) && m.submission==record && m.clearConfirmation==nil,"Pending reply changed/repeated/lost exact raw/key")
    m.back(expected:m.returnControl);m.open(expected:m.entryControl);try expect(m.submission==record && m.inputControl==nil,"Closing/reopening pending allowed mutable input")
    await p.fail(0);await job.value;let unknown=m.submission!;m.acknowledge(expected:m.control,record:unknown);m.verified(original,business:101,id:901,epoch:271);m.open(expected:m.entryControl)
    try expect(m.submissionBlocked && m.submission==nil && m.inputControl==nil && unknown.attempt.review==current && unknown.attempt.key==calls[0].key,"New epoch/reread/ack recovered unknown reply")
    let np=ControlledInboxReplyPort(fixture.grants),noWrite=ReplyDraftViewModel(submission:np);prepare(noWrite);let nr=noWrite.session.review!,nc=noWrite.control!;let nj=Task {await noWrite.submit(nr,expected:nc)};await np.wait(0);await np.resolve(0,.rejectedWithoutWrite);await nj.value;let rejected=noWrite.submission!;noWrite.acknowledge(expected:noWrite.control,record:rejected);await noWrite.submit(nr,expected:nc)
    try expect(noWrite.session.phase == .editing && noWrite.session.text==nr.raw && noWrite.session.review==nil,"No-write erased raw or repeated without new review")
    noWrite.prepare(expected:noWrite.control);let second=Task {await noWrite.submit(noWrite.session.review!,expected:noWrite.control)};await np.wait(1);let history=await np.recorded();try expect(history.count==2 && history[0].key != history[1].key && history[0].review==history[1].review,"Fresh no-write review generated/reused rather than selected a configured unused key")
    await np.resolve(1,.unknown);await second.value
    let transport=SearchTransport(directory),owner=InboxViewModel(repository:APIReadRepository(transport:transport),replySubmission:fixture);await owner.load(business:101,epoch:272);await owner.open(id:901);let snapshot=inboxReadSnapshot(owner.thread,owner.items),reads=await transport.recorded().count,v=owner.reply
    owner.openReply(v.session.context!,expected:owner.control);v.update(" Local test reply ",input:v.inputControl);v.prepare(expected:v.control);let review=v.session.review!;await v.submit(review,expected:v.control);let accepted=v.submission!,after=await transport.recorded().count
    try expect(accepted.phase == .confirmed && accepted.receipt?.delivery == .queued && inboxReadSnapshot(owner.thread,owner.items)==snapshot && reads==after,"Queued fake receipt claimed no-write/delivery or mutated thread/unread/read count")
    v.acknowledge(expected:v.control,record:accepted);try expect(v.session.selection==nil && v.session.text.isEmpty && accepted.attempt.review==review,"Known receipt acknowledgement lost immutable original attempt")
    let long=ReplyDraftViewModel(submission:fixture);prepare(long,String(repeating:"e\u{0301}",count:250)+"Z");let lr=long.session.review!;await long.submit(lr,expected:long.control)
    try expect(long.submission?.phase == .unknown && long.submission?.attempt.review.raw==lr.raw && lr.text.unicodeScalars.count==501,"500 excerpt was full-input proof or manual input was truncated")
    let lp=ControlledInboxReplyPort(fixture.grants),late=ReplyDraftViewModel(submission:lp);prepare(late);let lj=Task {await late.submit(late.session.review!,expected:late.control)};await lp.wait(0);let a=await lp.recorded()[0];late.verified(try thread(202,951),business:202,id:951,epoch:273);late.open(expected:late.entryControl);late.update(" Other owner private raw ",input:late.inputControl);let replacement=late.control,input=late.inputControl
    await lp.resolve(0,try await fixture.execute(a));await lj.value;try expect(late.control==replacement && late.inputControl==input && late.session.text==" Other owner private raw " && late.submission==nil,"Late reply receipt touched replacement owner/input")
    return count
}
