import Foundation
import CRMCore

actor ControlledInboxRetryPort:SyntheticInboxRetryPort {
    nonisolated let grants:[SyntheticInboxRetryGrant]
    private var attempts:[InboxRetryAttempt]=[]
    private var pending:[Int:CheckedContinuation<SyntheticInboxRetryOutcome,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    init(_ grants:[SyntheticInboxRetryGrant]) {self.grants=grants}
    func execute(_ a:InboxRetryAttempt) async throws -> SyntheticInboxRetryOutcome {let i=attempts.count;attempts.append(a);return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ outcome:SyntheticInboxRetryOutcome) {pending.removeValue(forKey:i)!.resume(returning:outcome)}
    func fail(_ i:Int) {pending.removeValue(forKey:i)!.resume(throwing:ReadFailure.unavailable)}
    func recorded()->[InboxRetryAttempt] {attempts}
}
actor RetryFixtureReadRecorder:ReadTransport {
    private let base:FixtureInboxRetryReadTransport;private var requests:[ReadRequest]=[]
    init(_ directory:URL) {base=FixtureInboxRetryReadTransport(directory:directory)}
    func get(_ q:ReadRequest) async throws -> ReadResponse {requests.append(q);return try await base.get(q)}
    func recorded()->[ReadRequest] {requests}
}
@MainActor func checkInboxRetryMessage(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let read=APIReadRepository(transport:FixtureTransport(directory:directory)),fixture=FixtureInboxRetryPort(directory:directory),port=ControlledInboxRetryPort(fixture.grants),transport=RetryFixtureReadRecorder(directory),metadata=APIInboxMessageFilesRepository(transport:transport),replyPort=ControlledInboxReplyPort(FixtureInboxReplyPort(directory:directory).grants),handoffPort=ControlledHandoffPort(FixtureHandoffPort(directory:directory).grants)
    let m=InboxViewModel(repository:read,replySubmission:replyPort,handoffSubmission:handoffPort,messageFiles:metadata,retrySubmission:port)
    await m.load(business:101,epoch:411);await m.open(id:901);let row=m.thread!.messages[1],original=inboxReadSnapshot(m.thread,m.items),child=m.messageMetadata!,replyContext=m.reply.session.context!
    m.openMessageFiles(expected:m.messageFilesEntryControl(row));let presentation=m.messageFilesPresentationControl!
    try expect(await transport.recorded()==[] && !child.canPrepareRetry && child.retryReview==nil,"Bounded row/open minted generic source/UPDATE review or automatic GET")
    await child.load(expected:child.control);let source=child.window!.retrySource!,before=child.control!
    try expect(source.context.message==row.id && source.status=="failed" && row.sourceState == .sent && child.canPrepareRetry && inboxReadSnapshot(m.thread,m.items)==original,"Generic retry source came from bounded status or patched thread")
    child.prepareRetry(expected:before);let review=child.retryReview!,control=child.control!,reads=await transport.recorded()
    await child.load(expected:control);await child.submitRetry(review,expected:before);child.backRetry(expected:before)
    try expect(await transport.recorded()==reads && child.retryReview==review && child.canSubmitRetry,"Old review/control or manual reread changed frozen review")
    let none=await port.recorded();try expect(none.isEmpty,"Preparing review executed a fake command")
    let job=Task {await child.submitRetry(review,expected:control)};await port.wait(0);let first=await port.recorded()[0],pending=child.retryRecord!
    await child.submitRetry(review,expected:child.control);child.acknowledgeRetry(pending,expected:child.control)
    try expect(await port.recorded().count==1 && pending.phase == .pending && m.retryCommandsBlocked && first.preparedBody()==pending.attempt.preparedBody() && first.review.source==source,"Pending duplicate/ack lost frozen original/body/actor or failed parent barrier")
    m.closeMessageFiles(expected:presentation);m.openReply(replyContext,expected:m.control);m.openHandoff(entry:m.handoff.entryControl,expected:m.control)
    try expect(m.reply.control==nil && m.handoff.control==nil && m.retryCommandsBlocked,"Closing pending retry bypassed parent reply/handoff barrier")
    // Even trusted direct editor entry must fail at the sibling submit boundary.
    m.reply.open(replyContext);m.reply.update(" Must not bypass retry ",input:m.reply.inputControl);m.reply.prepare(expected:m.reply.control);let direct=m.reply.session.review!;await m.reply.submit(direct,expected:m.reply.control)
    try expect(await replyPort.recorded().isEmpty && !m.reply.canSubmit,"Direct old reply submit bypassed retained retry")
    m.reply.close(expected:m.reply.returnControl);m.openMessageFiles(expected:m.messageFilesEntryControl(row));await child.load(expected:child.control)
    try expect(await transport.recorded()==reads && child.retryRecord==pending && child.window==nil,"Pending reopen/reread lost attempt or invented a fresh command source")
    await port.resolve(0,try await fixture.execute(first));await job.value;let response=child.retryRecord!
    try expect(response.phase == .response && response.result?.id==9901 && response.attempt==first && inboxReadSnapshot(m.thread,m.items)==original,"Fake201 claimed thread mutation or lost original selector")
    child.acknowledgeRetry(response,expected:control);try expect(child.retryRecord==response,"Old acknowledgement cleared newer result")
    child.acknowledgeRetry(response,expected:child.control);try expect(!m.retryCommandsBlocked && child.retainedRetryCount==1 && child.retryRecord==nil,"Known acknowledgement erased history or failed to release explicit test result")
    await child.load(expected:child.control);child.prepareRetry(expected:child.control);let rejectedReview=child.retryReview!,rejectedControl=child.control!,rejectedJob=Task {await child.submitRetry(rejectedReview,expected:rejectedControl)};await port.wait(1);await port.resolve(1,.rejectedWithoutWrite);await rejectedJob.value;let rejected=child.retryRecord!
    try expect(rejected.phase == .rejected && rejected.attempt.review.source==source,"Explicit no-write rejection fabricated response or lost original text")
    child.acknowledgeRetry(rejected,expected:child.control);child.prepareRetry(expected:child.control);let unknownReview=child.retryReview!,unknownControl=child.control!,unknownJob=Task {await child.submitRetry(unknownReview,expected:unknownControl)};await port.wait(2);await port.fail(2);await unknownJob.value;let unknown=child.retryRecord!
    try expect(unknown.phase == .unknown && child.retainedRetryCount==3 && m.retryCommandsBlocked,"Thrown transport-like fake failure did not quarantine attempted input")
    child.acknowledgeRetry(unknown,expected:child.control);await child.load(expected:child.control);child.prepareRetry(expected:child.control);await child.submitRetry(unknownReview,expected:child.control)
    try expect(await port.recorded().count==3 && child.retryRecord==unknown && child.retryReview==nil && child.window?.retrySource==source && !child.canPrepareRetry,"Matching source reread/ack/review silently repeated or proved unknown")
    m.closeMessageFiles(expected:m.messageFilesPresentationControl);await m.retryThread(expected:m.threadSelection);m.openMessageFiles(expected:m.messageFilesEntryControl(m.thread!.messages[1]));await child.load(expected:child.control)
    try expect(child.retryRecord==unknown && m.retryCommandsBlocked && child.retainedRetryCount==3 && child.window?.retrySource?.context.revision != unknown.attempt.review.source.context.revision,"New thread read rebound original attempt/read revision or released unknown")
    m.closeMessageFiles(expected:m.messageFilesPresentationControl);await m.load(business:202,epoch:412);await m.open(id:951);m.openMessageFiles(expected:m.messageFilesEntryControl(m.thread!.messages[1]));await child.load(expected:child.control)
    try expect(child.retryRecord==nil && child.canPrepareRetry && !m.retryCommandsBlocked && child.retainedRetryCount==3,"Another Business showed or inherited old active source/actor")
    m.closeMessageFiles(expected:m.messageFilesPresentationControl);await m.load(business:101,epoch:413);await m.open(id:901);m.openMessageFiles(expected:m.messageFilesEntryControl(m.thread!.messages[0]));await child.load(expected:child.control)
    try expect(child.retryRecord==unknown && m.retryCommandsBlocked && !child.canPrepareRetry && child.window?.context.message==9011 && child.retryRecord?.attempt.review.source.context.message==9012,"Business A-B-A/other selected message rebound frozen original or bypassed unknown")
    m.closeMessageFiles(expected:m.messageFilesPresentationControl)
    m.handoff.open(expected:m.handoff.entryControl);m.handoff.update(" Must not bypass retry ",input:m.handoff.inputControl);m.handoff.prepare(expected:m.handoff.control);let forced=m.handoff.session.review!;await m.handoff.submit(forced,expected:m.handoff.control)
    try expect(await handoffPort.recorded().isEmpty && !m.handoff.canSubmit,"Direct handoff submit bypassed retained retry")
    m.handoff.back(expected:m.handoff.returnControl);m.handoff.back(expected:m.handoff.returnControl)
    // An existing unknown reply must block the inverse direction before fake retry execute.
    let blockedPort=ControlledInboxRetryPort(fixture.grants),rp=ControlledInboxReplyPort(FixtureInboxReplyPort(directory:directory).grants),blocked=InboxViewModel(repository:read,replySubmission:rp,messageFiles:metadata,retrySubmission:blockedPort)
    await blocked.load(business:101,epoch:414);await blocked.open(id:901);blocked.openReply(blocked.reply.session.context!,expected:blocked.control);blocked.reply.update(" Original unknown reply ",input:blocked.reply.inputControl);blocked.reply.prepare(expected:blocked.reply.control);let rr=blocked.reply.session.review!,rc=blocked.reply.control!,rj=Task {await blocked.reply.submit(rr,expected:rc)};await rp.wait(0);await rp.resolve(0,.unknown);await rj.value;let retained=blocked.reply.submission!;blocked.reply.close(expected:blocked.reply.returnControl)
    blocked.openMessageFiles(expected:blocked.messageFilesEntryControl(blocked.thread!.messages[1]));let bc=blocked.messageMetadata!;await bc.load(expected:bc.control);bc.prepareRetry(expected:bc.control)
    try expect(await blockedPort.recorded().isEmpty && !bc.canPrepareRetry && bc.retryReview==nil && blocked.reply.submission==retained,"Existing unknown reply became a retry command context")
    let hp=ControlledHandoffPort(FixtureHandoffPort(directory:directory).grants),blockedHandoff=InboxViewModel(repository:read,handoffSubmission:hp,messageFiles:metadata,retrySubmission:blockedPort)
    await blockedHandoff.load(business:101,epoch:415);await blockedHandoff.open(id:901);blockedHandoff.openHandoff(entry:blockedHandoff.handoff.entryControl,expected:blockedHandoff.control);blockedHandoff.handoff.update(" Original unknown handoff ",input:blockedHandoff.handoff.inputControl);blockedHandoff.handoff.prepare(expected:blockedHandoff.handoff.control);let hr=blockedHandoff.handoff.session.review!,hc=blockedHandoff.handoff.control!,hj=Task {await blockedHandoff.handoff.submit(hr,expected:hc)};await hp.wait(0);await hp.resolve(0,.unknown);await hj.value;let oldHandoff=blockedHandoff.handoff.record!;blockedHandoff.handoff.back(expected:blockedHandoff.handoff.returnControl)
    blockedHandoff.openMessageFiles(expected:blockedHandoff.messageFilesEntryControl(blockedHandoff.thread!.messages[1]));let bh=blockedHandoff.messageMetadata!;await bh.load(expected:bh.control);bh.prepareRetry(expected:bh.control)
    try expect(await blockedPort.recorded().isEmpty && !bh.canPrepareRetry && bh.retryReview==nil && blockedHandoff.handoff.record==oldHandoff,"Unknown handoff bypassed retry sibling barrier")
    // Completion for a closed old owner must retain its result without touching current peer input.
    let lp=ControlledInboxRetryPort(fixture.grants),late=InboxViewModel(repository:read,messageFiles:metadata,retrySubmission:lp);await late.load(business:101,epoch:416);await late.open(id:901);late.openMessageFiles(expected:late.messageFilesEntryControl(late.thread!.messages[1]));let lc=late.messageMetadata!;await lc.load(expected:lc.control);lc.prepareRetry(expected:lc.control);let lr=lc.retryReview!,lctrl=lc.control!,lj=Task {await lc.submitRetry(lr,expected:lctrl)};await lp.wait(0);let la=await lp.recorded()[0];late.closeMessageFiles(expected:late.messageFilesPresentationControl);await late.load(business:202,epoch:417);await late.open(id:951);late.openReply(late.reply.session.context!,expected:late.control);late.reply.update(" Current Business B draft ",input:late.reply.inputControl);let peer=late.reply.control,beforeLate=inboxReadSnapshot(late.thread,late.items)
    await lp.resolve(0,try await fixture.execute(la));await lj.value
    try expect(lc.retryRecord==nil && lc.window==nil && lc.retainedRetryCount==1 && late.reply.control==peer && late.reply.session.text==" Current Business B draft " && inboxReadSnapshot(late.thread,late.items)==beforeLate,"Late retry result displaced foreign draft/current read")
    let noPort=InboxViewModel(repository:read,messageFiles:metadata);await noPort.load(business:101,epoch:418);await noPort.open(id:901);noPort.openMessageFiles(expected:noPort.messageFilesEntryControl(noPort.thread!.messages[1]));let nc=noPort.messageMetadata!;await nc.load(expected:nc.control);nc.prepareRetry(expected:nc.control);try expect(!nc.canPrepareRetry && nc.retryReview==nil && nc.retainedRetryCount==0,"Default GET composition synthesized UPDATE or command port")
    return count
}
