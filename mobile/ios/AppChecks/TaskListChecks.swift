import Foundation
import CRMCore

actor ControlledTasks: TaskReadRepository {
    private var pages: [Int: CheckedContinuation<TaskPage, any Error>] = [:]
    private var details: [Int: CheckedContinuation<TaskDetails, any Error>] = [:]
    private var pageWaiters: [Int: CheckedContinuation<Void, Never>] = [:]
    private var detailWaiters: [Int: CheckedContinuation<Void, Never>] = [:]
    private var pageCount = 0, detailCount = 0
    func tasks(business: Int) async throws -> TaskPage {
        let id = pageCount; pageCount += 1
        return try await withCheckedThrowingContinuation { pages[id] = $0; pageWaiters.removeValue(forKey: id)?.resume() }
    }
    func taskDetails(business: Int, id: Int) async throws -> TaskDetails {
        let request = detailCount; detailCount += 1
        return try await withCheckedThrowingContinuation { details[request] = $0; detailWaiters.removeValue(forKey: request)?.resume() }
    }
    func waitPage(_ id: Int) async { if pages[id] == nil { await withCheckedContinuation { pageWaiters[id] = $0 } } }
    func waitDetail(_ id: Int) async { if details[id] == nil { await withCheckedContinuation { detailWaiters[id] = $0 } } }
    func resolvePage(_ id: Int, _ result: Result<TaskPage, ReadFailure>) {
        let continuation = pages.removeValue(forKey: id)!
        switch result { case .success(let value): continuation.resume(returning: value); case .failure(let error): continuation.resume(throwing: error) }
    }
    func resolveDetail(_ id: Int, _ result: Result<TaskDetails, ReadFailure>) {
        let continuation = details.removeValue(forKey: id)!
        switch result { case .success(let value): continuation.resume(returning: value); case .failure(let error): continuation.resume(throwing: error) }
    }
    func cancelPage(_ id: Int) { pages.removeValue(forKey: id)!.resume(throwing: CancellationError()) }
    func cancelDetail(_ id: Int) { details.removeValue(forKey: id)!.resume(throwing: CancellationError()) }
    func counts() -> [Int] { [pageCount, detailCount] }
}

@MainActor func checkTaskList(directory: URL) async throws -> Int {
    func fixture<T: Decodable>(_ name: String, as type: T.Type) throws -> T { try JSONDecoder().decode(type, from: Data(contentsOf: directory.appendingPathComponent(name + ".json"))) }
    let a = try fixture("tasks-101", as: TaskPage.self), b = try fixture("tasks-202", as: TaskPage.self)
    let detail = try fixture("task-101-1101", as: TaskDetails.self)
    let source = ControlledTasks()
    let tasks = TaskListViewModel(repository: source)
    var count = 0
    func expect(_ value: Bool, _ message: String) throws { guard value else { throw ViewModelCheckFailure(message: message) }; count += 1 }
    let loading = Task { await tasks.load(business: 101) }; await source.waitPage(0)
    try expect(tasks.loading && !tasks.showsEmpty, "Pending task list looked empty")
    await source.resolvePage(0, .success(a)); await loading.value
    tasks.query = " ALPHA "; tasks.status = "open"
    try expect(tasks.visible.map(\.id) == [1101], "Task search/status filter failed")
    let opening = Task { await tasks.open(id: 1101) }; await source.waitDetail(0)
    await source.resolveDetail(0, .success(detail)); await opening.value; tasks.back()
    try expect(tasks.query == " ALPHA " && tasks.status == "open" && tasks.visible.map(\.id) == [1101], "Task Back lost list/search/status")
    await tasks.open(id: 999); let localCounts = await source.counts()
    try expect(localCounts == [1,1] && tasks.selectedID == nil, "Local filter/unknown ID issued a read")
    let failedList = Task { await tasks.load(business: 101) }; await source.waitPage(1)
    await source.resolvePage(1, .failure(.denied)); await failedList.value
    try expect(tasks.status == "open" && tasks.statuses.contains("open"), "Retained task filter lost its valid picker tag")
    try expect(tasks.failure == .denied && !tasks.showsEmpty && tasks.query == " ALPHA ", "Task error lost scope or looked empty")
    let restore = Task { await tasks.load(business: 101) }; await source.waitPage(2)
    await source.resolvePage(2, .success(a)); await restore.value
    let oldVisit = Task { await tasks.open(id: 1101) }; await source.waitDetail(1); tasks.back()
    let reopened = Task { await tasks.open(id: 1101) }; await source.waitDetail(2)
    await source.resolveDetail(1, .success(detail)); await oldVisit.value
    try expect(tasks.detail == nil && tasks.detailLoading, "Previous task visit populated reopened detail")
    var json = try JSONSerialization.jsonObject(with: Data(contentsOf: directory.appendingPathComponent("task-101-1101.json"))) as! [String: Any]
    var header = json["task"] as! [String: Any]; header["title"] = NSNull(); header["due_at"] = NSNull(); header["status"] = "future_status"; json["task"] = header; json["details"] = ["description": NSNull()]
    let withheld = try JSONDecoder().decode(TaskDetails.self, from: JSONSerialization.data(withJSONObject: json))
    await source.resolveDetail(2, .success(withheld)); await reopened.value; tasks.back()
    try expect(tasks.items[0].title == nil && tasks.items[0].due_at == nil && tasks.items[0].status == "future_status", "Task redaction/unknown status was replaced")
    let staleDetail = Task { await tasks.open(id: 1101) }; await source.waitDetail(3)
    let staleList = Task { await tasks.load(business: 101) }; await source.waitPage(3)
    let other = Task { await tasks.load(business: 202) }; await source.waitPage(4)
    try expect(tasks.items.isEmpty && tasks.query.isEmpty && tasks.status == nil && tasks.selectedID == nil, "Business switch retained task data")
    await source.resolvePage(4, .success(b)); await other.value
    await source.resolvePage(3, .success(a)); await staleList.value
    await source.resolveDetail(3, .failure(.unavailable)); await staleDetail.value
    try expect(tasks.items.map(\.id) == [1201] && tasks.detailFailure == nil, "Late task data entered another Business")
    let backToA = Task { await tasks.load(business: 101) }; await source.waitPage(5)
    await source.resolvePage(5, .success(a)); await backToA.value; tasks.query = "Alpha"; tasks.status = "open"
    let cancelledDetail = Task { await tasks.open(id: 1101) }; await source.waitDetail(4)
    await source.cancelDetail(4); await cancelledDetail.value
    try expect(tasks.selectedID == nil && !tasks.detailLoading && tasks.query == "Alpha" && tasks.status == "open", "Cancelled task detail stranded destination")
    let cancelledList = Task { await tasks.load(business: 101) }; await source.waitPage(6)
    await source.cancelPage(6); await cancelledList.value
    try expect(!tasks.loading && !tasks.showsEmpty && tasks.failure == nil, "Cancelled task list stranded state")
    let partial = try JSONDecoder().decode(TaskPage.self, from: Data("{\"business\":101,\"items\":[],\"summary\":{\"total\":5}}".utf8))
    let partialRetry = Task { await tasks.load(business: 101) }; await source.waitPage(7)
    await source.resolvePage(7, .success(partial)); await partialRetry.value
    try expect(tasks.partial && !tasks.showsEmpty && tasks.statuses.contains("open"), "Partial task list lost filter or looked complete")
    let leaving = Task { await tasks.load(business: 101) }; await source.waitPage(8); tasks.clear()
    await source.resolvePage(8, .success(a)); await leaving.value
    try expect(tasks.business == nil && tasks.items.isEmpty && tasks.status == nil && !tasks.showsEmpty, "Cleared task context was repopulated")
    return count
}
