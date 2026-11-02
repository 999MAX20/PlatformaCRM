import Foundation
import CRMCore

actor RecordedMessageMetadataTransport:ReadTransport {
    let base:FixtureInboxMessageFilesTransport;private var requests:[ReadRequest]=[]
    init(_ directory:URL) {base=FixtureInboxMessageFilesTransport(directory:directory)}
    func get(_ request:ReadRequest) async throws -> ReadResponse {requests.append(request);return try await base.get(request)}
    func recorded()->[ReadRequest] {requests}
}
actor HeldMessageMetadata:InboxMessageFilesRepository {
    private var anchors:[Int:CheckedContinuation<InboxFilesConversationAnchor,any Error>]=[:],windows:[Int:CheckedContinuation<InboxMessageFileWindow,any Error>]=[:]
    private var anchorWaiters:[Int:CheckedContinuation<Void,Never>]=[:],windowWaiters:[Int:CheckedContinuation<Void,Never>]=[:]
    private var a=0,w=0
    func anchor(_ c:InboxMessageFilesContext) async throws -> InboxFilesConversationAnchor {let i=a;a += 1;return try await withCheckedThrowingContinuation {anchors[i]=$0;anchorWaiters.removeValue(forKey:i)?.resume()}}
    func messages(_ c:InboxMessageFilesContext,anchor:InboxFilesConversationAnchor) async throws -> InboxMessageFileWindow {let i=w;w += 1;return try await withCheckedThrowingContinuation {windows[i]=$0;windowWaiters.removeValue(forKey:i)?.resume()}}
    func waitAnchor(_ i:Int) async {if anchors[i]==nil {await withCheckedContinuation {anchorWaiters[i]=$0}}}
    func waitWindow(_ i:Int) async {if windows[i]==nil {await withCheckedContinuation {windowWaiters[i]=$0}}}
    func resolveAnchor(_ i:Int,_ value:InboxFilesConversationAnchor) {anchors.removeValue(forKey:i)!.resume(returning:value)}
    func resolveWindow(_ i:Int,_ value:InboxMessageFileWindow) {windows.removeValue(forKey:i)!.resume(returning:value)}
    func rejectAnchor(_ i:Int,_ error:ReadFailure) {anchors.removeValue(forKey:i)!.resume(throwing:error)}
    func rejectWindow(_ i:Int,_ error:ReadFailure) {windows.removeValue(forKey:i)!.resume(throwing:error)}
    func counts()->[Int] {[a,w]}
}
@MainActor func checkInboxMessageFiles(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),transport=RecordedMessageMetadataTransport(directory),messages=APIInboxMessageFilesRepository(transport:transport),files=APIInboxConversationFilesRepository(transport:FixtureInboxConversationFilesTransport(directory:directory)),port=ControlledInboxReplyPort(FixtureInboxReplyPort(directory:directory).grants)
    let m=InboxViewModel(repository:repo,replySubmission:port,handoffSubmission:FixtureHandoffPort(directory:directory),files:files,messageFiles:messages)
    await m.load(business:101,epoch:88);try expect(m.messageMetadata?.owner==nil,"List created a selected-message owner")
    await m.open(id:901);let child=m.messageMetadata!,row=m.thread!.messages[0],other=m.thread!.messages[1],entry=m.messageFilesEntryControl(row)!,parent=m.control!,oldReturn=m.returnControl,conversationEntry=m.filesEntryControl,client=m.clientLinks?.entryControl,handoff=m.handoff.entryControl,replyContext=m.reply.session.context!,original=inboxReadSnapshot(m.thread,m.items)
    let before=await transport.recorded();try expect(before.isEmpty && child.owner?.limit==m.thread?.payload_budget.max_messages && child.owner?.limit==30,"Message entry invented default limit or issued automatic reads")
    var foreignObject=(try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("inbox-101-901.json"))) as! [String:Any])["messages"] as! [[String:Any]];foreignObject[0]["conversation_id"]=951
    let foreign=try JSONDecoder().decode(InboxMessage.self,from:JSONSerialization.data(withJSONObject:foreignObject[0]));try expect(m.messageFilesEntryControl(foreign)==nil,"Foreign bounded message became an entry")
    m.openMessageFiles(expected:entry);let presentation=m.messageFilesPresentationControl!,initial=child.control!
    try expect(child.context?.message==row.id && child.context?.limit==30 && child.window==nil && !child.loading && m.filesEntryControl==nil && m.messageFilesEntryControl(other)==nil,"Open selected metadata defaulted response or overlapped another child")
    m.backToThreadList(expected:oldReturn);m.openFiles(expected:conversationEntry);m.openReply(replyContext,expected:parent);m.openReply(replyContext,expected:m.control);await m.openClient(entry:client,expected:m.control);m.openHandoff(entry:handoff,expected:m.control)
    try expect(m.matchesMessageFiles(presentation) && m.reply.control==nil && m.handoff.control==nil && m.clientLinks?.selectedID==nil && m.fileMetadata?.presented==false,"Old/current peer controls escaped message inspector")
    await child.load(expected:child.control);let window=child.window!,loaded=child.control!,requests=await transport.recorded()
    try expect(requests==[ReadRequest(path:"/api/inbox/conversations/901/"),ReadRequest(path:"/api/inbox/conversations/901/messages/",query:["limit":"30"])],"Message metadata did not independently anchor before exact provided-limit GET")
    try expect(window.context==child.context && window.providedMessages==2 && window.count==2 && !window.hasMore && window.items.count==2 && m.matchesMessageFiles(presentation),"Source count/window/selected projection or stable presentation changed")
    try expect(inboxReadSnapshot(m.thread,m.items)==original && m.reply.retainedAttemptCount==0 && m.handoff.retainedAttemptCount==0,"Metadata patched bounded source/unread or derived command context")
    child.select(window.items[0],expected:initial);try expect(child.selected==nil,"Old pending-control selected newer window row")
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("inbox-message-files.json"))) as! [String:Any],raw=(catalog["reads"] as! [[String:Any]]).first {($0["path"] as? String)=="/api/inbox/conversations/901/messages/"}!["response_json"] as! String
    let changed=try InboxMessageFileWindow.decode(Data(raw.replacingOccurrences(of:"e\u{301}.txt",with:"é.txt").utf8),context:window.context)
    child.select(changed.items[1],expected:loaded);try expect(child.selected==nil,"Canonical-equivalent different raw filename was admitted as current row")
    child.select(window.items[0],expected:loaded);let oldRow=child.control!;child.back(expected:oldRow);await child.load(expected:child.control);child.select(window.items[0],expected:loaded)
    try expect(child.selected==nil && m.matchesMessageFiles(presentation),"Matching independent reread revived old choice or lost navigation")
    child.select(child.window!.items[1],expected:child.control);let selected=child.selected;child.back(expected:oldRow);try expect(child.selected==selected && selected?.size==0 && selected?.contentType.isEmpty==true,"Old row Back/blank size/type corrupted current selection")
    m.closeMessageFiles(expected:presentation);try expect(child.window==nil && child.context==nil && !child.presented && m.messageFilesEntryControl(row) != nil,"Message close retained old payload/context or lost parent entry")
    m.openMessageFiles(expected:m.messageFilesEntryControl(other));let second=m.messageFilesPresentationControl!;m.closeMessageFiles(expected:presentation);m.openMessageFiles(expected:entry)
    try expect(m.messageFilesPresentationControl==second && child.context?.message==other.id,"Old selected-message Close/Open crossed reopen")
    await child.load(expected:child.control);try expect(child.window?.items.isEmpty==true && child.failure==nil && child.window?.context.message==other.id,"Provided selected empty attachments became missing message/error")
    m.closeMessageFiles(expected:second);m.openFiles(expected:m.filesEntryControl);try expect(m.messageFilesEntryControl(row)==nil && child.presented==false,"Message and conversation file inspectors overlapped");m.closeFiles(expected:m.filesPresentationControl)
    // Read observations must not release/replay a retained unknown local reply.
    m.openReply(replyContext,expected:m.control);m.reply.update(" Retained message metadata unknown reply ",input:m.reply.inputControl);m.reply.prepare(expected:m.reply.control);let review=m.reply.session.review!,sendControl=m.reply.control!
    let send=Task {await m.reply.submit(review,expected:sendControl)};await port.wait(0);await port.resolve(0,.unknown);await send.value;let unknown=m.reply.submission!;m.reply.close(expected:m.reply.returnControl)
    m.openMessageFiles(expected:m.messageFilesEntryControl(row));await child.load(expected:child.control);m.closeMessageFiles(expected:m.messageFilesPresentationControl)
    try expect(m.reply.submissionBlocked && m.reply.retainedAttemptCount==1 && m.reply.submission==unknown && inboxReadSnapshot(m.thread,m.items)==original,"Independent matching metadata proved/replayed unknown reply input/body/key")
    await m.retryThread(expected:m.threadSelection);try expect(m.reply.submissionBlocked && m.reply.retainedAttemptCount==1 && !child.presented && child.window==nil,"Matching bounded thread reread restored metadata or released unknown")
    // A late anchor must not issue the dependent message GET after close/peer/source change.
    let held=HeldMessageMetadata(),late=InboxViewModel(repository:repo,files:files,messageFiles:held);await late.load(business:101,epoch:90);await late.open(id:901);let lc=late.messageMetadata!,a=late.thread!.messages[0],b=late.thread!.messages[1]
    late.openMessageFiles(expected:late.messageFilesEntryControl(a));let first=late.messageFilesPresentationControl!,c0=lc.context!,job=Task {await lc.load(expected:lc.control)};await held.waitAnchor(0);late.closeMessageFiles(expected:first);late.openFiles(expected:late.filesEntryControl);let peer=late.filesPresentationControl!
    await held.resolveAnchor(0,try await messages.anchor(c0));await job.value;late.closeMessageFiles(expected:first)
    try expect(await held.counts()==[1,0] && lc.window==nil && !lc.presented && late.filesPresentationControl==peer,"Late anchor issued page GET or displaced conversation files")
    late.closeFiles(expected:peer);late.openMessageFiles(expected:late.messageFilesEntryControl(b));let c1=lc.context!,p1=late.messageFilesPresentationControl!,page=Task {await lc.load(expected:lc.control)};await held.waitAnchor(1);let anchor1=try await messages.anchor(c1);await held.resolveAnchor(1,anchor1);await held.waitWindow(0)
    late.closeMessageFiles(expected:p1);late.openReply(late.reply.session.context!,expected:late.control);late.reply.update(" Retained peer draft ",input:late.reply.inputControl);let draft=late.reply.control!
    await held.resolveWindow(0,try await messages.messages(c1,anchor:anchor1));await page.value
    try expect(lc.window==nil && !lc.presented && late.reply.control==draft && late.reply.session.text==" Retained peer draft ","Late metadata window restored rows or reset peer draft")
    late.reply.close(expected:late.reply.returnControl);late.openMessageFiles(expected:late.messageFilesEntryControl(a));let c2=lc.context!,p2=late.messageFilesPresentationControl!,changedOwner=Task {await lc.load(expected:lc.control)};await held.waitAnchor(2);let anchor2=try await messages.anchor(c2);await held.resolveAnchor(2,anchor2);await held.waitWindow(1)
    await late.load(business:202,epoch:91);await late.open(id:951);let next=late.messageFilesEntryControl(late.thread!.messages[0]);await held.resolveWindow(1,try await messages.messages(c2,anchor:anchor2));await changedOwner.value
    try expect(lc.window==nil && !lc.presented && lc.owner?.read.business==202 && late.messageFilesEntryControl(late.thread!.messages[0])==next,"Late message window crossed Business owner")
    await late.load(business:101,epoch:92);await late.open(id:901);late.closeMessageFiles(expected:p2);try expect(!lc.presented && lc.owner?.read.epoch==92 && lc.window==nil,"Source A-B-A restored old metadata selection")
    late.openMessageFiles(expected:late.messageFilesEntryControl(late.thread!.messages[0]));let current=lc.context!,badAnchor=Task {await lc.load(expected:lc.control)};await held.waitAnchor(3);let foreignContext=InboxMessageFilesContext(business:202,conversation:951,message:9511,epoch:1,revision:1,limit:30);await held.resolveAnchor(3,try await messages.anchor(foreignContext));await badAnchor.value
    let afterForeign=await held.counts();try expect(lc.failure == .invalidPayload && lc.window==nil && afterForeign==[4,2],"Typed foreign anchor reached dependent page or displayed metadata")
    let wrongSelected=Task {await lc.load(expected:lc.control)};await held.waitAnchor(4);let good=try await messages.anchor(current);await held.resolveAnchor(4,good);await held.waitWindow(2)
    let otherContext=InboxMessageFilesContext(business:101,conversation:901,message:9012,epoch:current.epoch,revision:current.revision,limit:30);await held.resolveWindow(2,try await messages.messages(otherContext,anchor:good));await wrongSelected.value
    try expect(lc.failure == .invalidPayload && lc.window==nil,"Typed other-selected-message window bypassed context admission")
    let denied=Task {await lc.load(expected:lc.control)};await held.waitAnchor(5);await held.rejectAnchor(5,.denied);await denied.value
    try expect(lc.failure == .denied && lc.window==nil && !lc.loading,"Denied anchor became empty/automatic retry")
    let missing=Task {await lc.load(expected:lc.control)};await held.waitAnchor(6);await held.resolveAnchor(6,good);await held.waitWindow(3);await held.rejectWindow(3,.unavailable);await missing.value
    try expect(lc.failure == .unavailable && lc.window==nil,"Missing selected message became empty attachments or cursor traversal")
    let noPort=InboxViewModel(repository:repo);await noPort.load(business:101,epoch:1);await noPort.open(id:901);try expect(noPort.messageMetadata==nil && noPort.messageFilesEntryControl(noPort.thread!.messages[0])==nil,"Default composition manufactured message repository")
    return count
}
