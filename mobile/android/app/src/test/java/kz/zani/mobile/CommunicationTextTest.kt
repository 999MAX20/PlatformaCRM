package kz.zani.mobile

import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import org.junit.Assert.*
import org.junit.Test

class CommunicationTextTest {
    private fun resource(name: String) = javaClass.classLoader!!.getResourceAsStream(name)!!.bufferedReader().use { it.readText() }
    @Test fun existingNotificationStatesAndChannelsUseExactLocaleKeys() {
        val statuses = listOf("pending" to "notificationPending","sent" to "notificationSent","failed" to "notificationFailed","cancelled" to "notificationCancelled")
        val channels = listOf("website" to "channelWebsite","telegram" to "channelTelegram","whatsapp" to "channelWhatsapp","instagram" to "channelInstagram","manual" to "channelManual","email" to "channelEmail","sms" to "channelSms","system" to "channelSystem")
        for (language in listOf("ru","kk","en")) {
            val copy = UiCopy(resource("ui-copy.json"),language)
            statuses.forEach { (raw,key) -> assertEquals(copy.text(key),NotificationStatusText.label(raw,copy::text)) }
            channels.forEach { (raw,key) -> assertEquals(copy.text(key),ReadChannelText.label(raw,copy::text)) }
        }
    }
    @Test fun unknownAndMissingCommunicationValuesNeverAcquireAnInferredState() {
        for (language in listOf("ru","kk","en")) {
            val copy = UiCopy(resource("ui-copy.json"),language)
            for (raw in listOf(null,""," \n")) {
                assertEquals(copy.text("notAvailable"),NotificationStatusText.label(raw,copy::text))
                assertEquals(copy.text("notAvailable"),ReadChannelText.label(raw,copy::text))
            }
            assertEquals("future_status",NotificationStatusText.label("future_status",copy::text)); assertEquals("future_channel",ReadChannelText.label("future_channel",copy::text))
        }
    }
    @Test fun statusPresentationDoesNotMarkReadOrAssertDelivery() {
        val source = JsonContracts.notifications(resource("fixtures/notifications-101.json")).items[0]
        val unread = source.unread; val copy = UiCopy(resource("ui-copy.json"),"ru")
        assertEquals(copy.text("notificationSent"),NotificationStatusText.label(source.status,copy::text))
        assertEquals("sent",source.status); assertEquals(unread,source.unread)
    }
}
