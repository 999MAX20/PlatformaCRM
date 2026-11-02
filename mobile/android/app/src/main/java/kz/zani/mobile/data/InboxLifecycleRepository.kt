package kz.zani.mobile.data

import android.content.res.AssetManager
import kz.zani.mobile.core.*
import org.json.JSONObject

interface InboxLifecycleRepository {suspend fun source(c:InboxConversationFilesContext):InboxLifecycleSource}
class APIInboxLifecycleRepository(private val transport:ReadTransport):InboxLifecycleRepository {
    override suspend fun source(c:InboxConversationFilesContext):InboxLifecycleSource {if(!c.valid)throw ReadException(ReadProblem.INVALID_CONTEXT);val r=transport.get(ReadRequest("/api/inbox/conversations/${c.conversation}/"));if(r.status!=200)throw ReadException(when(r.status){403->ReadProblem.DENIED;404->ReadProblem.NOT_FOUND;else->ReadProblem.UNAVAILABLE});return InboxLifecycleSource.decode(r.body,c) ?: throw ReadException(ReadProblem.INVALID_PAYLOAD)}
}
class FixtureInboxLifecyclePort private constructor(private val catalog:String):SyntheticInboxLifecyclePort {
    constructor(assets:AssetManager):this(assets.open("fixtures/inbox-lifecycle.json").bufferedReader().use {it.readText()})
    private val root=JSONObject(catalog)
    override val grants:List<SyntheticInboxLifecycleGrant> = if(root.optBoolean("fixture_only"))root.getJSONArray("grants").let {rows->(0 until rows.length()).map {rows.getJSONObject(it)}.map {SyntheticInboxLifecycleGrant(it.getInt("business"),it.getInt("conversation"),it.getInt("actor"),it.getBoolean("update"))}}else emptyList()
    override suspend fun execute(a:InboxLifecycleAttempt):SyntheticInboxLifecycleOutcome {
        val auth=a.review.authorization;val c=auth.context;if(!a.review.valid || grants.mapNotNull {it.authorization(c)}.none {it==auth})return SyntheticInboxLifecycleOutcome.RejectedWithoutWrite
        val rows=root.getJSONArray("scenarios");val row=(0 until rows.length()).map {rows.getJSONObject(it)}.firstOrNull {it.getInt("business")==c.business && it.getInt("conversation")==c.conversation && it.getInt("actor")==auth.actor && it.getString("action")==a.review.action.wire} ?: return SyntheticInboxLifecycleOutcome.RejectedWithoutWrite
        return when(row.getString("outcome")){"response"->SyntheticInboxLifecycleOutcome.Response(row.getInt("status"),row.getString("response_json"));"rejected"->SyntheticInboxLifecycleOutcome.RejectedWithoutWrite;else->SyntheticInboxLifecycleOutcome.Unknown}
    }
    companion object {fun fromJSON(raw:String)=FixtureInboxLifecyclePort(raw)}
}
class FixtureInboxLifecycleReadTransport private constructor(private val catalog:String):ReadTransport {
    constructor(assets:AssetManager):this(assets.open("fixtures/inbox-lifecycle.json").bufferedReader().use {it.readText()})
    override suspend fun get(request:ReadRequest):ReadResponse {val root=JSONObject(catalog);if(!root.getBoolean("fixture_only") || request.query.isNotEmpty())throw ReadException(ReadProblem.INVALID_CONTEXT);val rows=root.getJSONArray("reads");val row=(0 until rows.length()).map {rows.getJSONObject(it)}.firstOrNull {it.getString("path")==request.path} ?: throw ReadException(ReadProblem.INVALID_CONTEXT);return ReadResponse(200,row.getString("response_json"))}
    companion object {fun fromJSON(raw:String)=FixtureInboxLifecycleReadTransport(raw)}
}
