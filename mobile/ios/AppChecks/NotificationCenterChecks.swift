import Foundation
import CRMCore

actor ControlledNotifications: NotificationRepository {
    private var pages: [Int: CheckedContinuation<NotificationPage, any Error>] = [:]
    private var targets: [Int: CheckedContinuation<AppointmentDetail, any Error>] = [:]
    private var pageWaiters: [Int: CheckedContinuation<Void, Never>] = [:]
    private var targetWaiters: [Int: CheckedContinuation<Void, Never>] = [:]
    private var pageCount = 0, targetCount = 0
    private var targetIDs: [[Int]] = []
    func notifications(business: Int) async throws -> NotificationPage {
        let id = pageCount; pageCount += 1
        return try await withCheckedThrowingContinuation { pages[id] = $0; pageWaiters.removeValue(forKey: id)?.resume() }
    }
    func appointment(business: Int, id: Int) async throws -> AppointmentDetail {
        let request = targetCount; targetCount += 1; targetIDs.append([business,id])
        return try await withCheckedThrowingContinuation { targets[request] = $0; targetWaiters.removeValue(forKey: request)?.resume() }
    }
    func waitPage(_ id: Int) async { if pages[id] == nil { await withCheckedContinuation { pageWaiters[id] = $0 } } }
    func waitTarget(_ id: Int) async { if targets[id] == nil { await withCheckedContinuation { targetWaiters[id] = $0 } } }
    func resolvePage(_ id: Int, _ result: Result<NotificationPage, ReadFailure>) {
        let c = pages.removeValue(forKey: id)!
        switch result { case .success(let value): c.resume(returning: value); case .failure(let error): c.resume(throwing: error) }
    }
    func resolveTarget(_ id: Int, _ result: Result<AppointmentDetail, ReadFailure>) {
        let c = targets.removeValue(forKey: id)!
        switch result { case .success(let value): c.resume(returning: value); case .failure(let error): c.resume(throwing: error) }
    }
    func cancelTarget(_ id: Int) { targets.removeValue(forKey: id)!.resume(throwing: CancellationError()) }
    func cancelPage(_ id: Int) { pages.removeValue(forKey: id)!.resume(throwing: CancellationError()) }
    func counts() -> [Int] { [pageCount,targetCount] }
}

@MainActor func checkNotificationCenter(directory: URL) async throws -> Int {
    func fixture<T: Decodable>(_ name: String, as type: T.Type) throws -> T { try JSONDecoder().decode(type, from: Data(contentsOf: directory.appendingPathComponent(name + ".json"))) }
    let a = try fixture("notifications-101", as: NotificationPage.self), b = try fixture("notifications-202", as: NotificationPage.self)
    let appointment = try fixture("appointment-101-501", as: AppointmentDetail.self)
    let source = ControlledNotifications(); let model = NotificationCenterViewModel(repository: source)
    var count = 0
    func expect(_ condition: Bool, _ message: String) throws { guard condition else { throw ViewModelCheckFailure(message: message) }; count += 1 }
    let loading = Task { await model.load(business: 101) }; await source.waitPage(0)
    try expect(model.loading && !model.showsEmpty, "Pending notification list looked empty")
    await source.resolvePage(0, .success(a)); await loading.value
    model.query = " ALPHA "; model.category = "sales"; model.unreadOnly = true
    try expect(model.visible.map(\.id) == [2101], "Local notification filters failed")
    model.open(id: 2101); let cardCounts = await source.counts()
    try expect(model.selected?.unread == true && cardCounts == [1,0], "Opening card marked read or issued a request")
    let firstTarget = Task { await model.openTarget() }; await source.waitTarget(0)
    await source.resolveTarget(0, .success(appointment)); await firstTarget.value
    try expect(model.target?.appointment.id == 501 && model.selected?.unread == true, "Target read changed notification state")
    model.backTarget(); try expect(model.selectedID == 2101 && model.target == nil && !model.targetActive, "Target Back lost notification card")
    model.close(); try expect(model.query == " ALPHA " && model.category == "sales" && model.unreadOnly, "Card Back lost filters")
    model.open(id: 2102); await model.openTarget(); let legacyCounts = await source.counts()
    try expect(!model.targetActive && legacyCounts == [1,1], "Legacy Lead link redirected by numeric ID")
    model.close(); model.open(id: 999); try expect(model.selectedID == nil, "Unknown notification opened")
    model.open(id: 2101)
    let denied = Task { await model.openTarget() }; await source.waitTarget(1)
    await source.resolveTarget(1, .failure(.denied)); await denied.value
    try expect(model.targetFailure == .denied && model.target == nil && model.selected?.unread == true, "Parent access granted target access")
    let old = Task { await model.openTarget() }; await source.waitTarget(2); model.backTarget()
    let fresh = Task { await model.openTarget() }; await source.waitTarget(3)
    await source.resolveTarget(2, .success(appointment)); await old.value
    try expect(model.target == nil && model.targetLoading, "Previous target visit populated retry")
    var json = try JSONSerialization.jsonObject(with: Data(contentsOf: directory.appendingPathComponent("appointment-101-501.json"))) as! [String: Any]
    var header = json["appointment"] as! [String: Any]; header["title"] = NSNull(); json["appointment"] = header
    let withheld = try JSONDecoder().decode(AppointmentDetail.self, from: JSONSerialization.data(withJSONObject: json))
    await source.resolveTarget(3, .success(withheld)); await fresh.value
    try expect(model.target?.appointment.title == nil, "Target withholding was reconstructed")
    let staleTarget = Task { await model.openTarget() }; await source.waitTarget(4)
    let stalePage = Task { await model.load(business: 101) }; await source.waitPage(1)
    let other = Task { await model.load(business: 202) }; await source.waitPage(2)
    try expect(model.items.isEmpty && model.query.isEmpty && model.category == nil && !model.unreadOnly && model.selectedID == nil, "Business switch retained notification state")
    await source.resolvePage(2, .success(b)); await other.value
    await source.resolvePage(1, .success(a)); await stalePage.value
    await source.resolveTarget(4, .success(appointment)); await staleTarget.value
    try expect(model.items.map(\.id) == [2201] && model.target == nil, "Old target/list entered another Business")
    let failedList = Task { await model.load(business: 101) }; await source.waitPage(3); model.category = "sales"; model.query = "Alpha"
    await source.resolvePage(3, .failure(.unavailable)); await failedList.value
    try expect(!model.showsEmpty && model.categories.contains("sales") && model.query == "Alpha", "List error lost filter or looked empty")
    let partial = try JSONDecoder().decode(NotificationPage.self, from: Data("{\"business\":101,\"items\":[],\"summary\":{\"total\":5}}".utf8))
    let partialRetry = Task { await model.load(business: 101) }; await source.waitPage(4)
    await source.resolvePage(4, .success(partial)); await partialRetry.value
    try expect(model.partial && !model.showsEmpty, "Partial notifications looked complete-empty")
    let leaving = Task { await model.load(business: 101) }; await source.waitPage(5); model.clear()
    await source.resolvePage(5, .success(a)); await leaving.value
    try expect(model.business == nil && model.items.isEmpty && model.target == nil, "Cleared notifications were repopulated")
    let restart = Task { await model.load(business: 101) }; await source.waitPage(6)
    await source.resolvePage(6, .success(a)); await restart.value; model.open(id: 2101)
    let cancelled = Task { await model.openTarget() }; await source.waitTarget(5)
    await source.cancelTarget(5); await cancelled.value
    try expect(model.selectedID == 2101 && !model.targetActive && !model.targetLoading, "Cancelled target stranded destination")
    let cancelledList = Task { await model.load(business: 101) }; await source.waitPage(7)
    await source.cancelPage(7); await cancelledList.value
    try expect(!model.loading && !model.showsEmpty && model.failure == nil, "Cancelled notification list stranded state")
    return count
}
