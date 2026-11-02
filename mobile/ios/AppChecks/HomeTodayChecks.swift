import Foundation
import CRMCore

actor ControlledHomeToday: HomeTodayRepository {
    private var homes: [CheckedContinuation<HomeSummary, any Error>] = []
    private var days: [CheckedContinuation<TodaySummary, any Error>] = []
    func home(business: Int) async throws -> HomeSummary { try await withCheckedThrowingContinuation { homes.append($0) } }
    func today(business: Int, day: String) async throws -> TodaySummary { try await withCheckedThrowingContinuation { days.append($0) } }
    func wait(home: Int, today: Int) async { while homes.count < home || days.count < today { await Task.yield() } }
    func resolveHome(_ n: Int, _ result: Result<HomeSummary, ReadFailure>) { homes[n].resume(with: result.mapError { $0 as any Error }) }
    func resolveToday(_ n: Int, _ result: Result<TodaySummary, ReadFailure>) { days[n].resume(with: result.mapError { $0 as any Error }) }
    func counts()->[Int] {[homes.count,days.count]}
    func cancelHome(_ n: Int) { homes[n].resume(throwing: CancellationError()) }
}

@MainActor func checkHomeToday(directory: URL) async throws -> Int {
    let repo = APIReadRepository(transport: FixtureTransport(directory: directory))
    let a = try await repo.home(business:101), b = try await repo.home(business:202)
    let t = try await repo.today(business:101,day:"2026-10-28"), u = try await repo.today(business:202,day:"2026-10-28")
    let source = ControlledHomeToday(); let model = HomeTodayViewModel(repository:source,now:{ Appointment.instant("2026-10-28T23:30:00Z")! })
    var count = 0
    func expect(_ v: Bool, _ message: String) throws { guard v else { throw ViewModelCheckFailure(message:message) }; count += 1 }
    try expect(model.currentDay(timezone:"Asia/Almaty") == "2026-10-29", "Today used device day instead of selected Business")
    let first = Task { await model.start(business:101,day:"2026-10-28") }; await source.wait(home:1,today:1)
    await source.resolveHome(0,.success(a)); await source.resolveToday(0,.failure(.denied)); await first.value
    try expect(model.home != nil && model.today == nil && model.todayFailure == .denied, "One section failure erased successful projection")
    for target in HomeDestination.allCases { model.open(target); try expect(model.destination == target, "Home target lost"); model.back() }
    try expect(model.home != nil && model.day == "2026-10-28", "Home Back erased snapshot/context")
    let retry = Task { await model.reloadToday() }; await source.wait(home:1,today:2)
    await source.resolveToday(1,.success(t)); await retry.value
    try expect(model.todayFailure == nil && model.today != nil && model.home != nil, "Independent retry erased Home")
    let old = Task { await model.reloadHome() }; await source.wait(home:2,today:2)
    let fresh = Task { await model.reloadHome() }; await source.wait(home:3,today:2)
    var j = try JSONSerialization.jsonObject(with: Data(contentsOf:directory.appendingPathComponent("home-101.json"))) as! [String:Any]; j["sections"] = [:]
    let redacted = try JSONDecoder().decode(HomeSummary.self,from:JSONSerialization.data(withJSONObject:j))
    await source.resolveHome(2,.success(redacted)); await fresh.value; await source.resolveHome(1,.success(a)); await old.value
    try expect(model.home?.sections.tasks == nil, "Late summary restored withheld counter")
    let pendingDay = Task { await model.reloadToday() }; await source.wait(home:3,today:3)
    model.open(.tasks)
    let switchScope = Task { await model.start(business:202,day:"2026-10-28") }; await source.wait(home:4,today:4)
    try expect(model.destination == nil && model.home == nil && model.today == nil, "Scope switch kept old route/data")
    await source.resolveHome(3,.success(b)); await source.resolveToday(3,.success(u)); await switchScope.value
    await source.resolveToday(2,.failure(.unavailable)); await pendingDay.value
    try expect(model.today?.business == 202 && model.todayFailure == nil, "Old Business failure replaced current day")
    let cancel = Task { await model.reloadHome() }; await source.wait(home:5,today:4); await source.cancelHome(4); await cancel.value
    try expect(!model.homeLoading && model.home == nil && model.homeFailure == nil, "Cancelled summary stranded loading or fabricated data")
    let leaving = Task { await model.reloadToday() }; await source.wait(home:5,today:5); model.clear()
    await source.resolveToday(4,.success(u)); await leaving.value
    try expect(model.business == nil && model.today == nil, "Cleared Home repopulated by late result")
    let wrongDay = Task { await model.start(business:101,day:"2026-10-29") }; await source.wait(home:6,today:6)
    await source.resolveHome(5,.success(a)); await source.resolveToday(5,.success(t)); await wrongDay.value
    try expect(model.todayFailure == .invalidPayload && model.today == nil && model.home != nil, "Wrong date Today accepted")
    let liveModel = HomeTodayViewModel(repository:repo); let tasks = TaskListViewModel(repository:repo)
    await liveModel.start(business:101,day:"2026-10-28"); liveModel.open(.tasks)
    await tasks.load(business:101); tasks.query = "Alpha"; tasks.status = "open"; await tasks.open(id:1101)
    try expect(tasks.detail?.task.id == 1101, "Existing independent Task detail route unavailable")
    tasks.back(); liveModel.back()
    try expect(tasks.query == "Alpha" && tasks.status == "open" && liveModel.today != nil && liveModel.destination == nil, "Section/detail Back lost either context")
    let agenda = AgendaViewModel(repository:repo, initialDate:Appointment.instant("2026-10-28T04:00:00Z")!)
    liveModel.open(.appointments); await agenda.start(); await agenda.loadDetail(id:501)
    try expect(agenda.session.detail?.appointment.id == 501, "Home section could not reach independently read Appointment")
    agenda.closeDetail(); liveModel.back()
    try expect(agenda.session.selection?.day == "2026-10-28" && agenda.session.items.count == 2 && liveModel.home != nil, "Agenda/Home Back lost day/list/snapshot")
    let clients = ClientDirectoryViewModel(repository:repo), profile = ClientProfileViewModel(repository:repo)
    liveModel.open(.clients); await clients.load(business:101); clients.query = "Alpha"; clients.open(id:701)
    await profile.load(business:101,id:701,onContact:clients.refreshContact)
    try expect(profile.detail?.client.id == 701 && clients.selected?.id == 701, "Home Client route bypassed independent profile")
    profile.clear(); clients.back(); liveModel.back()
    try expect(clients.query == "Alpha" && clients.visible.count == 1 && liveModel.home != nil, "Client/Home Back lost directory context")
    let inbox = InboxViewModel(repository:repo)
    liveModel.open(.inbox); await inbox.load(business:101); inbox.query = "Alpha"; inbox.unreadOnly = true; await inbox.open(id:901)
    try expect(inbox.thread?.conversation.id == 901, "Home Inbox route failed separate thread read")
    inbox.back(); liveModel.back()
    try expect(inbox.query == "Alpha" && inbox.unreadOnly && inbox.visible.count == 1 && liveModel.home != nil, "Inbox/Home Back lost filter/snapshot")
    return count
}
