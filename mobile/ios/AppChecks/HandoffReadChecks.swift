import Foundation
import CRMCore

@MainActor func checkHandoffRead(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let data=try Data(contentsOf:directory.appendingPathComponent("inbox-101-901.json"))
    func variant(_ value: Any?,present: Bool=true) throws -> InboxThread {
        var object=try JSONSerialization.jsonObject(with:data) as! [String:Any],conversation=object["conversation"] as! [String:Any]
        if present {conversation["handoff_required"]=value ?? NSNull()} else {conversation.removeValue(forKey:"handoff_required")};object["conversation"]=conversation
        return try JSONDecoder().decode(InboxThread.self,from:JSONSerialization.data(withJSONObject:object))
    }
    let required=try variant(true),notRequired=try variant(false),unknown=try variant(nil,present:false)
    let a=try JSONDecoder().decode(InboxList.self,from:Data(contentsOf:directory.appendingPathComponent("inbox-101.json"))),b=try JSONDecoder().decode(InboxList.self,from:Data(contentsOf:directory.appendingPathComponent("inbox-202.json")))
    let other=try JSONDecoder().decode(InboxThread.self,from:Data(contentsOf:directory.appendingPathComponent("inbox-202-951.json")))
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),unscoped=InboxViewModel(repository:repo)
    await unscoped.load(business:101);await unscoped.open(id:901)
    try expect(unscoped.handoffState==nil,"Unscoped local epoch was treated as authenticated/current read")
    let source=ControlledInbox(),model=InboxViewModel(repository:source)
    let list=Task {await model.load(business:101,epoch:10)};await source.waitPage(0);await source.resolvePage(0,.success(a));await list.value
    try expect(model.handoffState==nil,"Cached list false replaced independent detail")
    let first=Task {await model.open(id:901)};await source.waitThread(0)
    try expect(model.handoffState==nil && model.thread==nil,"Pending detail exposed cached handoff state")
    await source.resolveThread(0,.success(required));await first.value
    try expect(model.handoffState == .required && model.items[0].handoff_required==true,"Fresh true was not consumed from independent response")
    let firstTarget=model.threadSelection!
    let second=Task {await model.open(id:901)};await source.waitThread(1)
    try expect(model.handoffState==nil,"Reload retained prior true while pending")
    await source.resolveThread(1,.success(unknown));await second.value
    try expect(model.handoffState == .unknown && model.items[0].handoff_required==nil,"Fresh unknown fell back to old cached true")
    model.back(expected:firstTarget);await model.retryThread(expected:firstTarget)
    let noExtra=await source.counts()
    try expect(model.threadSelection != firstTarget && model.handoffState == .unknown && noExtra==[1,2],"Stale Back/Retry affected reopened same-ID read")
    let oldTrue=Task {await model.open(id:901)};await source.waitThread(2)
    let freshFalse=Task {await model.open(id:901)};await source.waitThread(3);await source.resolveThread(3,.success(notRequired));await freshFalse.value;await source.resolveThread(2,.success(required));await oldTrue.value
    try expect(model.handoffState == .notRequired,"Old true restored over newer false")
    for (n,failure) in [ReadFailure.denied,.unavailable].enumerated() {
        let failing=Task {await model.open(id:901)};await source.waitThread(4+n);await source.resolveThread(4+n,.failure(failure));await failing.value
        try expect(model.handoffState==nil && model.thread==nil && model.threadFailure==failure,"403/503 was rendered as false/unknown success")
    }
    let leaving=Task {await model.open(id:901)};await source.waitThread(6);model.back();await source.resolveThread(6,.success(required));await leaving.value
    try expect(model.handoffState==nil && model.selectedID==nil,"Back was repopulated by late true")
    let oldEpoch=Task {await model.open(id:901)};await source.waitThread(7)
    let newEpoch=Task {await model.load(business:101,epoch:11)};await source.waitPage(1);await source.resolvePage(1,.success(a));await newEpoch.value;await source.resolveThread(7,.success(required));await oldEpoch.value
    try expect(model.handoffState==nil && model.scopeEpoch==11,"Old same-Business epoch published handoff state")
    let oldBusiness=Task {await model.open(id:901)};await source.waitThread(8)
    let newBusiness=Task {await model.load(business:202,epoch:12)};await source.waitPage(2);await source.resolvePage(2,.success(b));await newBusiness.value
    let openingOther=Task {await model.open(id:951)};await source.waitThread(9);await source.resolveThread(9,.success(other));await openingOther.value;await source.resolveThread(8,.success(required));await oldBusiness.value
    try expect(model.business==202 && model.handoffState == .notRequired && model.thread?.conversation.id==951,"Old Business handoff entered current read")
    let offTab=Task {await model.open(id:951)};await source.waitThread(10);model.reconcileHandoffOwner(business:101,epoch:13);await source.resolveThread(10,.success(other));await offTab.value
    try expect(model.handoffState==nil && model.threadSelection==nil,"Off-tab Business/epoch change failed to revoke pending state")
    let beforeOldRow=await source.counts();await model.open(id:951);let afterOldRow=await source.counts()
    try expect(model.business==nil && model.items.isEmpty && beforeOldRow==afterOldRow,"Old off-tab row could issue a request in revoked owner")
    let recording=SearchTransport(directory),concrete=InboxViewModel(repository:APIReadRepository(transport:recording))
    await concrete.load(business:101,epoch:20);await concrete.open(id:901)
    let readCount=await recording.recorded().count
    let beforeReads=concrete.handoffState,unread=concrete.thread!.conversation.unread_count,messages=concrete.thread!.messages.map(\.id)
    concrete.reply.open(ReplyDraftContext(business:101,conversation:901,epoch:20));let selection=concrete.reply.session.selection!;concrete.reply.update("Manual unsent reply",selection);concrete.reply.prepare(selection)
    try expect(concrete.handoffState==beforeReads && concrete.thread?.conversation.unread_count==unread && concrete.thread?.messages.map(\.id)==messages,"Unsent preview changed handoff/unread/messages")
    try expect(await recording.recorded().count==readCount,"Read badge or unsent draft issued a request")
    return count
}
