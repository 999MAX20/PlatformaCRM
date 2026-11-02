package kz.zani.mobile.data

import android.content.res.AssetManager
import kz.zani.mobile.core.*
import org.json.JSONObject

// Explicit synthetic outcomes. Never implements an HTTP/provider command.
class FixtureInboxRetryPort(private val raw:String):SyntheticInboxRetryPort {
    constructor(assets:AssetManager):this(assets.open("fixtures/inbox-retry-message.json").bufferedReader().use {it.readText()})
    override val grants:List<SyntheticInboxRetryGrant> get()=runCatching {
        val c=JSONObject(raw);require(c.opt("fixture_only")==true);val rows=c.getJSONArray("grants")
        (0 until rows.length()).map {i->val r=rows.getJSONObject(i)
            fun number(key:String):Int {val v=directoryReadInteger(r.get(key));require(v!=null && v in 1L..Int.MAX_VALUE.toLong());return v.toInt()}
            val update=r.get("update");require(update is Boolean);SyntheticInboxRetryGrant(number("business"),number("conversation"),number("actor"),update)
        }
    }.getOrDefault(emptyList())
    override suspend fun execute(attempt:InboxRetryAttempt):SyntheticInboxRetryOutcome {
        val s=attempt.review.source;val c=s.context
        if(!attempt.review.valid || grants.mapNotNull {it.authorization(attempt.review.authorization.owner)}.none {it==attempt.review.authorization})return SyntheticInboxRetryOutcome.RejectedWithoutWrite
        val rows=JSONObject(raw).getJSONArray("scenarios");val row=(0 until rows.length()).map {rows.getJSONObject(it)}.firstOrNull {it.getInt("business")==c.business && it.getInt("conversation")==c.conversation && it.getInt("message_id")==c.message} ?: return SyntheticInboxRetryOutcome.RejectedWithoutWrite
        return when(row.getString("outcome")){"response"->SyntheticInboxRetryOutcome.Response(row.getInt("status"),row.getString("response_json"));"rejected"->SyntheticInboxRetryOutcome.RejectedWithoutWrite;else->SyntheticInboxRetryOutcome.Unknown}
    }
}
// Separate GET fixture adapter; it cannot execute a command or grant UPDATE.
class FixtureInboxRetryReadTransport(private val raw:String):ReadTransport {
    constructor(assets:AssetManager):this(assets.open("fixtures/inbox-retry-message.json").bufferedReader().use {it.readText()})
    override suspend fun get(request:ReadRequest):ReadResponse {
        val c=JSONObject(raw);if(c.opt("fixture_only")!=true)throw ReadException(ReadProblem.INVALID_CONTEXT);val rows=c.getJSONArray("reads")
        val row=(0 until rows.length()).map {rows.getJSONObject(it)}.firstOrNull {val q=it.getJSONObject("query");it.getString("path")==request.path && q.keys().asSequence().associateWith {key->q.getString(key)}==request.query} ?: throw ReadException(ReadProblem.INVALID_CONTEXT)
        return ReadResponse(200,row.getString("response_json"))
    }
}
