import Foundation
import CRMCore

func runAgendaDayChecks(directory: URL) async throws -> Int {
    var count = 0
    func expect(_ v: Bool, _ message: String) throws { guard v else { throw CheckFailure(message:message) }; count += 1 }
    let source = RecordingTransport(FixtureTransport(directory:directory)); let repo = APIReadRepository(transport:source)
    let bootstrap = try await repo.bootstrap(); let edge = try await repo.appointments(business:101,day:"2026-10-29")
    var session = AgendaSession(); try session.install(bootstrap); let scope = try session.begin(businessID:101,day:"2026-10-29")
    _ = try session.receive(edge,for:scope)
    let d = AgendaDayDisplay(items:session.items,day:scope.day,responseDay:session.responseDay,timezone:scope.business.timezone)
    try expect(session.items.map(\.id) == [5602,5601,5603,5604,5605,5606] && session.isPartial, "Source order/count/partial state changed")
    try expect(d.scheduled.map(\.id) == [5601,5602], "Daily presentation did not order actual instants")
    try expect(d.uncertain.map(\.issue) == [.unknown,.unknown,.invalidRange,.otherDay], "Uncertain rows dropped or assigned invented time")
    try expect(d.scheduled.count + d.uncertain.count == edge.items.count, "Agenda omitted a same-scope record")
    try expect(edge.items[2].start_at == nil && edge.items[3].start_at == "not-an-instant", "Raw unknown times silently repaired")
    let night = d.scheduled[1].appointment
    try expect(Day.string(night.start!,timezone:"Asia/Almaty") == "2026-10-29" && Day.string(night.end!,timezone:"Asia/Almaty") == "2026-10-30", "Overnight endpoint clipped to chosen day")
    let dst = try JSONDecoder().decode(AppointmentList.self,from:Data(contentsOf:directory.appendingPathComponent("appointments-agenda-dst-101.json")))
    let repeatDay = AgendaDayDisplay(items:dst.items,day:dst.date,responseDay:dst.date,timezone:"America/New_York")
    try expect(repeatDay.scheduled.map(\.id) == [5611,5612] && repeatDay.uncertain.isEmpty, "Repeated DST wall hour confused instant ordering")
    let repeated = repeatDay.scheduled[0].appointment
    try expect(repeated.end! > repeated.start!, "DST wall-clock reversal became negative actual interval")
    var springJSON = try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-101-5601.json"))) as! [String:Any]
    var row = springJSON["appointment"] as! [String:Any]; row["start_at"] = "2026-03-08T06:30:00Z"; row["end_at"] = "2026-03-08T07:30:00Z"; springJSON["appointment"] = row
    let spring = try JSONDecoder().decode(AppointmentDetail.self,from:JSONSerialization.data(withJSONObject:springJSON))
    try expect(AgendaDayDisplay(items:[spring.appointment],day:"2026-03-08",responseDay:"2026-03-08",timezone:"America/New_York").scheduled.count == 1, "Spring-forward gap invented unavailable/free time")
    try expect(AgendaDayDisplay(items:[spring.appointment],day:"2026-03-08",responseDay:"2026-03-08",timezone:"Invalid/Zone").uncertain.first?.issue == .unknown, "Invalid timezone silently fell back")
    var badSource = try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointments-agenda-edge-101.json"))) as! [String:Any]; badSource["date"] = "2026-10-28"
    let mismatch = try JSONDecoder().decode(AppointmentList.self,from:JSONSerialization.data(withJSONObject:badSource))
    _ = try session.receive(mismatch,for:scope)
    let outside = AgendaDayDisplay(items:session.items,day:scope.day,responseDay:session.responseDay,timezone:scope.business.timezone)
    try expect(session.sourceDayMismatch && session.responseDay == "2026-10-28" && session.selection == scope, "Source date mismatch silently changed selected context")
    try expect(outside.scheduled.isEmpty && outside.uncertain.count == 6 && outside.uncertain.allSatisfy { $0.issue == .sourceDay }, "Mismatched response placed on the selected day")
    _ = try session.receive(edge,for:scope)
    for item in edge.items {
        let request = try session.beginDetail(id:item.id); let detail = try await repo.appointment(business:101,id:item.id)
        try expect(try session.receive(detail,for:request), "Independent same-ID unknown-time read failed")
        session.clearDetail()
        try expect(session.selection == scope && session.items.map(\.id) == edge.items.map(\.id), "Detail Back lost day or raw list identity/order")
    }
    let unknown = try await repo.appointment(business:101,id:5603)
    try expect(!AttentionDetail.appointment(unknown).valid(for:101,target:AttentionTarget(kind:.appointment,id:5603)), "Unknown interval weakened unrelated target guard")
    var absent = springJSON; var a = absent["appointment"] as! [String:Any]; a.removeValue(forKey:"start_at"); a["end_at"] = NSNull(); absent["appointment"] = a
    let missing = try JSONDecoder().decode(AppointmentDetail.self,from:JSONSerialization.data(withJSONObject:absent))
    try expect(missing.appointment.start_at == nil && missing.appointment.end_at == nil, "Missing/null time was fabricated")
    let requests = await source.requests
    try expect(requests[1] == ReadRequest(path:"/api/mobile/v1/appointments/",query:["business":"101","date":"2026-10-29","limit":"50"]), "Agenda introduced a different endpoint/DTO")
    return count
}
