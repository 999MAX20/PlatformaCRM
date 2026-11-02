package kz.zani.mobile.data

import android.content.res.AssetManager
import org.json.JSONObject
import kz.zani.mobile.core.*

// Explicit composite fixture source. Read repositories never create these grants.
class FixtureAppointmentTerminalPort private constructor(private val mobile:FixtureAppointmentLifecyclePort,private val rows:List<Row>):SyntheticAppointmentLifecyclePort {
    private data class Row(val grant:SyntheticAppointmentTerminalGrant,val action:AppointmentLifecycleAction,val outcome:String,val status:Int?,val body:String?)
    override val grants get()=mobile.grants
    override val terminalGrants get()=rows.map {it.grant}.distinct()
    constructor(assets:AssetManager):this(FixtureAppointmentLifecyclePort(assets),runCatching {parse(assets.open("fixtures/appointment-terminal.json").bufferedReader().use {it.readText()})}.getOrDefault(emptyList()))
    override suspend fun execute(attempt:AppointmentLifecycleAttempt):SyntheticAppointmentLifecycleOutcome {
        if(!attempt.review.action.isGenericTerminal)return mobile.execute(attempt)
        val row=rows.filter {it.action==attempt.review.action && it.grant.authorization(attempt.review.source,it.action)==attempt.authorization}.singleOrNull() ?: return SyntheticAppointmentLifecycleOutcome.Unknown
        if(row.outcome=="rejected_without_write")return SyntheticAppointmentLifecycleOutcome.RejectedWithoutWrite
        return if(row.outcome=="response" && row.status!=null && row.body!=null)SyntheticAppointmentLifecycleOutcome.Response(row.status,row.body)else SyntheticAppointmentLifecycleOutcome.Unknown
    }
    companion object {
        fun fromJSON(mobile:String,terminal:String)=FixtureAppointmentTerminalPort(FixtureAppointmentLifecyclePort.fromJSON(mobile),parse(terminal))
        private fun parse(json:String):List<Row> {
            val o=JSONObject(json);require((o.get("fixture_only") as? Boolean)==true);val a=o.getJSONArray("scenarios")
            return (0 until a.length()).map {i->val x=a.getJSONObject(i);val g=x.getJSONObject("grant")
                fun integer(k:String):Int {val v=g.get(k);require(v is Int || v is Long);val n=(v as Number).toLong();require(n in 1..Int.MAX_VALUE.toLong());return n.toInt()}
                fun action(wire:String)=AppointmentLifecycleAction.entries.first {it.wire==wire}.also {require(it.isGenericTerminal)}
                val actions=g.getJSONArray("actions");val grant=SyntheticAppointmentTerminalGrant(integer("business"),integer("appointment"),integer("actor"),g.get("update") as? Boolean ?: throw IllegalArgumentException(),(0 until actions.length()).map {action(actions.getString(it))})
                Row(grant,action(x.getString("action")),x.getString("outcome"),if(x.isNull("status"))null else x.getInt("status"),if(x.isNull("response_json"))null else x.getString("response_json"))
            }
        }
    }
}
