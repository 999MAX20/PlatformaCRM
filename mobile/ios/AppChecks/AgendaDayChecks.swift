import Foundation
import CRMCore

actor ControlledAgendaDay: AgendaRepository {
    let fixtures: APIReadRepository
    private var pages: [CheckedContinuation<AppointmentList,any Error>] = []
    private var details: [CheckedContinuation<AppointmentDetail,any Error>] = []
    init(directory: URL) { fixtures = APIReadRepository(transport:FixtureTransport(directory:directory)) }
    func bootstrap() async throws -> Bootstrap { try await fixtures.bootstrap() }
    func appointments(business: Int,day: String) async throws -> AppointmentList { try await withCheckedThrowingContinuation { pages.append($0) } }
    func appointment(business: Int,id: Int) async throws -> AppointmentDetail { try await withCheckedThrowingContinuation { details.append($0) } }
    func wait(pages: Int,details: Int) async { while self.pages.count < pages || self.details.count < details { await Task.yield() } }
    func page(_ n: Int,_ result: Result<AppointmentList,ReadFailure>) { pages[n].resume(with:result.mapError { $0 as any Error }) }
    func detail(_ n: Int,_ result: Result<AppointmentDetail,ReadFailure>) { details[n].resume(with:result.mapError { $0 as any Error }) }
    func cancelPage(_ n: Int) { pages[n].resume(throwing:CancellationError()) }
}

@MainActor func checkAgendaDay(directory: URL) async throws -> Int {
    var count = 0
    func expect(_ value: Bool,_ message: String) throws { guard value else { throw ViewModelCheckFailure(message:message) }; count += 1 }
    let repo = APIReadRepository(transport:FixtureTransport(directory:directory)); let edge = try await repo.appointments(business:101,day:"2026-10-29")
    let model = AgendaViewModel(repository:repo,initialDate:Appointment.instant("2026-10-29T04:00:00Z")!)
    await model.start(); model.mode = .calendar
    let ids = model.session.items.map(\.id)
    for id in ids {
        await model.loadDetail(id:id)
        try expect(model.session.detail?.appointment.id == id && model.detailFailure == nil, "Day agenda target used cached row or lost ID")
        model.closeDetail()
        try expect(model.mode == .calendar && model.session.selection?.day == "2026-10-29" && model.session.items.map(\.id) == ids, "Back lost mode/day/source context")
    }
    let dst = try JSONDecoder().decode(AppointmentList.self,from:Data(contentsOf:directory.appendingPathComponent("appointments-agenda-dst-101.json")))
    let d = AgendaDayDisplay(items:dst.items,day:dst.date,responseDay:dst.date,timezone:"America/New_York")
    for language in ["ru","kk","en"] {
        let a = d.scheduled[0].appointment, b = d.scheduled[1].appointment
        let first = AgendaEndpoint.format(a.start_at,timezone:"America/New_York",language:language)
        let end = AgendaEndpoint.format(a.end_at,timezone:"America/New_York",language:language)
        try expect(first?.contains("UTC-04:00") == true && end?.contains("UTC-05:00") == true, "DST endpoint label lost actual offsets")
        try expect(first != AgendaEndpoint.format(b.start_at,timezone:"America/New_York",language:language), "Repeated wall-clock labels are ambiguous")
    }
    try expect(AgendaEndpoint.format(nil,timezone:"UTC",language:"ru") == nil && AgendaEndpoint.format("bad",timezone:"Asia/Almaty",language:"kk") == nil, "Unknown endpoint got invented time")
    try expect(AgendaEndpoint.format("2026-03-08T06:30:00Z",timezone:"America/New_York",language:"en")?.contains("UTC-05:00") == true && AgendaEndpoint.format("2026-03-08T07:30:00Z",timezone:"America/New_York",language:"en")?.contains("UTC-04:00") == true, "Spring-forward endpoint offsets changed")
    let controlled = ControlledAgendaDay(directory:directory)
    let current = AgendaViewModel(repository:controlled,initialDate:model.date)
    let start = Task { await current.start() }; await controlled.wait(pages:1,details:0); await controlled.page(0,.success(edge)); await start.value; current.mode = .calendar
    let old = Task { await current.load(business:101) }; await controlled.wait(pages:2,details:0)
    let fresh = Task { await current.load(business:101) }; await controlled.wait(pages:3,details:0); await controlled.page(2,.success(edge)); await fresh.value; await controlled.page(1,.failure(.unavailable)); await old.value
    try expect(current.failure == nil && current.mode == .calendar && current.session.items.count == 6, "Old list retry replaced current agenda")
    let detail = try await repo.appointment(business:101,id:5602)
    let closing = Task { await current.loadDetail(id:5602) }; await controlled.wait(pages:3,details:1); current.closeDetail()
    let reopen = Task { await current.loadDetail(id:5602) }; await controlled.wait(pages:3,details:2); await controlled.detail(1,.success(detail)); await reopen.value; await controlled.detail(0,.failure(.unavailable)); await closing.value
    try expect(current.session.detail?.appointment.id == 5602 && current.detailFailure == nil, "Back/reopen accepted late detail failure")
    let foreign = Task { await current.loadDetail(id:5602) }; await controlled.wait(pages:3,details:3)
    let switchBusiness = Task { await current.load(business:202) }; await controlled.wait(pages:4,details:3)
    let other = try await repo.appointments(business:202,day:"2026-10-29"); await controlled.page(3,.success(other)); await switchBusiness.value; await controlled.detail(2,.success(detail)); await foreign.value
    try expect(current.session.selection?.business.id == 202 && current.mode == .calendar && current.session.detail == nil, "Business switch restored old record or lost mode")
    var j = try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointments-agenda-edge-101.json"))) as! [String:Any]
    j["business"] = 202; j["date"] = "2026-10-28"; j["items"] = []; j["summary"] = ["total":0]
    let mismatch = try JSONDecoder().decode(AppointmentList.self,from:JSONSerialization.data(withJSONObject:j))
    let mismatchTask = Task { await current.load(business:202) }; await controlled.wait(pages:5,details:3); await controlled.page(4,.success(mismatch)); await mismatchTask.value
    try expect(current.session.sourceDayMismatch && !current.showsEmptyResult && current.failure == nil, "Wrong source date became a confirmed empty selected day")
    let cancel = Task { await current.load(business:202) }; await controlled.wait(pages:6,details:3); await controlled.cancelPage(5); await cancel.value
    try expect(!current.loading && !current.showsEmptyResult && current.mode == .calendar, "Cancelled agenda stranded loading or claimed empty")
    let recover = Task { await current.load(business:202) }; await controlled.wait(pages:7,details:3); await controlled.page(6,.success(other)); await recover.value
    try expect(current.showsEmptyResult && current.mode == .calendar, "Matching empty retry failed or changed calendar mode")
    return count
}
