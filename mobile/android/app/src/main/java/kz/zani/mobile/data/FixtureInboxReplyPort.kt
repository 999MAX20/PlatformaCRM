package kz.zani.mobile.data

import android.content.res.AssetManager
import kz.zani.mobile.core.*
import org.json.JSONObject

class FixtureInboxReplyPort private constructor(private val catalog:JSONObject):SyntheticInboxReplyPort {
    constructor(assets:AssetManager):this(JSONObject(assets.open("fixtures/inbox-reply-outcome.json").bufferedReader().use {it.readText()}))
    constructor(source:String):this(JSONObject(source))
    private val rows=if(catalog.opt("fixture_only")==true)catalog.getJSONArray("scenarios") else org.json.JSONArray()
    override val grants=runCatching {(0 until rows.length()).map {n->val g=rows.getJSONObject(n).getJSONObject("grant")
        fun integer(key:String):Int {val v=g.get(key);require(v is Int || v is Long);val x=(v as Number).toLong();require(x in 1L..Int.MAX_VALUE.toLong());return x.toInt()}
        val update=g.get("update");require(update is Boolean);val keys=g.getJSONArray("keys");SyntheticInboxReplyGrant(integer("business"),integer("conversation"),integer("actor"),update,(0 until keys.length()).map {keys.get(it) as String})
    }}.getOrDefault(emptyList())
    override suspend fun execute(attempt:InboxReplyAttempt):SyntheticInboxReplyOutcome {
        val i=grants.indexOfFirst {it.authorization(attempt.authorization.context)==attempt.authorization};if(i<0 || attempt.key !in attempt.authorization.keys)return SyntheticInboxReplyOutcome.Unknown
        val row=rows.getJSONObject(i);if(row.opt("outcome")=="rejected_without_write")return SyntheticInboxReplyOutcome.RejectedWithoutWrite
        val raw=row.optJSONObject("response") ?: return SyntheticInboxReplyOutcome.Unknown;if(row.opt("outcome")!="response")return SyntheticInboxReplyOutcome.Unknown
        val reply=JSONObject(raw.toString());val value=attempt.review.text;reply.getJSONObject("message").put("text",value.substring(0,value.offsetByCodePoints(0,minOf(500,value.codePointCount(0,value.length)))))
        return SyntheticInboxReplyOutcome.Response(200,reply.toString())
    }
}
