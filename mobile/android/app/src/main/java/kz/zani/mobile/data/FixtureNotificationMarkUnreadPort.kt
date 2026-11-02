package kz.zani.mobile.data

import android.content.res.AssetManager
import org.json.JSONObject
import kz.zani.mobile.core.*

// Explicit DEBUG dependency; no transport, POST or actual notification mutation.
class FixtureNotificationMarkUnreadPort private constructor(catalog:JSONObject):SyntheticNotificationMarkUnreadPort {
    constructor(assets:AssetManager):this(JSONObject(assets.open("fixtures/notification-mark-unread.json").bufferedReader().use {it.readText()}))
    init {require(catalog.get("fixture_only") == true)}
    private val rows=catalog.getJSONArray("scenarios")
    override val grants=(0 until rows.length()).map {val g=rows.getJSONObject(it).getJSONObject("grant");SyntheticNotificationMarkUnreadGrant(g.get("business") as? Int ?: error("Invalid fixture Business"),g.get("notification") as? Int ?: error("Invalid fixture target"),g.get("actor") as? Int ?: error("Invalid fixture actor"),g.get("update") as? Boolean ?: error("Invalid fixture grant"))}
    override suspend fun execute(attempt:NotificationMarkUnreadAttempt):SyntheticNotificationMarkUnreadOutcome {
        val index=grants.indexOfFirst {it.authorization(attempt.authorization.context)==attempt.authorization}
        if(index<0)return SyntheticNotificationMarkUnreadOutcome.Unknown
        val row=rows.getJSONObject(index)
        return when(row.getString("outcome")) {
            "rejected_without_write"->SyntheticNotificationMarkUnreadOutcome.RejectedWithoutWrite
            "response"->SyntheticNotificationMarkUnreadOutcome.Response(200,JsonContracts.notificationMarkUnreadReply(row.getJSONObject("reply").toString()))
            else->SyntheticNotificationMarkUnreadOutcome.Unknown
        }
    }
}
