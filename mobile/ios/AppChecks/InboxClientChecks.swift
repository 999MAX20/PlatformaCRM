import Foundation
import CRMCore

@MainActor func checkInboxClient(directory: URL) async throws -> Int {
    var count = 0, next = 0
    func expect(_ value: Bool,_ message: String) throws { guard value else { throw ViewModelCheckFailure(message: message) }; count += 1 }
    func response(_ name: String,change: ((inout [String:Any]) -> Void)? = nil) throws -> ReadResponse {
        var data = try Data(contentsOf:directory.appendingPathComponent(name+".json"))
        if let change { var object = try JSONSerialization.jsonObject(with:data) as! [String:Any]; change(&object); data = try JSONSerialization.data(withJSONObject:object) }
        return ReadResponse(status:200,data:data)
    }
    let transport = SearchTransport(directory), repo = APIReadRepository(transport:transport), model = InboxViewModel(repository:repo)
    let links = model.clientLinks!
    for (business,id,client,task) in [(101,901,701,1401),(202,951,801,2401)] {
        await model.load(business:business); model.query = "response"; model.unreadOnly = true; await model.open(id:id)
        let request = links.request!, messages = model.thread!.messages.map(\.id), before = await transport.recorded().count
        try expect(links.profile.detail == nil && links.selectedID == nil,"Thread auto-loaded Client contacts")
        await links.open(expected:request)
        try expect(links.profile.detail?.client.id == client && !links.loading,"Explicit Client independently read failed")
        let recorded = await transport.recorded()
        try expect(recorded.count == before + 2 && recorded.suffix(2).map(\.path) == ["/api/mobile/v1/inbox/\(id)/","/api/mobile/v1/clients/\(client)/"],"Client action did not revalidate thread then GET independent profile")
        await links.profile.work!.open(.task(task)); try expect(links.profile.work?.detail != nil,"Inbox Client work nested read failed")
        links.profile.work?.back(); try expect(links.selectedID == client && links.profile.detail != nil,"Nested work Back closed Client or thread")
        links.back(expected:request)
        try expect(links.profile.detail == nil && links.profile.work?.parent == nil && model.thread?.messages.map(\.id) == messages && model.selectedID == id,"Client Back lost thread or retained dependent profile/work")
        try expect(model.query == "response" && model.unreadOnly && model.thread?.conversation.unread_count == (business == 101 ? 2 : 1),"Client read changed Inbox query/unread state")
        model.back(); try expect(links.request == nil && model.selectedID == nil,"Thread Back retained child context")
    }
    await model.load(business:101); await model.open(id:902)
    let noClientBefore = await transport.recorded().count
    await links.open()
    try expect(await transport.recorded().count == noClientBefore && links.selectedID == nil,"Unlinked thread inferred a Client")
    await model.open(id:901); await transport.holdDetails()
    func begin(_ expected: InboxReadSelection? = nil) async -> (Task<Void,Never>,Int) {
        let index = next; next += 1; let pending = Task { await links.open(expected:expected) }; await transport.wait(index); return (pending,index)
    }
    func allow(_ index: Int) async throws -> Int {
        let clientIndex = next; next += 1; await transport.resolve(index,try response("inbox-101-901")); await transport.wait(clientIndex); return clientIndex
    }
    func target(_ reply: ReadResponse) async throws {
        let (pending,index) = await begin(); let clientIndex = try await allow(index); await transport.resolve(clientIndex,reply); await pending.value
    }
    for reply in [ReadResponse(status:403,data:Data()),try response("client-101-702"),try response("client-202-801")] {
        try await target(reply)
        try expect(links.profile.detail == nil && links.profile.failure != nil && model.thread?.conversation.id == 901,"Denied/wrong/foreign Client fell back to thread contacts or erased parent")
        links.back()
    }
    try await target(try response("client-101-701") { object in var client = object["client"] as! [String:Any]; client["phone"] = NSNull(); client["email"] = NSNull(); object["client"] = client })
    try expect(links.profile.detail?.client.phone == nil && links.profile.detail?.client.email == nil,"Profile reconstructed withheld contacts from source thread")
    links.back()
    for reference in [NSNull(),["id":702]] as [Any] {
        let (pending,index) = await begin(); await transport.resolve(index,try response("inbox-101-901") { $0["details"] = ["client":reference] }); await pending.value
        try expect(links.profile.detail == nil && links.selectedID == nil && model.thread?.clientReferenceID == (reference is NSNull ? nil : 702),"Changed/withheld parent relation left old Client route")
        // Restore a new independent parent generation through the normal thread route.
        let parentIndex = next; next += 1; let parent = Task { await model.open(id:901) }; await transport.wait(parentIndex); await transport.resolve(parentIndex,try response("inbox-101-901")); await parent.value
    }
    let (old,oldIndex) = await begin(); links.back()
    let (newer,newIndex) = await begin(); let currentClient = try await allow(newIndex)
    await transport.resolve(oldIndex,ReadResponse(status:403,data:Data())); await old.value
    await transport.resolve(currentClient,try response("client-101-701")); await newer.value
    try expect(links.profile.detail != nil && model.threadFailure == nil,"Late old thread denial erased current route/body")
    links.back()
    let (closing,closingIndex) = await begin(); let oldClient = try await allow(closingIndex); links.back()
    let (reopened,reopenIndex) = await begin(); let newClient = try await allow(reopenIndex)
    await transport.resolve(newClient,try response("client-101-701") { object in var client = object["client"] as! [String:Any]; client["phone"] = NSNull(); object["client"] = client }); await reopened.value
    await transport.resolve(oldClient,try response("client-101-701")); await closing.value
    try expect(links.profile.detail?.client.phone == nil && links.selectedID == 701,"Old profile success restored contacts after Back/reopen")
    links.back()
    let stale = links.request!, beforeRefresh = await transport.recorded().count
    let (refreshing,index) = await begin(stale); let pendingClient = try await allow(index)
    let parentIndex = next; next += 1; let parent = Task { await model.open(id:901) }; await transport.wait(parentIndex); await transport.resolve(parentIndex,try response("inbox-101-901")); await parent.value
    await transport.resolve(pendingClient,try response("client-101-701")); await refreshing.value
    try expect(links.profile.detail == nil && links.request != stale,"Thread refresh accepted old Client response")
    let afterRefresh = await transport.recorded().count; await links.open(expected:stale)
    let afterStale = await transport.recorded().count
    try expect(afterRefresh > beforeRefresh && afterRefresh == afterStale && !links.back(expected:stale),"Stale UI started/closed new thread Client route")
    let (cancelled,cancelIndex) = await begin(); await transport.cancel(cancelIndex); await cancelled.value
    try expect(links.selectedID == nil && model.thread != nil && model.threadFailure == nil,"Cancelled parent revalidation erased independent thread")
    let (foreign,foreignIndex) = await begin(); await transport.resolve(foreignIndex,try response("inbox-202-951")); await foreign.value
    try expect(model.thread == nil && model.threadFailure == .invalidPayload && links.profile.detail == nil && links.selectedID == nil,"Foreign parent revalidation kept stale dialogue or contacts")
    let restoreIndex = next; next += 1; let restore = Task { await model.open(id:901) }; await transport.wait(restoreIndex); await transport.resolve(restoreIndex,try response("inbox-101-901")); await restore.value
    let (switching,switchIndex) = await begin(); let switchClient = try await allow(switchIndex); await model.load(business:202)
    await transport.resolve(switchClient,try response("client-101-701")); await switching.value
    try expect(model.business == 202 && links.profile.detail == nil && links.request == nil && model.thread == nil,"Business change accepted previous Client contacts")
    return count
}
