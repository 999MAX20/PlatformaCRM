import Foundation
import CRMCore

actor InboxWindowTransport:ReadTransport {
    let fixture:FixtureTransport
    private var requests:[ReadRequest]=[],paths:Set<String>=[],next=0
    private var pending:[Int:CheckedContinuation<ReadResponse,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    private var overrides:[String:ReadResponse]=[:]
    init(_ directory:URL) {fixture=FixtureTransport(directory:directory)}
    func hold(_ paths:Set<String>) {self.paths=paths}
    func override(_ path:String,_ response:ReadResponse) {overrides[path]=response}
    func get(_ request:ReadRequest) async throws -> ReadResponse {
        requests.append(request)
        if let response=overrides.removeValue(forKey:request.path) {return response}
        if paths.contains(request.path) {let index=next;next += 1;return try await withCheckedThrowingContinuation {pending[index]=$0;waiters.removeValue(forKey:index)?.resume()}}
        return try await fixture.get(request)
    }
    func wait(_ index:Int) async {if pending[index]==nil {await withCheckedContinuation {waiters[index]=$0}}}
    func resolve(_ index:Int,_ response:ReadResponse) {pending.removeValue(forKey:index)!.resume(returning:response)}
    func recorded()->[ReadRequest] {requests}
}

@MainActor func checkInboxListThreadControls(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func response(_ name:String)->ReadResponse {ReadResponse(status:200,data:try! Data(contentsOf:directory.appendingPathComponent(name+".json")))}
    let listPath="/api/mobile/v1/inbox/",threadPath="/api/mobile/v1/inbox/901/"
    let transport=InboxWindowTransport(directory),model=InboxViewModel(repository:APIReadRepository(transport:transport))
    await model.load(business:101,epoch:120);let input=model.listInputControl!,initial=model.listControl!,reads=await transport.recorded().count
    model.search("res",input:input);model.search("response",input:input)
    try expect(model.query=="response" && model.listInputControl==input && model.visible.map(\.id)==[901],"Continuous Inbox input was invalidated mid-typing or changed bounded search")
    let searched=model.listControl!;model.search("Synthetic",input:input);model.search("response",input:input);await model.open(id:901,list:searched);await model.retryList(list:initial)
    try expect(await transport.recorded().count==reads && model.selectedID==nil && model.query=="response","Old query-window row/retry acted after ABA query")
    let filter=model.listControl!;model.filterUnread(true,list:filter);model.filterUnread(false,list:model.listControl);model.filterUnread(true,list:filter)
    try expect(!model.unreadOnly && model.listInputControl==input,"Old filter callback revalidated after ABA or broke continuous input")
    model.query="";model.unreadOnly=true;let unread=model.listControl!;await model.open(id:902,list:unread)
    try expect(model.selectedID==nil && model.visible.map(\.id)==[901],"Current filtered-out row bypassed local visibility")
    model.unreadOnly=false;model.query="response";let refresh=model.listControl!,beforeRefresh=await transport.recorded().count
    await transport.hold([listPath]);let refreshing=Task {await model.retryList(list:refresh)};await transport.wait(0)
    model.search("late stale input",input:input);await model.retryList(list:refresh);await model.open(id:901,list:refresh)
    try expect(model.listControl==nil && model.listInputControl==nil && model.query=="response","Pending list accepted old input/actions")
    try expect(await transport.recorded().count==beforeRefresh+1,"Pending list Retry started duplicate request")
    await transport.resolve(0,response("inbox-101"));await refreshing.value;try expect(model.listInputControl != input && model.query=="response","Same-owner refresh revived old input or lost query")
    // Failure list still permits local input and only its current window can retry.
    await transport.hold([]);await transport.override(listPath,ReadResponse(status:403,data:Data()));await model.retryList(list:model.listControl)
    let denied=model.listControl!,deniedInput=model.listInputControl!;model.search("Beta",input:deniedInput);let failedReads=await transport.recorded().count;await model.retryList(list:denied)
    try expect(model.failure == .denied && model.selectedID==nil && model.query=="Beta","Failed-list local input was lost")
    try expect(await transport.recorded().count==failedReads,"Old failed-list Retry ignored changed query window")
    await model.retryList(list:model.listControl);try expect(model.failure==nil && model.query=="Beta" && model.visible.map(\.id)==[902],"Current failed-list Retry failed to retain bounded filter")
    model.search("response",input:model.listInputControl);await transport.override(threadPath,ReadResponse(status:403,data:Data()));await model.open(id:901,list:model.listControl)
    let retry=model.threadRetryControl!,listBefore=model.listControl;try expect(listBefore==nil && model.threadFailure == .denied,"Failed selected thread leaked list controls")
    await transport.hold([threadPath]);let retrying=Task {await model.retryThread(control:retry)};await transport.wait(1);let pending=await transport.recorded().count
    await model.retryThread(control:retry);await model.retryThread(control:model.threadRetryControl)
    try expect(model.threadRetryControl==nil && model.threadLoading,"Pending thread exposed another Retry")
    try expect(await transport.recorded().count==pending,"Duplicate pending thread retry started request")
    await transport.resolve(1,response("inbox-101-901"));await retrying.value;let done=await transport.recorded().count;await model.retryThread(control:retry)
    try expect(await transport.recorded().count==done && model.thread?.conversation.id==901 && model.threadRetryControl==nil,"Old failure Retry acted on current successful thread")
    let context=ReplyDraftContext(business:101,conversation:901,epoch:120);model.openReply(context,expected:model.control);model.reply.update("Private retained",input:model.reply.inputControl)
    await model.retryThread(control:retry);model.search("hidden",input:deniedInput)
    try expect(model.reply.session.text=="Private retained" && model.query=="response" && model.listControl==nil,"Old list/retry affected Reply sibling")
    model.reply.close(expected:model.reply.returnControl);model.backToThreadList(expected:model.returnControl);let oldEpoch=model.listControl!,oldInput=model.listInputControl!
    await transport.hold([]);await model.load(business:101,epoch:121);model.search("old epoch",input:oldInput);await model.open(id:901,list:oldEpoch)
    try expect(model.query=="" && model.selectedID==nil && model.scopeEpoch==121,"Same-Business new epoch accepted prior list controls")
    // A late detail failure may not install retry UI on a different Business owner.
    await transport.hold([threadPath]);let late=Task {await model.open(id:901,list:model.listControl)};await transport.wait(2);await model.load(business:202,epoch:122)
    await transport.resolve(2,ReadResponse(status:403,data:Data()));await late.value
    try expect(model.business==202 && model.selectedID==nil && model.threadRetryControl==nil && model.failure==nil,"Late old detail installed Retry on replacement Business")
    // Partial/no-match stays a bounded projection, never an authoritative global empty.
    var object=try JSONSerialization.jsonObject(with:response("inbox-101").data) as! [String:Any];var summary=object["summary"] as! [String:Any];summary["open"]=3;object["summary"]=summary
    await transport.override(listPath,ReadResponse(status:200,data:try JSONSerialization.data(withJSONObject:object)));await model.load(business:101,epoch:123);model.search("absent",input:model.listInputControl)
    try expect(model.partial && model.visible.isEmpty && !model.showsEmpty,"Partial Inbox search asserted complete global absence")
    count += try await checkInboxRawUnicodeWindows(directory:directory)
    return count
}

// Test projection of every existing conversation field; retain nil/preview presence and exact string bytes.
private struct InboxRawConversationSnapshot:Equatable {
    let id:Int,title:[UInt8]?,channel:[UInt8]?,unread:Int,previewPresent:Bool,previewText:[UInt8]?,handoffRequired:Bool?
    init(_ row:InboxConversation) {id=row.id;title=row.title.map {Array($0.utf8)};channel=row.channel.map {Array($0.utf8)};unread=row.unread_count;previewPresent=row.last_message_preview != nil;previewText=row.last_message_preview?.text.map {Array($0.utf8)};handoffRequired=row.handoff_required}
}
@MainActor private func checkInboxRawUnicodeWindows(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let cases=(try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("inbox-list-raw-unicode-cases.json"))) as! [String:Any])["cases"] as! [[String:Any]]
    let path="/api/mobile/v1/inbox/"
    for (index,row) in cases.enumerated() {
        let data=Data((row["list_json"] as! String).utf8),page=try JSONDecoder().decode(InboxList.self,from:data),response=ReadResponse(status:200,data:data),before=row["before"] as! String,after=row["after"] as! String,changed=row["changed"] as! Bool,partial=row["partial"] as! Bool
        let source=InboxWindowTransport(directory),model=InboxViewModel(repository:APIReadRepository(transport:source)),epoch=1900+index
        await source.override(path,response);await model.load(business:101,epoch:epoch);let input=model.listInputControl!
        model.search(before,input:input);let old=model.listControl!;model.search(after,input:input);let current=model.listControl!
        try expect(model.query.utf8.elementsEqual(after.utf8) && model.listInputControl==input,"Inbox lost raw Unicode query or continuous input")
        try expect((current != old)==changed && model.visible.map(\.id)==[901],"Canonical Unicode raw change kept old Inbox action window or filtered source rows")
        let reads=await source.recorded()
        if changed {model.filterUnread(true,list:old);await model.open(id:901,list:old);await model.retryList(list:old)}
        let unchangedReads=await source.recorded();try expect(!model.unreadOnly && model.selectedID==nil && unchangedReads==reads,"Old changed-query filter/open/retry acted on same visible row")
        try expect(model.items.map(InboxRawConversationSnapshot.init)==page.items.map(InboxRawConversationSnapshot.init) && model.total==page.summary.open && model.partial==partial && model.thread==nil,"Local raw filter changed source/count/partial/thread")
        let filter=model.listControl!;model.filterUnread(true,list:filter);model.filterUnread(false,list:filter)
        try expect(model.unreadOnly && model.visible.map(\.id)==[901] && model.listInputControl==input,"Current unread filter failed or old filter callback remained current")
        model.filterUnread(false,list:model.listControl);try expect(!model.unreadOnly && model.query.utf8.elementsEqual(after.utf8),"Current unread filter changed raw query")
        await model.open(id:901,list:model.listControl);try expect(model.thread?.conversation.id==901 && model.listControl==nil && model.listInputControl==nil,"Current exact-query row failed explicit detail read")
        let detail=try JSONDecoder().decode(InboxThread.self,from:Data(contentsOf:directory.appendingPathComponent("inbox-101-901.json"))),expectedReadItems=page.items.map {$0.id==901 ? detail.conversation:$0},openedItems=model.items.map(InboxRawConversationSnapshot.init)
        try expect(openedItems==expectedReadItems.map(InboxRawConversationSnapshot.init),"Explicit current detail read did not project its own conversation fields")
        model.search("hidden overwrite",input:input);try expect(model.query.utf8.elementsEqual(after.utf8),"Old list input overwrote query while detail owned route")
        model.backToThreadList(expected:model.returnControl);let afterBack=model.listInputControl!;model.search("old input after back",input:input)
        try expect(afterBack != input && model.query.utf8.elementsEqual(after.utf8) && model.items.map(InboxRawConversationSnapshot.init)==openedItems,"Detail Back revived old raw input or changed independently read source")
        model.search("__absent_unicode_window_fixture__",input:afterBack)
        try expect(model.visible.isEmpty && model.showsEmpty == !partial && model.total==page.summary.open,"Bounded local filter invented global empty/completeness")
        let refresh=model.listControl!,priorInput=model.listInputControl!;await source.override(path,response);await model.retryList(list:refresh)
        try expect(model.query=="__absent_unicode_window_fixture__" && model.listInputControl != priorInput && model.items.map(InboxRawConversationSnapshot.init)==page.items.map(InboxRawConversationSnapshot.init) && model.partial==partial,"Explicit list refresh lost raw filter/revived old input/replaced source counts")
        let priorWindow=model.listControl!,prior=model.listInputControl!;await source.override(path,response);await model.load(business:101,epoch:epoch+100)
        let afterEpochReads=await source.recorded();model.search("old epoch",input:prior);model.filterUnread(true,list:priorWindow);await model.open(id:901,list:priorWindow);await model.retryList(list:priorWindow)
        let finalReads=await source.recorded();try expect(model.query.isEmpty && !model.unreadOnly && model.selectedID==nil && model.scopeEpoch==epoch+100 && finalReads==afterEpochReads,"New epoch reused old Inbox query/action window")
    }
    return count
}
