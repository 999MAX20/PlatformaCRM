import Foundation
import CRMCore

func runNotificationReadChecks(directory: URL) async throws -> Int {
    var count = 0
    func expect(_ condition: Bool, _ message: String) throws { guard condition else { throw CheckFailure(message: message) }; count += 1 }
    func item(url: String? = nil, appointment: Int? = 501, omitRead: Bool = false) throws -> CRMNotification {
        let data = try Data(contentsOf: directory.appendingPathComponent("notifications-101.json"))
        let json = try JSONSerialization.jsonObject(with: data) as! [String: Any]
        var row = (json["items"] as! [[String: Any]])[0]
        if let url { row["action_url"] = url }
        row["appointment_id"] = appointment.map { $0 as Any } ?? NSNull()
        if omitRead { row.removeValue(forKey: "read_at") }
        return try JSONDecoder().decode(CRMNotification.self, from: JSONSerialization.data(withJSONObject: row))
    }
    let source = RecordingTransport(FixtureTransport(directory: directory))
    let repository = APIReadRepository(transport: source)
    let page = try await repository.notifications(business: 101)
    try expect(page.valid(for: 101) && page.items.map(\.id) == [2101,2103,2102], "Notification source identity/order changed")
    try expect(page.items[0].unread && !page.items[2].unread, "Explicit source read markers changed")
    let unknown = try item(omitRead: true)
    try expect(!unknown.readMarkerPresent && !unknown.unread, "Missing read marker became unread")
    for url in ["/app/calendar?appointment=501", "/app/calendar/501", "/app/calendar/501/"] {
        try expect(try item(url: url).appointmentTarget == 501, "Known relative calendar route not resolved")
    }
    for url in ["https://evil.invalid/app/calendar/501", "//evil.invalid/app/calendar/501", "/app/leads/501", "/app/tasks?task=501", "/app/calendar/999", "/app/calendar?appointment=501&business=202", "/app/calendar?appointment=501&appointment=999", "/app/calendar/501#x", "/app/calendar/%35%30%31", "/x/../app/calendar/501"] {
        try expect(try item(url: url).appointmentTarget == nil, "Unsupported/foreign route was accepted: \(url)")
    }
    try expect(try item(appointment: nil).appointmentTarget == nil, "Link inferred missing Appointment identity")
    let target = try await repository.appointment(business: 101, id: 501)
    try expect(target.business == 101 && target.appointment.id == 501, "Independent target fixture read changed")
    let requests = await source.requests
    try expect(requests == [ReadRequest(path: "/api/mobile/v1/notifications/", query: ["business":"101","limit":"50"]), ReadRequest(path: "/api/mobile/v1/appointments/501/", query: ["business":"101"])], "Notification flow issued unexpected/write routes")
    do { _ = try await repository.notifications(business: 0); throw CheckFailure(message: "Invalid notification scope requested") }
    catch let error as ReadFailure { try expect(error == .invalidContext, "Wrong notification context error") }
    let afterInvalid = await source.requests; try expect(afterInvalid.count == 2, "Invalid notification scope reached transport")
    let denied = APIReadRepository(transport: FixedTransport(response: ReadResponse(status: 403, data: Data())))
    do { _ = try await denied.appointment(business: 101, id: 501); throw CheckFailure(message: "Parent notification bypassed target permission") }
    catch let error as ReadFailure { try expect(error == .denied, "Wrong independent target denied error") }
    return count
}
