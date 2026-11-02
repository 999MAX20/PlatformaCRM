package kz.zani.mobile.data

import android.content.res.AssetManager
import kz.zani.mobile.core.*
import org.json.JSONObject

class FixtureHandoffPort private constructor(private val catalog:JSONObject):SyntheticHandoffPort {
    constructor(assets:AssetManager):this(JSONObject(assets.open("fixtures/inbox-handoff-outcome.json").bufferedReader().use {it.readText()}))
    constructor(source:String):this(JSONObject(source))
    private val rows=if(catalog.opt("fixture_only")==true)catalog.getJSONArray("scenarios") else org.json.JSONArray()
    override val grants=runCatching {(0 until rows.length()).map {n->val g=rows.getJSONObject(n).getJSONObject("grant")
        fun integer(key:String):Int {val v=g.get(key);require(v is Int || v is Long);val x=(v as Number).toLong();require(x in 1L..Int.MAX_VALUE.toLong());return x.toInt()}
        val update=g.get("update");require(update is Boolean);SyntheticHandoffGrant(integer("business"),integer("conversation"),integer("actor"),update)
    }}.getOrDefault(emptyList())
    override suspend fun execute(attempt:HandoffAttempt):SyntheticHandoffOutcome {
        val i=grants.indexOfFirst {it.authorization(attempt.authorization.context)==attempt.authorization};if(i<0)return SyntheticHandoffOutcome.Unknown
        val row=rows.getJSONObject(i);if(row.opt("outcome")=="rejected_without_write")return SyntheticHandoffOutcome.RejectedWithoutWrite
        val raw=row.optJSONObject("response") ?: return SyntheticHandoffOutcome.Unknown;if(row.opt("outcome")!="response")return SyntheticHandoffOutcome.Unknown
        val reply=JSONObject(raw.toString()).put("handoff_reason",attempt.review.value.reason);return SyntheticHandoffOutcome.Response(200,reply.toString())
    }
}
