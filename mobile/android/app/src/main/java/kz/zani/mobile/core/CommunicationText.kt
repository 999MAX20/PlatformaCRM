package kz.zani.mobile.core

// Read labels only: never update read markers or imply delivery/provider support.
object NotificationStatusText {
    fun label(raw: String?,text: (String) -> String): String = when (raw) {
        "pending" -> text("notificationPending")
        "sent" -> text("notificationSent")
        "failed" -> text("notificationFailed")
        "cancelled" -> text("notificationCancelled")
        else -> unknownCommunicationValue(raw,text)
    }
}
object ReadChannelText {
    fun label(raw: String?,text: (String) -> String): String = when (raw) {
        "website" -> text("channelWebsite")
        "telegram" -> text("channelTelegram")
        "whatsapp" -> text("channelWhatsapp")
        "instagram" -> text("channelInstagram")
        "manual" -> text("channelManual")
        "email" -> text("channelEmail")
        "sms" -> text("channelSms")
        "system" -> text("channelSystem")
        else -> unknownCommunicationValue(raw,text)
    }
}
private fun unknownCommunicationValue(raw: String?,text: (String) -> String) = raw?.takeIf { it.isNotBlank() } ?: text("notAvailable")
