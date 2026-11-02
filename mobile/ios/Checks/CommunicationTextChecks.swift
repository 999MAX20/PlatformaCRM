import Foundation
import CRMCore

func runCommunicationTextChecks(directory: URL) throws -> Int {
    var count = 0
    func expect(_ value: Bool,_ message: String) throws { guard value else { throw CheckFailure(message:message) }; count += 1 }
    let data = try Data(contentsOf:directory.deletingLastPathComponent().appendingPathComponent("ui-copy.json"))
    let statuses = [("pending","notificationPending"),("sent","notificationSent"),("failed","notificationFailed"),("cancelled","notificationCancelled")]
    let channels = [("website","channelWebsite"),("telegram","channelTelegram"),("whatsapp","channelWhatsapp"),("instagram","channelInstagram"),("manual","channelManual"),("email","channelEmail"),("sms","channelSms"),("system","channelSystem")]
    let page = try JSONDecoder().decode(NotificationPage.self,from:Data(contentsOf:directory.appendingPathComponent("notifications-101.json")))
    let source = page.items[0], unread = source.unread
    for language in ["ru","kk","en"] {
        let copy = try UICopy(data:data,preferredLanguage:language)
        for (raw,key) in statuses { try expect(NotificationStatusText.label(raw,text:copy.text)==copy.text(key),"Notification transport status label mismatch") }
        for (raw,key) in channels { try expect(ReadChannelText.label(raw,text:copy.text)==copy.text(key),"Channel label mismatch") }
        for raw in [nil,""," \n"] as [String?] {
            try expect(NotificationStatusText.label(raw,text:copy.text)==copy.text("notAvailable"),"Missing status guessed")
            try expect(ReadChannelText.label(raw,text:copy.text)==copy.text("notAvailable"),"Missing channel guessed")
        }
        try expect(NotificationStatusText.label("future_status",text:copy.text)=="future_status" && ReadChannelText.label("future_channel",text:copy.text)=="future_channel","Unknown source communication value translated/guessed")
        _ = NotificationStatusText.label(source.status,text:copy.text)
        try expect(source.status=="sent" && source.unread==unread,"Display converted sent into read/delivery or changed marker")
    }
    return count
}
