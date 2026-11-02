package kz.zani.mobile.data

import android.content.res.AssetManager
import org.json.JSONObject
import kz.zani.mobile.core.*

class FixtureTaskPriorityEditPort private constructor(private val catalog:JSONObject):SyntheticTaskPriorityEditPort {
    constructor(assets:AssetManager):this(JSONObject(assets.open("fixtures/task-priority-partial-outcome.json").bufferedReader().use {it.readText()}))
    constructor(source:String):this(JSONObject(source))
    private val rows=if(catalog.opt("fixture_only")==true)catalog.getJSONArray("scenarios") else org.json.JSONArray()
    private fun integer(g:JSONObject,key:String):Int {val raw=g.get(key);require(raw is Int || raw is Long);val n=(raw as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());return n.toInt()}
    private fun flag(g:JSONObject,key:String):Boolean {val raw=g.get(key);require(raw is Boolean);return raw}
    override val grants=runCatching {(0 until rows.length()).map {n->val g=rows.getJSONObject(n).getJSONObject("grant");SyntheticTaskPriorityEditGrant(integer(g,"business"),integer(g,"task"),integer(g,"actor"),flag(g,"update"))}}.getOrDefault(emptyList())
    override suspend fun execute(attempt:TaskPriorityEditAttempt):SyntheticTaskPriorityEditOutcome {
        val i=grants.indexOfFirst {it.authorization(attempt.authorization.context)==attempt.authorization};if(i<0)return SyntheticTaskPriorityEditOutcome.Unknown
        val row=rows.getJSONObject(i)
        return when(row.opt("outcome")) {"rejected_without_write"->SyntheticTaskPriorityEditOutcome.RejectedWithoutWrite;"response"->row.optJSONObject("response")?.let {SyntheticTaskPriorityEditOutcome.Response(200,JSONObject(it.toString()).put("priority",attempt.review.value.raw).toString())} ?: SyntheticTaskPriorityEditOutcome.Unknown;else->SyntheticTaskPriorityEditOutcome.Unknown}
    }
}
