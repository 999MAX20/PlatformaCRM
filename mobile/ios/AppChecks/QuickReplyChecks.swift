import Foundation
import CRMCore

actor ControlledQuickReplies: QuickReplyRepository {
    private let fixture: FixtureQuickReplyRepository
    private var calls: [String]=[]
    private var held=false,next=0
    private var pending: [Int:CheckedContinuation<QuickReplyPage,any Error>]=[:]
    private var waiters: [Int:CheckedContinuation<Void,Never>]=[:]
    private var nextResult: Result<QuickReplyPage,ReadFailure>?
    init(_ directory: URL) {fixture=FixtureQuickReplyRepository(directory:directory)}
    func hold(_ value: Bool) {held=value}
    func set(_ result: Result<QuickReplyPage,ReadFailure>) {nextResult=result}
    func quickReplies(business: Int,channel: String) async throws -> QuickReplyPage {
        calls.append("\(business):\(channel)")
        if let result=nextResult {nextResult=nil;return try result.get()}
        if held {let index=next;next += 1;return try await withCheckedThrowingContinuation {pending[index]=$0;waiters.removeValue(forKey:index)?.resume()}}
        return try await fixture.quickReplies(business:business,channel:channel)
    }
    func recorded() -> [String] {calls}
    func wait(_ index: Int) async {if pending[index]==nil {await withCheckedContinuation {waiters[index]=$0}}}
    func resolve(_ index: Int,_ result: Result<QuickReplyPage,ReadFailure>) {
        let continuation=pending.removeValue(forKey:index)!
        switch result {case .success(let page):continuation.resume(returning:page);case .failure(let error):continuation.resume(throwing:error)}
    }
}

@MainActor func checkQuickReplies(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func page(_ business: Int=101,_ channel: String="website") async throws -> QuickReplyPage {try await FixtureQuickReplyRepository(directory:directory).quickReplies(business:business,channel:channel)}
    func thread(_ channel: String?) throws -> ReadResponse {
        var object=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("inbox-101-901.json"))) as! [String:Any]
        var conversation=object["conversation"] as! [String:Any];conversation["channel"]=channel;object["conversation"]=conversation
        return ReadResponse(status:200,data:try JSONSerialization.data(withJSONObject:object))
    }
    let transport=SearchTransport(directory),source=ControlledQuickReplies(directory),model=InboxViewModel(repository:APIReadRepository(transport:transport),quickReplies:source)
    let reply=model.reply,picker=reply.quickReplies!,a=ReplyDraftContext(business:101,conversation:901,epoch:50)
    await model.load(business:101,epoch:50);await model.open(id:901);reply.open(a);var parent=reply.session.selection!
    reply.update("  Operator note \n",parent)
    let reads=await transport.recorded().count,messages=model.thread!.messages.map(\.id),unread=model.thread!.conversation.unread_count
    await reply.openQuickReplies(parent);let first=picker.session.selection!
    try expect(picker.session.choices.map(\.id)==[9101,9102,9103] && reply.session.text=="  Operator note \n","Opening picker mutated draft or wrong source order")
    try expect(await source.recorded()==["101:website"],"Catalogue invented Conversation query or ignored current Business/channel")
    try expect(await transport.recorded().count==reads,"Fixture picker invoked a web/mobile transport request")
    let staleChoice=picker.session.choices[0]
    picker.search("appointments",first)
    try expect(picker.session.choices.map(\.id)==[9102] && !reply.insert(staleChoice,expected:parent),"Local category filter or stale row guard missing")
    let filteredChoice=picker.session.choices[0];reply.back(parent)
    try expect(picker.session.selection==nil && reply.session.selection==parent && reply.session.phase == .editing && reply.session.text=="  Operator note \n","Layered Back closed composer or changed text")
    await reply.openQuickReplies(parent);let reopened=picker.session.selection!
    try expect(reopened != first && picker.session.query=="appointments" && !reply.insert(filteredChoice,expected:parent),"Cancel/reopen retained actionable old row or lost own filter")
    let choice=picker.session.choices[0]
    try expect(reply.insert(choice,expected:parent),"Current selected template failed insertion")
    let inserted=reply.session.text,oldParent=parent;parent=reply.session.selection!
    try expect(inserted=="  Operator note\n"+choice.template.text && parent != oldParent && picker.session.selection==nil,"Insertion did not follow exact JS append/close/new-editor generation")
    reply.update("late old input",oldParent)
    try expect(!reply.insert(choice,expected:oldParent) && reply.session.text==inserted,"Old editor or double template click overwrote text")
    try expect(model.thread?.messages.map(\.id)==messages && model.thread?.conversation.unread_count==unread && model.clientLinks?.selectedID==nil,"Insert changed messages/unread/Client inspector")
    try expect(await transport.recorded().count==reads,"Insert triggered send/read/handoff or another API request")
    reply.prepare(parent);let calls=await source.recorded().count;await reply.openQuickReplies(parent)
    try expect(reply.session.phase == .review && picker.session.context==nil && reply.session.text==inserted,"Review allowed picker or lost raw draft")
    try expect(await source.recorded().count==calls,"Review fetched templates")
    reply.back(parent);await source.set(.failure(.denied));await reply.openQuickReplies(parent);let denied=picker.session.selection!
    try expect(picker.session.failure == .denied && picker.session.choices.isEmpty && !picker.session.showsEmpty && reply.session.text==inserted,"Denied template read altered draft or fell back")
    await picker.retry(denied);try expect(picker.session.failure==nil && picker.session.loaded && reply.session.text==inserted,"Catalogue retry did not preserve draft")
    picker.close(denied)
    let empty=try await page(202,"instagram");await source.set(.success(empty));await reply.openQuickReplies(parent)
    try expect(picker.session.showsEmpty && reply.session.text==inserted,"Confirmed empty catalogue lost input")
    reply.back(parent)
    await transport.override("/api/mobile/v1/inbox/901/",try thread("email"));await model.open(id:901);reply.open(a);let unknown=reply.session.selection!
    let callsBeforeUnknown=await source.recorded().count;await reply.openQuickReplies(unknown)
    try expect(picker.session.context==nil && reply.session.text==inserted,"Unknown channel exposed templates or erased own draft")
    try expect(await source.recorded().count==callsBeforeUnknown,"Unknown Conversation channel read a guessed catalogue")
    await transport.override("/api/mobile/v1/inbox/901/",try thread("website"));await model.open(id:901);reply.open(a);parent=reply.session.selection!
    await source.hold(true)
    let oldChannel=Task {await reply.openQuickReplies(parent)};await source.wait(0)
    await transport.override("/api/mobile/v1/inbox/901/",try thread("telegram"));await model.open(id:901);reply.open(a);parent=reply.session.selection!
    await source.resolve(0,.success(try await page()));await oldChannel.value
    try expect(picker.session.context?.channel=="telegram" && !picker.session.loaded && reply.session.text==inserted,"Late old-channel catalogue survived revalidation")
    let oldBusiness=Task {await reply.openQuickReplies(parent)};await source.wait(1)
    await model.load(business:202,epoch:51);await source.resolve(1,.success(try await page(101,"telegram")));await oldBusiness.value
    try expect(reply.session.context==nil && picker.session.context==nil && reply.session.text.isEmpty,"Business switch retained draft/catalogue")
    await model.open(id:951);let b=ReplyDraftContext(business:202,conversation:951,epoch:51);reply.open(b);parent=reply.session.selection!
    await source.hold(false);await reply.openQuickReplies(parent)
    try expect(picker.session.choices.map(\.id)==[9202],"Business B inherited Business A templates")
    reply.back(parent)
    await model.load(business:101,epoch:52);await model.open(id:901);let c=ReplyDraftContext(business:101,conversation:901,epoch:52);reply.open(c);parent=reply.session.selection!;reply.update("Private A",parent)
    await source.hold(true);let oldConversation=Task {await reply.openQuickReplies(parent)};await source.wait(2)
    await model.open(id:902);let other=ReplyDraftContext(business:101,conversation:902,epoch:52);reply.open(other)
    await source.resolve(2,.success(try await page()));await oldConversation.value
    try expect(reply.session.context==other && reply.session.text.isEmpty && !picker.session.loaded,"Same-Business/channel old Conversation catalogue leaked")
    await model.open(id:901);reply.open(c);parent=reply.session.selection!
    try expect(reply.session.text=="Private A","Returning to own verified dialogue lost draft")
    let closing=Task {await reply.openQuickReplies(parent)};await source.wait(3);let closedParent=parent
    reply.close(closedParent);reply.open(c);parent=reply.session.selection!
    await source.resolve(3,.success(try await page()));await closing.value
    try expect(parent != closedParent && !picker.session.loaded && reply.session.text=="Private A","Old closed editor catalogue reached reopened editor")
    await source.hold(false);await reply.openQuickReplies(parent);let active=picker.session.selection!,snapshot=picker.session.choices[0]
    picker.search("Alpha",active)
    try expect(!reply.insert(snapshot,expected:parent) && reply.session.text=="Private A","Old filter-generation choice remained active")
    picker.search("",active);let beforeReload=picker.session.choices[0]
    await source.hold(true);let reload=Task {await picker.retry(active)};await source.wait(4)
    try expect(!reply.insert(beforeReload,expected:parent) && reply.session.text=="Private A","Reload retained actionable old catalogue")
    var object=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("quick-replies-101-website.json"))) as! [String:Any];var rows=object["results"] as! [[String:Any]];rows[0]["text"]="New fixture body {{client}}";object["results"]=rows
    let newPage=try JSONDecoder().decode(QuickReplyPage.self,from:JSONSerialization.data(withJSONObject:object));await source.resolve(4,.success(newPage));await reload.value
    try expect(!reply.insert(beforeReload,expected:parent),"Old same-ID template snapshot inserted after reload")
    try expect(reply.insert(picker.session.choices[0],expected:parent) && reply.session.text=="Private A\nNew fixture body {{client}}","Current template text was not inserted literally")
    model.back();try expect(picker.session.context==nil && reply.session.text.isEmpty,"Thread Back retained visible catalogue/draft")
    return count
}
