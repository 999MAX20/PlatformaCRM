import Foundation

// Read labels only. Sent is not delivered/read; no provider action or marker update.
public enum NotificationStatusText {
    public static func label(_ raw: String?, text: (String) -> String) -> String {
        switch raw {
        case "pending": return text("notificationPending")
        case "sent": return text("notificationSent")
        case "failed": return text("notificationFailed")
        case "cancelled": return text("notificationCancelled")
        default: return ReadChannelText.unknown(raw, text: text)
        }
    }
}
public enum ReadChannelText {
    public static func label(_ raw: String?, text: (String) -> String) -> String {
        switch raw {
        case "website": return text("channelWebsite")
        case "telegram": return text("channelTelegram")
        case "whatsapp": return text("channelWhatsapp")
        case "instagram": return text("channelInstagram")
        case "manual": return text("channelManual")
        case "email": return text("channelEmail")
        case "sms": return text("channelSms")
        case "system": return text("channelSystem")
        default: return unknown(raw, text: text)
        }
    }
    fileprivate static func unknown(_ raw: String?, text: (String) -> String) -> String {
        guard let raw, !raw.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return text("notAvailable") }
        return raw
    }
}
