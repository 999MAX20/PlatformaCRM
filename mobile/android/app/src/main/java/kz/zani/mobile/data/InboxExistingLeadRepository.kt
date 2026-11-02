package kz.zani.mobile.data

import android.content.res.AssetManager
import kz.zani.mobile.core.*
import org.json.JSONObject

typealias InboxExistingLeadRepository = InboxLinkLeadRepository
typealias APIInboxExistingLeadRepository = APIInboxLinkLeadRepository
class FixtureInboxExistingLeadPort private constructor(private val catalog:String):SyntheticInboxExistingLeadPort {
    constructor(assets:AssetManager):this(assets.open("fixtures/inbox-existing-lead.json").bufferedReader().use {it.readText()})
    private val root=JSONObject(catalog)
    override val grants:List<SyntheticInboxExistingLeadGrant> = if(root.optBoolean("fixture_only"))root.getJSONArray("grants").let {rows->(0 until rows.length()).map {rows.getJSONObject(it)}.map {SyntheticInboxExistingLeadGrant(it.getInt("business"),it.getInt("conversation"),it.getInt("actor"),it.getBoolean("leads_create"),it.getBoolean("conversations_update"))}}else emptyList()
    override suspend fun execute(a:InboxExistingLeadAttempt):SyntheticInboxExistingLeadOutcome {
        val auth=a.review.authorization;val c=auth.context;if(!a.review.valid || grants.mapNotNull {it.authorization(c)}.none {it==auth})return SyntheticInboxExistingLeadOutcome.RejectedWithoutWrite
        val rows=root.getJSONArray("scenarios");val row=(0 until rows.length()).map {rows.getJSONObject(it)}.firstOrNull {it.getInt("business")==c.business && it.getInt("conversation")==c.conversation && it.getInt("actor")==auth.actor && it.getInt("original_lead")==a.review.source.lead && (if(it.isNull("original_client"))null else it.getInt("original_client"))==a.review.source.client && it.getString("original_updated_at")==a.review.source.updatedAt} ?: return SyntheticInboxExistingLeadOutcome.RejectedWithoutWrite
        return when(row.getString("outcome")){"response"->SyntheticInboxExistingLeadOutcome.Response(row.getInt("status"),row.getString("response_json"));"rejected"->SyntheticInboxExistingLeadOutcome.RejectedWithoutWrite;else->SyntheticInboxExistingLeadOutcome.Unknown}
    }
    companion object {fun fromJSON(raw:String)=FixtureInboxExistingLeadPort(raw)}
}
class FixtureInboxExistingLeadReadTransport private constructor(private val catalog:String):ReadTransport {
    constructor(assets:AssetManager):this(assets.open("fixtures/inbox-existing-lead.json").bufferedReader().use {it.readText()})
    override suspend fun get(request:ReadRequest):ReadResponse {val root=JSONObject(catalog);if(!root.getBoolean("fixture_only") || request.query.isNotEmpty())throw ReadException(ReadProblem.INVALID_CONTEXT);val rows=root.getJSONArray("reads");val row=(0 until rows.length()).map {rows.getJSONObject(it)}.firstOrNull {it.getString("path")==request.path} ?: throw ReadException(ReadProblem.INVALID_CONTEXT);return ReadResponse(200,row.getString("response_json"))}
    companion object {fun fromJSON(raw:String)=FixtureInboxExistingLeadReadTransport(raw)}
}
