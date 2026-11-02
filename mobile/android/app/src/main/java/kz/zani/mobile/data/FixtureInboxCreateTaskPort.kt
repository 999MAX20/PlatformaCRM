package kz.zani.mobile.data
import android.content.res.AssetManager
import kz.zani.mobile.core.*
import org.json.JSONObject

// No HTTP command implementation; generic GET uses the separate source reader.
class FixtureInboxCreateTaskPort private constructor(private val catalog:String):SyntheticInboxCreateTaskPort {
    constructor(assets:AssetManager):this(assets.open("fixtures/inbox-create-task.json").bufferedReader().use {it.readText()})
    private val root=JSONObject(catalog)
    override val grants:List<SyntheticInboxCreateTaskGrant> = if(root.optBoolean("fixture_only"))root.getJSONArray("grants").let {rows->(0 until rows.length()).map {rows.getJSONObject(it)}.map {SyntheticInboxCreateTaskGrant(it.getInt("business"),it.getInt("conversation"),it.getInt("actor"),it.getBoolean("create"))}}else emptyList()
    override suspend fun execute(a:InboxCreateTaskAttempt):SyntheticInboxCreateTaskOutcome {
        val auth=a.review.authorization;val c=auth.context;if(!a.review.valid || grants.mapNotNull {it.authorization(c)}.none {it==auth})return SyntheticInboxCreateTaskOutcome.RejectedWithoutWrite
        val rows=root.getJSONArray("scenarios");val row=(0 until rows.length()).map {rows.getJSONObject(it)}.firstOrNull {it.getInt("business")==c.business && it.getInt("conversation")==c.conversation && it.getInt("actor")==auth.actor && (if(it.isNull("original_client"))null else it.getInt("original_client"))==a.review.source.client && (if(it.isNull("original_lead"))null else it.getInt("original_lead"))==a.review.source.lead && it.getString("original_updated_at")==a.review.source.updatedAt} ?: return SyntheticInboxCreateTaskOutcome.RejectedWithoutWrite
        return when(row.getString("outcome")){"response"->SyntheticInboxCreateTaskOutcome.Response(row.getInt("status"),row.getString("response_json"));"rejected"->SyntheticInboxCreateTaskOutcome.RejectedWithoutWrite;else->SyntheticInboxCreateTaskOutcome.Unknown}
    }
    companion object {fun fromJSON(raw:String)=FixtureInboxCreateTaskPort(raw)}
}
