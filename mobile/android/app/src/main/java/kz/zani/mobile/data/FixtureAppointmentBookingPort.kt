package kz.zani.mobile.data

import android.content.res.AssetManager
import org.json.JSONObject
import kz.zani.mobile.core.*

class FixtureAppointmentBookingPort private constructor(private val rows:List<Row>):SyntheticAppointmentBookingPort {
    private data class Input(val client:Int,val service:Int,val resource:Int?,val start:String)
    private data class Row(val grant:SyntheticAppointmentBookingGrant,val input:Input,val outcome:String,val status:Int?,val body:String?)
    override val grants get()=rows.map {it.grant}
    constructor(assets:AssetManager):this(kotlin.runCatching {FixtureAppointmentBookingPort.parse(assets.open("fixtures/appointment-booking.json").bufferedReader().use {it.readText()})}.getOrDefault(emptyList()))
    override suspend fun execute(attempt:AppointmentBookingAttempt):SyntheticAppointmentBookingOutcome {
        val row=rows.filter {it.grant.authorization(attempt.review.source)==attempt.authorization}.singleOrNull() ?: return SyntheticAppointmentBookingOutcome.Unknown;val input=attempt.review.input
        if(row.input.client!=input.client.id || row.input.service!=input.service.id || row.input.resource!=input.resource.id || row.input.start!=input.start.raw)return SyntheticAppointmentBookingOutcome.Unknown
        if(row.outcome=="rejected_without_write")return SyntheticAppointmentBookingOutcome.RejectedWithoutWrite
        return if(row.outcome=="response" && row.status!=null && row.body!=null)SyntheticAppointmentBookingOutcome.Response(row.status,row.body)else SyntheticAppointmentBookingOutcome.Unknown
    }
    companion object {
        fun fromJSON(json:String)=FixtureAppointmentBookingPort(parse(json))
        private fun parse(json:String):List<Row> {val o=JSONObject(json);require((o.get("fixture_only") as? Boolean)==true);val a=o.getJSONArray("scenarios")
            fun integer(o:JSONObject,k:String):Int {val v=o.get(k);require(v is Int || v is Long);val n=(v as Number).toLong();require(n in 1..Int.MAX_VALUE.toLong());return n.toInt()}
            return (0 until a.length()).map {n->val row=a.getJSONObject(n);val g=row.getJSONObject("grant");val i=row.getJSONObject("input");require(i.has("resource"));val input=Input(integer(i,"client"),integer(i,"service"),if(i.isNull("resource"))null else integer(i,"resource"),i.get("start_at") as? String ?: throw IllegalArgumentException())
                Row(SyntheticAppointmentBookingGrant(integer(g,"business"),integer(g,"from_appointment"),integer(g,"actor"),g.get("create") as? Boolean ?: throw IllegalArgumentException()),input,row.getString("outcome"),if(row.isNull("status"))null else row.getInt("status"),if(row.isNull("response_json"))null else row.getString("response_json"))}
        }
    }
}
