package kz.zani.mobile.data

import android.content.res.AssetManager
import org.json.JSONObject
import kz.zani.mobile.core.*

class FixtureAppointmentLifecyclePort private constructor(private val rows:List<Row>):SyntheticAppointmentLifecyclePort {
    private data class Expected(val start:String,val reason:String,val resource:Int?)
    private data class Row(val grant:SyntheticAppointmentLifecycleGrant,val action:AppointmentLifecycleAction,val outcome:String,val status:Int?,val body:String?,val input:Expected?)
    override val grants get()=rows.map {it.grant}.distinct()
    constructor(assets:AssetManager):this(runCatching {parse(assets.open("fixtures/appointment-lifecycle.json").bufferedReader().use {it.readText()})}.getOrDefault(emptyList()))
    override suspend fun execute(attempt:AppointmentLifecycleAttempt):SyntheticAppointmentLifecycleOutcome {
        val row=rows.filter {it.action==attempt.review.action && it.grant.authorization(attempt.review.source,it.action)==attempt.authorization}.singleOrNull() ?: return SyntheticAppointmentLifecycleOutcome.Unknown
        if(attempt.review.action==AppointmentLifecycleAction.RESCHEDULE) {val input=attempt.review.reschedule ?: return SyntheticAppointmentLifecycleOutcome.Unknown;val expected=row.input ?: return SyntheticAppointmentLifecycleOutcome.Unknown;if(input.start.raw!=expected.start || input.rawReason!=expected.reason || input.resource.id!=expected.resource)return SyntheticAppointmentLifecycleOutcome.Unknown}
        if(row.outcome=="rejected_without_write")return SyntheticAppointmentLifecycleOutcome.RejectedWithoutWrite
        return if(row.outcome=="response" && row.status!=null && row.body!=null)SyntheticAppointmentLifecycleOutcome.Response(row.status,row.body)else SyntheticAppointmentLifecycleOutcome.Unknown
    }
    companion object {
        fun fromJSON(json:String)=FixtureAppointmentLifecyclePort(parse(json))
        private fun parse(json:String):List<Row> {val o=JSONObject(json);require((o.get("fixture_only") as? Boolean)==true);val rows=o.getJSONArray("scenarios");return (0 until rows.length()).map {i->val x=rows.getJSONObject(i);val g=x.getJSONObject("grant")
            fun optional(k:String)=if(g.isNull(k))null else g.getString(k)
            val expected=x.optJSONObject("input")?.let {e->require(e.has("resource"));val v=e.get("resource");val id=if(v==JSONObject.NULL)null else {require(v is Int || v is Long);val n=(v as Number).toLong();require(n in 1..Int.MAX_VALUE.toLong());n.toInt()};Expected(e.get("start_at") as? String ?: throw IllegalArgumentException(),e.get("reason_raw") as? String ?: throw IllegalArgumentException(),id)}
            Row(SyntheticAppointmentLifecycleGrant(g.getInt("business"),g.getInt("appointment"),g.getInt("actor"),g.get("update") as? Boolean ?: throw IllegalArgumentException(),optional("confirm_key"),optional("cancel_key"),optional("reschedule_key")),AppointmentLifecycleAction.entries.first {it.wire==x.getString("action")},x.getString("outcome"),if(x.isNull("status"))null else x.getInt("status"),if(x.isNull("response_json"))null else x.getString("response_json"),expected)}
        }
    }
}
