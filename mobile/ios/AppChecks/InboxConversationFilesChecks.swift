import Foundation
import CRMCore

actor RecordedConversationFilesTransport:ReadTransport {
    let base:FixtureInboxConversationFilesTransport
    private var requests:[ReadRequest]=[]
    init(_ directory:URL) {base=FixtureInboxConversationFilesTransport(directory:directory)}
    func get(_ request:ReadRequest) async throws -> ReadResponse {requests.append(request);return try await base.get(request)}
    func recorded()->[ReadRequest] {requests}
}
actor HeldConversationFiles:InboxConversationFilesRepository {
    private var pending:[Int:CheckedContinuation<[InboxConversationFileMetadata],any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    private var requests:[InboxConversationFilesContext]=[]
    func files(_ context:InboxConversationFilesContext) async throws -> [InboxConversationFileMetadata] {let i=requests.count;requests.append(context);return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ rows:[InboxConversationFileMetadata]) {pending.removeValue(forKey:i)!.resume(returning:rows)}
    func reject(_ i:Int,_ failure:ReadFailure) {pending.removeValue(forKey:i)!.resume(throwing:failure)}
}
@MainActor func checkInboxConversationFiles(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),transport=RecordedConversationFilesTransport(directory),files=APIInboxConversationFilesRepository(transport:transport),replyPort=ControlledInboxReplyPort(FixtureInboxReplyPort(directory:directory).grants)
    let m=InboxViewModel(repository:repo,replySubmission:replyPort,handoffSubmission:FixtureHandoffPort(directory:directory),files:files)
    await m.load(business:101,epoch:77);try expect(m.filesEntryControl==nil,"List-only source created file context")
    await m.open(id:901);let child=m.fileMetadata!,entry=m.filesEntryControl!,original=inboxReadSnapshot(m.thread,m.items),source=m.threadSelection!,oldReturn=m.returnControl,parent=m.control!,client=m.clientLinks?.entryControl,handoff=m.handoff.entryControl,context=m.reply.session.context!
    let initialMetadataReads=await transport.recorded()
    try expect(child.context==InboxConversationFilesContext(business:101,conversation:901,epoch:77,revision:source.revision) && initialMetadataReads.isEmpty,"Bounded thread derived attachment contents or automatic GET")
    m.openFiles(expected:entry);let presentation=m.filesPresentationControl!,before=child.control!
    try expect(child.presented && !child.loaded && !child.loading && m.filesEntryControl==nil,"Open files automatically read/defaulted empty or allowed duplicate entry")
    m.openFiles(expected:entry);m.backToThreadList(expected:oldReturn);m.openReply(context,expected:parent);await m.openClient(entry:client,expected:m.control);m.openHandoff(entry:handoff,expected:m.control);m.openReply(context,expected:m.control)
    try expect(m.threadSelection==source && m.reply.control==nil && m.handoff.control==nil && m.clientLinks?.selectedID==nil && m.matchesFiles(presentation),"Stale/current peer actions escaped file inspector ownership")
    await child.load(expected:child.control);let rows=child.items,loaded=child.control!
    try expect(await transport.recorded()==[ReadRequest(path:"/api/inbox/conversations/901/")] && rows.count==2 && child.loaded && child.failure==nil && m.matchesFiles(presentation),"Metadata exact separate GET or stable presentation changed")
    try expect(inboxReadSnapshot(m.thread,m.items)==original && m.reply.retainedAttemptCount==0 && m.handoff.retainedAttemptCount==0,"Metadata read patched source/read counts or generated command")
    child.select(rows[0],expected:before);try expect(child.selected==nil,"Old manual-read control selected new result")
    child.select(rows[0],expected:loaded);let oldRowControl=child.control!
    try expect(child.selected==rows[0] && child.selected?.size==4294967296,"Current metadata row lost strict64-bit observation")
    child.back(expected:oldRowControl);await child.load(expected:child.control);child.select(rows[0],expected:loaded)
    try expect(child.selected==nil && m.matchesFiles(presentation),"Matching reread revived old row control or revoked navigation")
    child.select(child.items[1],expected:child.control);let second=child.selected;child.back(expected:oldRowControl)
    try expect(child.selected==second && second?.contentType.isEmpty==true && second?.size==0,"Old row Back closed newer row or explicit blank/zero defaulted")
    m.closeFiles(expected:presentation);try expect(!child.presented && child.items.isEmpty && child.selected==nil && m.filesEntryControl != nil && inboxReadSnapshot(m.thread,m.items)==original,"File close lost parent source or retained metadata window")
    let nextEntry=m.filesEntryControl!;m.openFiles(expected:nextEntry);let reopened=m.filesPresentationControl!
    m.closeFiles(expected:presentation);m.openFiles(expected:entry);try expect(m.filesPresentationControl==reopened && child.items.isEmpty,"Old file Close/Open crossed same-context reopen")
    m.closeFiles(expected:reopened)
    // Peers exclude file entry; an immutable unknown reply is not released or replayed by metadata.
    m.openReply(context,expected:m.control);m.openFiles(expected:m.filesEntryControl)
    try expect(!child.presented && m.filesEntryControl==nil && m.reply.control != nil,"File entry overlapped reply composer")
    m.reply.update(" Retained unknown reply ",input:m.reply.inputControl);m.reply.prepare(expected:m.reply.control);let review=m.reply.session.review!,control=m.reply.control!
    let send=Task {await m.reply.submit(review,expected:control)};await replyPort.wait(0);await replyPort.resolve(0,.unknown);await send.value;let unknown=m.reply.submission!
    m.reply.close(expected:m.reply.returnControl);m.openFiles(expected:m.filesEntryControl);try expect(child.presented && m.reply.submissionBlocked,"Unknown unnecessarily invented read authority or was released")
    await child.load(expected:child.control);m.closeFiles(expected:m.filesPresentationControl)
    try expect(m.reply.retainedAttemptCount==1 && m.reply.submission==unknown && inboxReadSnapshot(m.thread,m.items)==original,"Metadata changed/repeated original unknown reply/body/key")
    await m.retryThread(expected:m.threadSelection);try expect(m.reply.submissionBlocked && m.reply.retainedAttemptCount==1 && !child.presented && child.items.isEmpty,"Matching thread reread kept old files or released unknown")
    // Source transitions and late success/denial cannot restore closed rows or displace another peer.
    let held=HeldConversationFiles(),late=InboxViewModel(repository:repo,files:held);await late.load(business:101,epoch:80);await late.open(id:901);let lc=late.fileMetadata!
    late.openFiles(expected:late.filesEntryControl);let first=late.filesPresentationControl!;let job=Task {await lc.load(expected:lc.control)};await held.wait(0)
    late.closeFiles(expected:first);late.openReply(late.reply.session.context!,expected:late.control);let reply=late.reply.control!
    await held.resolve(0,rows);await job.value;late.closeFiles(expected:first)
    try expect(late.reply.control==reply && lc.items.isEmpty && !lc.presented && !lc.loading,"Late metadata or old file Close displaced reply or restored rows")
    late.reply.close(expected:late.reply.returnControl);late.openFiles(expected:late.filesEntryControl);let denial=Task {await lc.load(expected:lc.control)};await held.wait(1);await held.reject(1,.denied);await denial.value
    try expect(lc.failure == .denied && !lc.loaded && lc.items.isEmpty && late.filesPresentationControl != nil,"Metadata denial became empty/success/parent permission")
    let retry=Task {await lc.load(expected:lc.control)};await held.wait(2);await late.load(business:202,epoch:81);await late.open(id:951);let other=late.filesEntryControl
    await held.resolve(2,rows);await retry.value;try expect(lc.items.isEmpty && !lc.presented && lc.context?.business==202 && late.filesEntryControl==other,"Late metadata crossed Business context")
    await late.load(business:101,epoch:82);await late.open(id:901);late.closeFiles(expected:first);try expect(!lc.presented && lc.items.isEmpty && lc.context?.epoch==82,"Business A-B-A restored old file inspector")
    // Typed fake ports also need model-side all-row scope/duplicate admission.
    let foreign=try await APIInboxConversationFilesRepository(transport:FixtureInboxConversationFilesTransport(directory:directory)).files(InboxConversationFilesContext(business:202,conversation:951,epoch:1,revision:1))
    late.openFiles(expected:late.filesEntryControl);let malformed=Task {await lc.load(expected:lc.control)};await held.wait(3);await held.resolve(3,foreign);await malformed.value
    try expect(lc.failure == .invalidPayload && lc.items.isEmpty && !lc.loaded,"Typed fake foreign rows bypassed model-side admission")
    let duplicate=Task {await lc.load(expected:lc.control)};await held.wait(4);await held.resolve(4,[rows[0],rows[0]]);await duplicate.value
    try expect(lc.failure == .invalidPayload && lc.items.isEmpty,"Typed duplicate rows reached UI")
    let empty=Task {await lc.load(expected:lc.control)};await held.wait(5);await held.resolve(5,[]);await empty.value
    try expect(lc.loaded && lc.failure==nil && lc.items.isEmpty,"Provided valid empty array did not remain explicit empty")
    let noFiles=InboxViewModel(repository:repo);await noFiles.load(business:101,epoch:1);await noFiles.open(id:901);noFiles.openFiles(expected:nil);try expect(noFiles.fileMetadata==nil && noFiles.filesEntryControl==nil,"Default composition manufactured generic attachment contract")
    return count
}
