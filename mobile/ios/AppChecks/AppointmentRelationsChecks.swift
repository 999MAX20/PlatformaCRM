import Foundation
import CRMCore

actor ControlledAppointmentRelations: AgendaRepository, AppointmentRelatedRepository {
    let repo: APIReadRepository
    private var profiles: [CheckedContinuation<ClientProfile,any Error>] = []
    private var tasks: [CheckedContinuation<TaskDetails,any Error>] = []
    init(directory: URL) { repo = APIReadRepository(transport:FixtureTransport(directory:directory)) }
    func bootstrap() async throws -> Bootstrap { try await repo.bootstrap() }
    func appointments(business: Int,day: String) async throws -> AppointmentList { try await repo.appointments(business:business,day:day) }
    func appointment(business: Int,id: Int) async throws -> AppointmentDetail { try await repo.appointment(business:business,id:id) }
    func clientProfile(business: Int,id: Int) async throws -> ClientProfile { try await withCheckedThrowingContinuation { profiles.append($0) } }
    func taskDetails(business: Int,id: Int) async throws -> TaskDetails { try await withCheckedThrowingContinuation { tasks.append($0) } }
    func wait(profiles: Int,tasks: Int) async { while self.profiles.count < profiles || self.tasks.count < tasks { await Task.yield() } }
    func profile(_ n: Int,_ result: Result<ClientProfile,ReadFailure>) { profiles[n].resume(with:result.mapError { $0 as any Error }) }
    func task(_ n: Int,_ result: Result<TaskDetails,ReadFailure>) { tasks[n].resume(with:result.mapError { $0 as any Error }) }
    func counts()->[Int] {[profiles.count,tasks.count]}
    func cancelTask(_ n: Int) { tasks[n].resume(throwing:CancellationError()) }
}

@MainActor func checkAppointmentRelations(directory: URL) async throws -> Int {
    var count = 0
    func expect(_ v: Bool,_ message: String) throws { guard v else { throw ViewModelCheckFailure(message:message) }; count += 1 }
    let repo = APIReadRepository(transport:FixtureTransport(directory:directory)); let links = AppointmentRelationsViewModel(repository:repo)
    let a = AgendaViewModel(repository:repo,initialDate:Appointment.instant("2026-10-28T04:00:00Z")!,relations:links)
    let directoryModel = ClientDirectoryViewModel(repository:repo), tasksModel = TaskListViewModel(repository:repo)
    await directoryModel.load(business:101); directoryModel.query = "Alpha"; await tasksModel.load(business:101); tasksModel.query = "Alpha"; tasksModel.status = "open"
    await a.start(); a.mode = .calendar; await a.loadDetail(id:501); let scope = a.session.selection; let notes = a.session.detail?.details.notes
    await links.openClient()
    try expect(links.profile.detail?.client.id == 7001 && links.profile.detail?.client.email == "appointment-7001@example.invalid", "Parent used cached directory contacts instead of Client GET")
    links.back()
    try expect(a.session.detail?.appointment.id == 501 && a.session.detail?.details.notes == notes, "Child Back lost parent record")
    for id in 1301...1305 { await links.openTask(id); try expect(links.task?.details.appointment_id == 501 && links.task?.task.id == id, "Provided Task independent binding failed"); links.back() }
    a.closeDetail()
    try expect(links.request == nil && links.profile.detail == nil && links.task == nil && a.session.selection == scope && a.mode == .calendar, "Parent Back left dependent state or changed day/mode")
    try expect(directoryModel.query == "Alpha" && tasksModel.query == "Alpha" && tasksModel.status == "open", "Relation flow altered another screen's search/filter")
    let controlled = ControlledAppointmentRelations(directory:directory); let l = AppointmentRelationsViewModel(repository:controlled)
    let m = AgendaViewModel(repository:controlled,initialDate:a.date,relations:l); await m.start(); await m.loadDetail(id:501)
    let profile = try await repo.clientProfile(business:101,id:7001), task = try await repo.taskDetails(business:101,id:1301)
    let deny = Task { await l.openClient() }; await controlled.wait(profiles:1,tasks:0); await controlled.profile(0,.failure(.denied)); await deny.value
    try expect(l.profile.detail == nil && l.profile.failure == .denied && m.session.detail?.appointment.id == 501, "Client denial fell back to parent or removed parent")
    let badClient = Task { await l.openClient() }; await controlled.wait(profiles:2,tasks:0)
    let foreignProfile = try await repo.clientProfile(business:202,id:7003); await controlled.profile(1,.success(foreignProfile)); await badClient.value
    try expect(l.profile.failure == .invalidPayload && l.profile.detail == nil, "Foreign Client profile accepted")
    let oldRequest = l.request!
    let oldClient = Task { await l.openClient(expected:oldRequest) }; await controlled.wait(profiles:3,tasks:0)
    await m.loadDetail(id:501); await controlled.profile(2,.success(profile)); await oldClient.value
    try expect(l.selected == nil && l.profile.detail == nil && l.request != oldRequest, "Parent retry accepted old Client response")
    await l.openClient(expected:oldRequest)
    try expect(l.selected == nil, "Stale UI scope started a new Client route")
    let deniedTask = Task { await l.openTask(1301) }; await controlled.wait(profiles:3,tasks:1); await controlled.task(0,.failure(.denied)); await deniedTask.value
    try expect(l.task == nil && l.failure == .denied, "Provided Task implied read permission")
    var j = try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-101-1301.json"))) as! [String:Any]
    var fields = j["details"] as! [String:Any]; fields["appointment_id"] = 502; j["details"] = fields
    let rebound = try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:j))
    let wrongTask = Task { await l.openTask(1301) }; await controlled.wait(profiles:3,tasks:2); await controlled.task(1,.success(rebound)); await wrongTask.value
    try expect(l.task == nil && l.failure == .invalidPayload, "Task changed Appointment binding but was shown")
    let old = Task { await l.openTask(1301) }; await controlled.wait(profiles:3,tasks:3)
    let newer = Task { await l.openTask(1301) }; await controlled.wait(profiles:3,tasks:4)
    var row = j["task"] as! [String:Any]; row["title"] = NSNull(); j["task"] = row; fields["appointment_id"] = 501; j["details"] = fields
    let withheld = try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:j))
    await controlled.task(3,.success(withheld)); await newer.value; await controlled.task(2,.success(task)); await old.value
    try expect(l.task?.task.title == nil && l.tasks?.first?.title == nil, "Older Task restored withheld parent-window title")
    let closing = Task { await l.openTask(1301) }; await controlled.wait(profiles:3,tasks:5); l.back()
    let reopen = Task { await l.openTask(1301) }; await controlled.wait(profiles:3,tasks:6); await controlled.task(5,.success(task)); await reopen.value; await controlled.task(4,.failure(.unavailable)); await closing.value
    try expect(l.failure == nil && l.task?.task.id == 1301, "Back/reopen accepted stale Task error")
    let cancelled = Task { await l.openTask(1301) }; await controlled.wait(profiles:3,tasks:7); await controlled.cancelTask(6); await cancelled.value
    try expect(l.selected == nil && m.session.detail?.appointment.id == 501, "Cancelled child stranded route or erased Appointment")
    let pending = Task { await l.openClient() }; await controlled.wait(profiles:4,tasks:7); await m.load(business:202); await controlled.profile(3,.success(profile)); await pending.value
    try expect(l.profile.detail == nil && l.request == nil && m.session.selection?.business.id == 202, "Business switch restored foreign contacts")
    await m.loadDetail(id:601)
    let otherClient = Task { await l.openClient() }; await controlled.wait(profiles:5,tasks:7); await controlled.profile(4,.success(foreignProfile)); await otherClient.value
    try expect(l.profile.detail?.business == 202 && l.profile.detail?.client.id == 7003, "Other Business Client read lost its own scope")
    m.closeDetail()
    try expect(l.profile.detail == nil && l.parent == nil && l.selected == nil, "Closing parent retained dependent contacts")
    return count
}
