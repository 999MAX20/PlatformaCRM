import Foundation
import CRMCore

func checkAppointmentDate(directory: URL) throws -> Int {
    let data = try Data(contentsOf: directory.appendingPathComponent("appointment-101-501.json"))
    let detail = try JSONDecoder().decode(AppointmentDetail.self, from: data)
    var count = 0
    func expect(_ condition: Bool, _ message: String) throws {
        guard condition else { throw ViewModelCheckFailure(message: message) }
        count += 1
    }
    for language in ["ru", "kk", "en"] {
        let label = AppointmentDate.format(startAt: detail.appointment.start_at, timezone: "Asia/Almaty", language: language)
        try expect(label?.contains("9:00") == true && label?.contains("T04:00") == false, "\(language) detail did not show Business-local09:00: \(label ?? "nil")")
        let nextDay = AppointmentDate.format(startAt: "2026-10-28T23:30:00Z", timezone: "Asia/Almaty", language: language)
        try expect(nextDay?.contains("29") == true && nextDay?.contains("4:30") == true, "\(language) Business timezone did not roll into day29 at04:30")
    }
    let utc = AppointmentDate.format(startAt: detail.appointment.start_at, timezone: "UTC", language: "en")
    let almaty = AppointmentDate.format(startAt: detail.appointment.start_at, timezone: "Asia/Almaty", language: "en")
    try expect(utc?.contains("4:00") == true && almaty?.contains("9:00") == true && utc != almaty, "Selected Business timezone was ignored")
    try expect(AppointmentDate.format(startAt: detail.appointment.start_at, timezone: nil, language: "ru") == nil, "Missing Business timezone guessed a date")
    try expect(AppointmentDate.format(startAt: detail.appointment.start_at, timezone: "Invalid/Zone", language: "kk") == nil, "Invalid Business timezone guessed a date")
    try expect(AppointmentDate.format(startAt: "not-an-instant", timezone: "Asia/Almaty", language: "en") == nil, "Invalid instant was presented as a date")
    return count
}
