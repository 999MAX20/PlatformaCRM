package kz.zani.mobile.data

import android.content.res.AssetManager
import kz.zani.mobile.core.*
import org.json.JSONObject

interface InboxLinkLeadRepository {suspend fun source(c:InboxConversationFilesContext):InboxLinkLeadSource}
class APIInboxLinkLeadRepository(private val transport:ReadTransport):InboxLinkLeadRepository {
    override suspend fun source(c:InboxConversationFilesContext):InboxLinkLeadSource {if(!c.valid)throw ReadException(ReadProblem.INVALID_CONTEXT);val r=transport.get(ReadRequest("/api/inbox/conversations/${c.conversation}/"));if(r.status!=200)throw ReadException(when(r.status){403->ReadProblem.DENIED;404->ReadProblem.NOT_FOUND;else->ReadProblem.UNAVAILABLE});return InboxLinkLeadSource.decode(r.body,c) ?: throw ReadException(ReadProblem.INVALID_PAYLOAD)}
}
class FixtureInboxLinkLeadPort private constructor(private val catalog:String):SyntheticInboxLinkLeadPort {
    constructor(assets:AssetManager):this(assets.open("fixtures/inbox-link-lead.json").bufferedReader().use {it.readText()})
    private val root=JSONObject(catalog)
    override val grants:List<SyntheticInboxLinkLeadGrant> = if(root.optBoolean("fixture_only"))root.getJSONArray("grants").let {rows->(0 until rows.length()).map {rows.getJSONObject(it)}.map {SyntheticInboxLinkLeadGrant(it.getInt("business"),it.getInt("conversation"),it.getInt("actor"),it.getBoolean("leads_update"),it.getBoolean("conversations_update"))}}else emptyList()
    override suspend fun execute(a:InboxLinkLeadAttempt):SyntheticInboxLinkLeadOutcome {
        val auth=a.review.authorization;val c=auth.context;if(!a.review.valid || grants.mapNotNull {it.authorization(c)}.none {it==auth})return SyntheticInboxLinkLeadOutcome.RejectedWithoutWrite
        val rows=root.getJSONArray("scenarios");val row=(0 until rows.length()).map {rows.getJSONObject(it)}.firstOrNull {it.getInt("business")==c.business && it.getInt("conversation")==c.conversation && it.getInt("actor")==auth.actor && it.getInt("lead_id")==a.review.candidate.reference.detail.lead.id && (if(it.isNull("original_client"))null else it.getInt("original_client"))==a.review.source.client} ?: return SyntheticInboxLinkLeadOutcome.RejectedWithoutWrite
        return when(row.getString("outcome")){"response"->SyntheticInboxLinkLeadOutcome.Response(row.getInt("status"),row.getString("response_json"));"rejected"->SyntheticInboxLinkLeadOutcome.RejectedWithoutWrite;else->SyntheticInboxLinkLeadOutcome.Unknown}
    }
    companion object {fun fromJSON(raw:String)=FixtureInboxLinkLeadPort(raw)}
}
class FixtureInboxLinkLeadReadTransport private constructor(private val catalog:String):ReadTransport {
    constructor(assets:AssetManager):this(assets.open("fixtures/inbox-link-lead.json").bufferedReader().use {it.readText()})
    override suspend fun get(request:ReadRequest):ReadResponse {val root=JSONObject(catalog);if(!root.getBoolean("fixture_only") || request.query.isNotEmpty())throw ReadException(ReadProblem.INVALID_CONTEXT);val rows=root.getJSONArray("reads");val row=(0 until rows.length()).map {rows.getJSONObject(it)}.firstOrNull {it.getString("path")==request.path} ?: throw ReadException(ReadProblem.INVALID_CONTEXT);return ReadResponse(200,row.getString("response_json"))}
    companion object {fun fromJSON(raw:String)=FixtureInboxLinkLeadReadTransport(raw)}
}
