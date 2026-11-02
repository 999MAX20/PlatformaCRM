package kz.zani.mobile.data

import android.content.res.AssetManager
import kz.zani.mobile.core.*
import org.json.JSONObject

interface InboxPriorityRepository {suspend fun source(c:InboxConversationFilesContext):InboxPrioritySource}
class APIInboxPriorityRepository(private val transport:ReadTransport):InboxPriorityRepository {
    override suspend fun source(c:InboxConversationFilesContext):InboxPrioritySource {if(!c.valid)throw ReadException(ReadProblem.INVALID_CONTEXT);val r=transport.get(ReadRequest("/api/inbox/conversations/${c.conversation}/"));if(r.status!=200)throw ReadException(when(r.status){403->ReadProblem.DENIED;404->ReadProblem.NOT_FOUND;else->ReadProblem.UNAVAILABLE});return InboxPrioritySource.decode(r.body,c) ?: throw ReadException(ReadProblem.INVALID_PAYLOAD)}
}
class FixtureInboxPriorityPort private constructor(private val catalog:String):SyntheticInboxPriorityPort {
    constructor(assets:AssetManager):this(assets.open("fixtures/inbox-priority.json").bufferedReader().use {it.readText()})
    private val root=JSONObject(catalog)
    override val grants:List<SyntheticInboxPriorityGrant> = if(root.optBoolean("fixture_only"))root.getJSONArray("grants").let {rows->(0 until rows.length()).map {rows.getJSONObject(it)}.map {SyntheticInboxPriorityGrant(it.getInt("business"),it.getInt("conversation"),it.getInt("actor"),it.getBoolean("update"))}}else emptyList()
    override suspend fun execute(a:InboxPriorityAttempt):SyntheticInboxPriorityOutcome {
        val auth=a.review.authorization;val c=auth.context;if(!a.review.valid || grants.mapNotNull {it.authorization(c)}.none {it==auth})return SyntheticInboxPriorityOutcome.RejectedWithoutWrite
        val rows=root.getJSONArray("scenarios");val row=(0 until rows.length()).map {rows.getJSONObject(it)}.firstOrNull {it.getInt("business")==c.business && it.getInt("conversation")==c.conversation && it.getInt("actor")==auth.actor && it.getString("priority")==a.review.value.wire} ?: return SyntheticInboxPriorityOutcome.RejectedWithoutWrite
        return when(row.getString("outcome")){"response"->SyntheticInboxPriorityOutcome.Response(row.getInt("status"),row.getString("response_json"));"rejected"->SyntheticInboxPriorityOutcome.RejectedWithoutWrite;else->SyntheticInboxPriorityOutcome.Unknown}
    }
    companion object {fun fromJSON(raw:String)=FixtureInboxPriorityPort(raw)}
}
class FixtureInboxPriorityReadTransport private constructor(private val catalog:String):ReadTransport {
    constructor(assets:AssetManager):this(assets.open("fixtures/inbox-priority.json").bufferedReader().use {it.readText()})
    override suspend fun get(request:ReadRequest):ReadResponse {val root=JSONObject(catalog);if(!root.getBoolean("fixture_only") || request.query.isNotEmpty())throw ReadException(ReadProblem.INVALID_CONTEXT);val rows=root.getJSONArray("reads");val row=(0 until rows.length()).map {rows.getJSONObject(it)}.firstOrNull {it.getString("path")==request.path} ?: throw ReadException(ReadProblem.INVALID_CONTEXT);return ReadResponse(200,row.getString("response_json"))}
    companion object {fun fromJSON(raw:String)=FixtureInboxPriorityReadTransport(raw)}
}
