import Foundation
import CRMCore

func runAppointmentStatusChecks(directory: URL) throws -> Int {
    var count = 0
    func expect(_ value: Bool,_ message: String) throws { guard value else { throw CheckFailure(message:message) }; count += 1 }
    let data = try Data(contentsOf:directory.deletingLastPathComponent().appendingPathComponent("ui-copy.json"))
    let source = try JSONDecoder().decode(AppointmentDetail.self,from:Data(contentsOf:directory.appendingPathComponent("appointment-101-501.json")))
    let statuses = [("created","appointmentCreated"),("confirmed","appointmentConfirmed"),("cancelled","appointmentCancelled"),("rescheduled","appointmentRescheduled"),("completed","appointmentCompleted"),("no_show","appointmentNoShow")]
    for language in ["ru","kk","en"] {
        let copy = try UICopy(data:data,preferredLanguage:language)
        for (raw,key) in statuses { try expect(AppointmentStatusText.label(raw,text:copy.text) == copy.text(key),"Appointment status label mismatch in \(language): \(raw)") }
        for raw in [nil,"","  \n"] as [String?] { try expect(AppointmentStatusText.label(raw,text:copy.text) == copy.text("notAvailable"),"Unknown/empty status incorrectly implied a lifecycle state") }
        try expect(AppointmentStatusText.label("future_source_status",text:copy.text) == "future_source_status","Unknown source status was guessed")
        _ = AppointmentStatusText.label(source.appointment.status,text:copy.text)
        try expect(source.appointment.status == "confirmed" && source.appointment.id == 501,"Display helper rewrote source state/identity")
    }
    return count
}
