import Foundation
import CRMCore

actor ControlledAttention: AttentionRepository {
    private var pages: [CheckedContinuation<AttentionPage, any Error>] = []
    private var details: [CheckedContinuation<AttentionDetail, any Error>] = []
    private(set) var targets: [(Int, AttentionTarget)] = []
    func actions(business: Int) async throws -> AttentionPage { try await withCheckedThrowingContinuation { pages.append($0) } }
    private func target(_ business: Int, _ kind: AttentionKind, _ id: Int) async throws -> AttentionDetail {
        targets.append((business,AttentionTarget(kind:kind,id:id)))
        return try await withCheckedThrowingContinuation { details.append($0) }
    }
    func taskDetails(business: Int, id: Int) async throws -> TaskDetails { guard case .task(let d) = try await target(business,.task,id) else { throw ReadFailure.invalidPayload }; return d }
    func thread(business: Int, id: Int) async throws -> InboxThread { guard case .conversation(let d) = try await target(business,.conversation,id) else { throw ReadFailure.invalidPayload }; return d }
    func appointment(business: Int, id: Int) async throws -> AppointmentDetail { guard case .appointment(let d) = try await target(business,.appointment,id) else { throw ReadFailure.invalidPayload }; return d }
    func wait(pages: Int, details: Int) async { while self.pages.count < pages || self.details.count < details { await Task.yield() } }
    func page(_ n: Int, _ result: Result<AttentionPage,ReadFailure>) { pages[n].resume(with:result.mapError { $0 as any Error }) }
    func detail(_ n: Int, _ result: Result<AttentionDetail,ReadFailure>) { details[n].resume(with:result.mapError { $0 as any Error }) }
    func counts()->[Int] {[pages.count,details.count]}
    func cancelPage(_ n: Int) { pages[n].resume(throwing:CancellationError()) }
    func cancelDetail(_ n: Int) { details[n].resume(throwing:CancellationError()) }
}

@MainActor func checkAttentionQueue(directory: URL) async throws -> Int {
    let repo = APIReadRepository(transport:FixtureTransport(directory:directory))
    let a = try await repo.actions(business:101), b = try await repo.actions(business:202)
    let task = try await repo.taskDetails(business:101,id:1111)
    var j = try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-101-1111.json"))) as! [String:Any]
    var row = j["task"] as! [String:Any]; row["title"] = NSNull(); j["task"] = row
    let withheld = try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:j))
    let source = ControlledAttention(); let model = AttentionQueueViewModel(repository:source)
    var count = 0
    func expect(_ value: Bool, _ message: String) throws { guard value else { throw ViewModelCheckFailure(message:message) }; count += 1 }
    let denied = Task { await model.load(business:101) }; await source.wait(pages:1,details:0); await source.page(0,.failure(.denied)); await denied.value
    try expect(model.failure == .denied && !model.showsEmpty && model.items.isEmpty, "Denied queue became empty success")
    let loaded = Task { await model.load(business:101) }; await source.wait(pages:2,details:0); await source.page(1,.success(a)); await loaded.value
    await model.open(a.items[0].id); await model.open(a.items[3].id)
    let targetCount = await source.targets.count
    try expect(targetCount == 0 && model.selectedID == nil, "Approval/Lead gained native target request")
    model.query = "attention"
    let d0 = Task { await model.open(a.items[1].id) }; await source.wait(pages:2,details:1); await source.detail(0,.failure(.denied)); await d0.value
    try expect(model.detail == nil && model.detailFailure == .denied, "Readable queue granted Task access or cached detail")
    let wrong = Task { await model.open(a.items[1].id) }; await source.wait(pages:2,details:2)
    let foreign = try await repo.taskDetails(business:202,id:1211); await source.detail(1,.success(.task(foreign))); await wrong.value
    try expect(model.detailFailure == .invalidPayload && model.detail == nil, "Foreign read target accepted")
    let valid = Task { await model.open(a.items[1].id) }; await source.wait(pages:2,details:3); await source.detail(2,.success(.task(task))); await valid.value
    try expect(model.detail != nil && model.detailFailure == nil, "Current target retry failed")
    let old = Task { await model.open(a.items[1].id) }; await source.wait(pages:2,details:4)
    let fresh = Task { await model.open(a.items[1].id) }; await source.wait(pages:2,details:5)
    await source.detail(4,.success(.task(withheld))); await fresh.value; await source.detail(3,.success(.task(task))); await old.value
    try expect(model.detail?.title == nil && model.items[1].entity.title == nil, "Late target restored withheld queue/detail title")
    let closing = Task { await model.open(a.items[1].id) }; await source.wait(pages:2,details:6); model.back()
    let reopen = Task { await model.open(a.items[1].id) }; await source.wait(pages:2,details:7)
    await source.detail(6,.success(.task(task))); await reopen.value; await source.detail(5,.failure(.unavailable)); await closing.value
    try expect(model.detailFailure == nil && model.detail != nil, "Back/same-ID reopen accepted old error")
    let leaving = Task { await model.open(a.items[1].id) }; await source.wait(pages:2,details:8); model.back(); await source.detail(7,.success(.task(task))); await leaving.value
    try expect(model.selectedID == nil && model.detail == nil && model.query == "attention", "Back repopulated or lost search")
    let pending = Task { await model.open(a.items[1].id) }; await source.wait(pages:2,details:9)
    let other = Task { await model.load(business:202) }; await source.wait(pages:3,details:9); await source.page(2,.success(b)); await other.value; await source.detail(8,.success(.task(task))); await pending.value
    try expect(model.business == 202 && model.query.isEmpty && model.detail == nil && model.selectedID == nil, "Business switch kept old target/context")
    let cancelled = Task { await model.open(b.items[0].id) }; await source.wait(pages:3,details:10); await source.cancelDetail(9); await cancelled.value
    try expect(model.selectedID == nil && !model.detailLoading && model.loaded, "Cancelled target stranded a destination")
    let cancelledPage = Task { await model.load(business:202) }; await source.wait(pages:4,details:10); await source.cancelPage(3); await cancelledPage.value
    try expect(!model.loading && !model.showsEmpty && !model.loaded, "Cancelled page claimed empty or stranded loading")
    let stalePage = Task { await model.load(business:202) }; await source.wait(pages:5,details:10)
    let newPage = Task { await model.load(business:202) }; await source.wait(pages:6,details:10); await source.page(5,.success(b)); await newPage.value; await source.page(4,.failure(.unavailable)); await stalePage.value
    try expect(model.failure == nil && model.items.count == 1, "Late list retry error replaced new queue")
    let liveModel = AttentionQueueViewModel(repository:repo); await liveModel.load(business:101); liveModel.query = "attention"
    let identities = liveModel.items.map(\.id)
    for item in liveModel.visible {
        await liveModel.open(item.id)
        try expect(liveModel.detail != nil && liveModel.detailFailure == nil, "Source target did not independently load")
        liveModel.back()
        try expect(liveModel.query == "attention" && liveModel.items.map(\.id) == identities && liveModel.selectedID == nil, "Target Back changed order/filter/window")
    }
    await liveModel.load(business:nil)
    try expect(liveModel.items.isEmpty && !liveModel.showsEmpty && liveModel.business == nil, "Clearing queue fabricated a loaded empty result")
    return count
}
