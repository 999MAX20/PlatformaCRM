import Foundation
import CRMCore

@MainActor func checkReplyDraft(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws { guard value else { throw ViewModelCheckFailure(message:message) };count += 1 }
    func response(_ status: Any?) throws -> ReadResponse {
        var object=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("inbox-101-901.json"))) as! [String:Any]
        var details=object["details"] as! [String:Any];details["status"]=status;object["details"]=details
        return ReadResponse(status:200,data:try JSONSerialization.data(withJSONObject:object))
    }
    let transport=SearchTransport(directory),model=InboxViewModel(repository:APIReadRepository(transport:transport))
    await model.load(business:101,epoch:4);model.query="Alpha";model.unreadOnly=true;await model.open(id:901)
    let a=ReplyDraftContext(business:101,conversation:901,epoch:4),messages=model.thread!.messages.map(\.id),unread=model.thread!.conversation.unread_count
    let reads=await transport.recorded().count
    model.reply.open(a);let selection=model.reply.session.selection!;model.reply.update("  Synthetic local reply\n",selection);model.reply.prepare(selection)
    try expect(model.reply.session.phase == .review && model.reply.session.review?.text=="Synthetic local reply","Inbox did not reach unsent review")
    try expect(await transport.recorded().count==reads,"Draft/preview issued request")
    try expect(model.thread?.messages.map(\.id)==messages && model.thread?.conversation.unread_count==unread && model.clientLinks?.selectedID==nil,"Draft changed message/unread/client inspector")
    model.reply.back(selection);model.reply.back(selection);model.back()
    try expect(model.query=="Alpha" && model.unreadOnly && model.reply.session.text.isEmpty,"Back lost list context or retained visible text")
    await model.open(id:902);try expect(model.reply.session.text.isEmpty,"Another Conversation inherited text")
    await model.open(id:901);try expect(model.reply.session.text=="  Synthetic local reply\n","Verified same thread failed to restore manual input")
    for status: Any? in ["closed","archived","unknown",nil] {
        await transport.override("/api/mobile/v1/inbox/901/",try response(status));await model.open(id:901);model.reply.open(a)
        try expect(!model.reply.session.available && model.reply.session.selection==nil && model.reply.session.text.isEmpty,"Closed/missing/unknown state allowed draft")
    }
    await transport.override("/api/mobile/v1/inbox/901/",try response(1));await model.open(id:901)
    try expect(model.thread==nil && model.threadFailure == .invalidPayload && !model.reply.session.available,"Malformed source status accepted")
    await model.open(id:901);model.reply.open(a);let current=model.reply.session.selection!
    model.reply.update("Retain on failure",current)
    await transport.override("/api/mobile/v1/inbox/901/",ReadResponse(status:403,data:Data()));await model.open(id:901)
    try expect(model.thread==nil && model.reply.session.text.isEmpty && model.reply.session.selection==nil,"Denied reread retained route/input")
    await model.open(id:901);try expect(model.reply.session.text=="Retain on failure","Recoverable reread lost manual buffer")
    await transport.holdDetails();let pending=Task { await model.open(id:901) };await transport.wait(0)
    await model.load(business:202,epoch:5)
    model.reply.update("late",current);model.reply.close(current)
    await transport.resolve(0,try response("open"));await pending.value
    try expect(model.business==202 && model.thread==nil && model.reply.session.context==nil,"Late old Business read restored composer")
    try expect(model.reply.session.text.isEmpty,"New Business inherited draft")
    model.clear();try expect(model.reply.session.context==nil,"Clear retained private draft context")
    return count
}
