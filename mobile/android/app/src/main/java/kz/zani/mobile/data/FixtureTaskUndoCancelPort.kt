package kz.zani.mobile.data

import android.content.res.AssetManager
import org.json.JSONObject
import kz.zani.mobile.core.*

class FixtureTaskUndoCancelPort private constructor(private val catalog:JSONObject):SyntheticTaskUndoCancelPort {
    constructor(assets:AssetManager):this(JSONObject(assets.open("fixtures/task-undo-cancel-outcome.json").bufferedReader().use {it.readText()}))
    constructor(source:String):this(JSONObject(source))
    private val rows=if(catalog.opt("fixture_only")==true)catalog.getJSONArray("scenarios") else org.json.JSONArray()
    private fun integer(g:JSONObject,key:String):Int {val raw=g.get(key);require(raw is Int || raw is Long);val n=(raw as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());return n.toInt()}
    private fun flag(g:JSONObject,key:String):Boolean {val raw=g.get(key);require(raw is Boolean);return raw}
    override val grants=runCatching {(0 until rows.length()).map {n->val g=rows.getJSONObject(n).getJSONObject("grant");SyntheticTaskUndoCancelGrant(integer(g,"business"),integer(g,"task"),integer(g,"actor"),flag(g,"update"))}}.getOrDefault(emptyList())
    override suspend fun execute(attempt:TaskUndoCancelAttempt):SyntheticTaskUndoCancelOutcome {
        val i=grants.indexOfFirst {it.authorization(attempt.authorization.context)==attempt.authorization};if(i<0)return SyntheticTaskUndoCancelOutcome.Unknown
        val row=rows.getJSONObject(i)
        return when(row.opt("outcome")) {"rejected_without_write"->SyntheticTaskUndoCancelOutcome.RejectedWithoutWrite;"response"->row.optJSONObject("response")?.let {SyntheticTaskUndoCancelOutcome.Response(200,it.toString())} ?: SyntheticTaskUndoCancelOutcome.Unknown;else->SyntheticTaskUndoCancelOutcome.Unknown}
    }
}
