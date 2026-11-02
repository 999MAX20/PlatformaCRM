import Foundation
import CRMCore

actor ControlledInbox: InboxRepository {
    private var pages: [Int: CheckedContinuation<InboxList, any Error>] = [:]
    private var threads: [Int: CheckedContinuation<InboxThread, any Error>] = [:]
    private var pageWaiters: [Int: CheckedContinuation<Void, Never>] = [:]
    private var threadWaiters: [Int: CheckedContinuation<Void, Never>] = [:]
    private var pageCount = 0, threadCount = 0
    func inbox(business: Int) async throws -> InboxList {
        let id = pageCount; pageCount += 1
        return try await withCheckedThrowingContinuation { pages[id] = $0; pageWaiters.removeValue(forKey: id)?.resume() }
    }
    func thread(business: Int, id: Int) async throws -> InboxThread {
        let request = threadCount; threadCount += 1
        return try await withCheckedThrowingContinuation { threads[request] = $0; threadWaiters.removeValue(forKey: request)?.resume() }
    }
    func waitPage(_ id: Int) async { if pages[id] == nil { await withCheckedContinuation { pageWaiters[id] = $0 } } }
    func waitThread(_ id: Int) async { if threads[id] == nil { await withCheckedContinuation { threadWaiters[id] = $0 } } }
    func resolvePage(_ id: Int, _ result: Result<InboxList, ReadFailure>) {
        let continuation = pages.removeValue(forKey: id)!
        switch result { case .success(let value): continuation.resume(returning: value); case .failure(let error): continuation.resume(throwing: error) }
    }
    func resolveThread(_ id: Int, _ result: Result<InboxThread, ReadFailure>) {
        let continuation = threads.removeValue(forKey: id)!
        switch result { case .success(let value): continuation.resume(returning: value); case .failure(let error): continuation.resume(throwing: error) }
    }
    func counts() -> [Int] { [pageCount, threadCount] }
    func cancelThread(_ id: Int) { threads.removeValue(forKey: id)!.resume(throwing: CancellationError()) }
    func cancelPage(_ id: Int) { pages.removeValue(forKey: id)!.resume(throwing: CancellationError()) }
}

@MainActor func checkInbox(directory: URL) async throws -> Int {
    func fixture<T: Decodable>(_ name: String, as type: T.Type) throws -> T {
        try JSONDecoder().decode(type, from: Data(contentsOf: directory.appendingPathComponent(name + ".json")))
    }
    let a = try fixture("inbox-101", as: InboxList.self), b = try fixture("inbox-202", as: InboxList.self)
    let detail = try fixture("inbox-101-901", as: InboxThread.self)
    let source = ControlledInbox()
    let inbox = InboxViewModel(repository: source)
    var count = 0
    func expect(_ condition: Bool, _ message: String) throws { guard condition else { throw ViewModelCheckFailure(message: message) }; count += 1 }
    let loading = Task { await inbox.load(business: 101) }; await source.waitPage(0)
    try expect(inbox.loading && !inbox.showsEmpty, "Pending Inbox was called empty")
    await source.resolvePage(0, .success(a)); await loading.value
    inbox.query = " ALPHA "; inbox.unreadOnly = true
    try expect(inbox.visible.map(\.id) == [901], "Local title/unread filter failed")
    inbox.query = "operator response"
    try expect(inbox.visible.map(\.id) == [901], "Local preview search failed")
    inbox.query = "Alpha"
    let opening = Task { await inbox.open(id: 901) }; await source.waitThread(0)
    await source.resolveThread(0, .success(detail)); await opening.value
    try expect(inbox.thread?.conversation.unread_count == 2, "Opening implicitly marked read")
    inbox.back()
    try expect(inbox.query == "Alpha" && inbox.unreadOnly && inbox.visible.map(\.id) == [901], "Back lost list/search/filter")
    await inbox.open(id: 999)
    let localCounts = await source.counts()
    try expect(localCounts == [1,1] && inbox.selectedID == nil, "Local filters/unknown ID issued requests")

    let oldVisit = Task { await inbox.open(id: 901) }; await source.waitThread(1); inbox.back()
    let reopened = Task { await inbox.open(id: 901) }; await source.waitThread(2)
    await source.resolveThread(1, .success(detail)); await oldVisit.value
    try expect(inbox.thread == nil && inbox.threadLoading, "Old visit entered reopened thread")
    var redactedJSON = try JSONSerialization.jsonObject(with: Data(contentsOf: directory.appendingPathComponent("inbox-101-901.json"))) as! [String: Any]
    var header = redactedJSON["conversation"] as! [String: Any]; header["title"] = NSNull(); redactedJSON["conversation"] = header
    var messages = redactedJSON["messages"] as! [[String: Any]]; messages[0]["text"] = NSNull(); redactedJSON["messages"] = messages
    let redacted = try JSONDecoder().decode(InboxThread.self, from: JSONSerialization.data(withJSONObject: redactedJSON))
    await source.resolveThread(2, .success(redacted)); await reopened.value; inbox.back()
    try expect(inbox.items[0].title == nil && inbox.items[0].last_message_preview == nil, "Fresh withheld header restored old preview")

    let failed = Task { await inbox.open(id: 901) }; await source.waitThread(3)
    await source.resolveThread(3, .failure(.unavailable)); await failed.value
    try expect(inbox.threadFailure == .unavailable && inbox.query == "Alpha", "Thread failure lost context")
    let retry = Task { await inbox.open(id: 901) }; await source.waitThread(4)
    await source.resolveThread(4, .success(detail)); await retry.value
    try expect(inbox.threadFailure == nil && inbox.thread?.messages.count == 2, "Thread retry did not recover")

    let staleThread = Task { await inbox.open(id: 901) }; await source.waitThread(5)
    let staleList = Task { await inbox.load(business: 101) }; await source.waitPage(1)
    let other = Task { await inbox.load(business: 202) }; await source.waitPage(2)
    try expect(inbox.items.isEmpty && inbox.selectedID == nil && inbox.query.isEmpty && !inbox.unreadOnly, "Business switch retained prior Inbox data")
    await source.resolvePage(2, .success(b)); await other.value
    await source.resolvePage(1, .success(a)); await staleList.value
    await source.resolveThread(5, .failure(.denied)); await staleThread.value
    try expect(inbox.items.map(\.id) == [951] && inbox.thread == nil && inbox.threadFailure == nil, "Late old Business result entered current scope")

    let denied = Task { await inbox.load(business: 101) }; await source.waitPage(3); inbox.query = "Alpha"; inbox.unreadOnly = true
    await source.resolvePage(3, .failure(.denied)); await denied.value
    try expect(inbox.failure == .denied && !inbox.showsEmpty && inbox.query == "Alpha" && inbox.unreadOnly, "Denied list looked empty or lost filter")
    let partial = try JSONDecoder().decode(InboxList.self, from: Data("{\"business\":101,\"items\":[],\"summary\":{\"open\":5}}".utf8))
    let partialRetry = Task { await inbox.load(business: 101) }; await source.waitPage(4)
    await source.resolvePage(4, .success(partial)); await partialRetry.value
    try expect(inbox.partial && !inbox.showsEmpty, "Partial-zero Inbox looked complete-empty")
    let leaving = Task { await inbox.load(business: 101) }; await source.waitPage(5); inbox.clear()
    await source.resolvePage(5, .success(a)); await leaving.value
    try expect(inbox.business == nil && inbox.items.isEmpty && !inbox.loading && !inbox.showsEmpty, "Cleared scope was repopulated")
    let restart = Task { await inbox.load(business: 101) }; await source.waitPage(6)
    await source.resolvePage(6, .success(a)); await restart.value
    inbox.query = "Alpha"; inbox.unreadOnly = true
    let cancelledThread = Task { await inbox.open(id: 901) }; await source.waitThread(6)
    await source.cancelThread(6); await cancelledThread.value
    try expect(inbox.selectedID == nil && !inbox.threadLoading && inbox.query == "Alpha" && inbox.unreadOnly, "Cancelled thread left a blank or loading destination")
    let cancelledList = Task { await inbox.load(business: 101) }; await source.waitPage(7)
    await source.cancelPage(7); await cancelledList.value
    try expect(!inbox.loading && !inbox.showsEmpty && inbox.failure == nil, "Cancelled list became empty/error or kept loading")
    let recovered = Task { await inbox.load(business: 101) }; await source.waitPage(8)
    await source.resolvePage(8, .success(a)); await recovered.value
    try expect(inbox.visible.map(\.id) == [901] && inbox.unreadOnly, "Cancelled list retry lost scope/filter")
    return count
}
