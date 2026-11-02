import Foundation
import CRMCore

actor ObservedMessageTransport:ReadTransport {
    let base:FixtureInboxMessageFilesTransport;let pages:[String];private var page=0;private var requests:[ReadRequest]=[]
    init(_ directory:URL) throws {base=FixtureInboxMessageFilesTransport(directory:directory);let c=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("inbox-message-observations.json"))) as! [String:Any];pages=c["host_pages"] as! [String]}
    func select(_ value:Int) {page=value}
    func get(_ request:ReadRequest) async throws -> ReadResponse {requests.append(request);if request.path=="/api/inbox/conversations/901/messages/" {guard request.query==["limit":"30"],pages.indices.contains(page) else {throw ReadFailure.invalidContext};return ReadResponse(status:200,data:Data(pages[page].utf8))};return try await base.get(request)}
    func recorded()->[ReadRequest] {requests}
}
@MainActor func checkInboxMessageObservation(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let read=APIReadRepository(transport:FixtureTransport(directory:directory)),transport=try ObservedMessageTransport(directory),repo=APIInboxMessageFilesRepository(transport:transport),port=ControlledInboxReplyPort(FixtureInboxReplyPort(directory:directory).grants),m=InboxViewModel(repository:read,replySubmission:port,messageFiles:repo)
    await m.load(business:101,epoch:97);await m.open(id:901);let child=m.messageMetadata!,row=m.thread!.messages[0],original=inboxReadSnapshot(m.thread,m.items)
    m.openMessageFiles(expected:m.messageFilesEntryControl(row));let presentation=m.messageFilesPresentationControl!
    try expect(await transport.recorded()==[] && child.window==nil,"Opening observations issued automatic GET/defaulted response")
    await child.load(expected:child.control);let window=child.window!,first=window.observation
    try expect(first.valid(for:child.context!) && first.state == .unknown && first.status == .value("provider_future"),"Future raw status inferred delivery/read or lost selected scope")
    try expect(first.sentAt == .value("2026-10-28T04:20:00.000000Z") && first.deliveredAt == .value("2026-10-28T10:10:00+06:00") && first.readAt == .value(" raw-read-observation "),"Raw timestamp precision/zone/whitespace was normalized or repaired")
    try expect(m.matchesMessageFiles(presentation) && inboxReadSnapshot(m.thread,m.items)==original && window.items.count==2,"Observation replaced bounded source/messages/unread or attachment metadata")
    child.select(window.items[0],expected:child.control);let oldRow=child.control!;try expect(child.window?.observation==first,"Selecting a file replaced independent source observations");child.back(expected:oldRow)
    let old=child.control;await transport.select(1);await child.load(expected:child.control);child.select(window.items[0],expected:old)
    try expect(child.selected==nil && child.window?.observation.state == .sent && child.window?.observation.deliveredAt == .null && child.window?.observation.readAt == .missing,"Reread restored old row or collapsed null/missing/state")
    try expect(child.window?.observation.sentAt != first.sentAt && m.matchesMessageFiles(presentation),"Equivalent timestamp instant collapsed raw text or changed presentation")
    let requests=await transport.recorded();try expect(requests==[ReadRequest(path:"/api/inbox/conversations/901/"),ReadRequest(path:"/api/inbox/conversations/901/messages/",query:["limit":"30"]),ReadRequest(path:"/api/inbox/conversations/901/"),ReadRequest(path:"/api/inbox/conversations/901/messages/",query:["limit":"30"])],"Observation added another read/cursor/default query")
    m.closeMessageFiles(expected:presentation);try expect(child.window==nil && child.context==nil,"Close retained observations")
    m.openReply(m.reply.session.context!,expected:m.control);m.reply.update(" Retained unknown observation reply ",input:m.reply.inputControl);m.reply.prepare(expected:m.reply.control);let review=m.reply.session.review!,control=m.reply.control!,send=Task {await m.reply.submit(review,expected:control)};await port.wait(0);await port.resolve(0,.unknown);await send.value;let record=m.reply.submission!;m.reply.close(expected:m.reply.returnControl)
    m.openMessageFiles(expected:m.messageFilesEntryControl(row));await child.load(expected:child.control)
    try expect(child.window?.observation.state == .sent && m.reply.submission==record && m.reply.submissionBlocked && m.reply.retainedAttemptCount==1 && inboxReadSnapshot(m.thread,m.items)==original,"Observed sent/timestamps proved or released/replayed own unknown attempt")
    m.closeMessageFiles(expected:m.messageFilesPresentationControl);await m.retryThread(expected:m.threadSelection);try expect(m.reply.submission==record && m.reply.submissionBlocked && child.window==nil,"Matching bounded reread released unknown or revived observations")
    // A delayed combined source carries observations only to the exact current owner.
    let held=HeldMessageMetadata(),late=InboxViewModel(repository:read,messageFiles:held);await late.load(business:101,epoch:98);await late.open(id:901);let lc=late.messageMetadata!;late.openMessageFiles(expected:late.messageFilesEntryControl(late.thread!.messages[0]));let c=lc.context!,job=Task {await lc.load(expected:lc.control)};await held.waitAnchor(0);let anchor=try await repo.anchor(c);await held.resolveAnchor(0,anchor);await held.waitWindow(0);late.closeMessageFiles(expected:late.messageFilesPresentationControl);late.openReply(late.reply.session.context!,expected:late.control);late.reply.update(" Current peer input ",input:late.reply.inputControl);let peer=late.reply.control
    await held.resolveWindow(0,try await repo.messages(c,anchor:anchor));await job.value
    try expect(lc.window==nil && !lc.presented && late.reply.control==peer && late.reply.session.text==" Current peer input ","Late observation window restored payload or replaced peer input")
    return count
}
