package kz.zani.mobile.core

import org.json.JSONObject

enum class AppointmentLifecycleAction(val wire:String,val expectedStatus:String?) {CONFIRM("confirm","confirmed"),CANCEL("cancel","cancelled"),RESCHEDULE("reschedule",null),COMPLETE("complete","completed"),NO_SHOW("no-show","no_show");val isGenericTerminal get()=this==COMPLETE || this==NO_SHOW}
data class AppointmentLifecycleSource(val read:DetailSelection,val epoch:Int,val appointment:Appointment,val linkedResourceID:Int?=null) {val valid get()=epoch>0 && read.revision>0 && read.scope.revision>0 && read.scope.business.id>0 && appointment.id>0 && appointment.id==read.id && (linkedResourceID==null || linkedResourceID>0)}
data class SyntheticAppointmentLifecycleGrant(val business:Int,val appointment:Int,val actor:Int,val update:Boolean,val confirmKey:String?,val cancelKey:String?,val rescheduleKey:String?=null) {
    fun authorization(source:AppointmentLifecycleSource,action:AppointmentLifecycleAction):SyntheticAppointmentLifecycleAuthorization? {
        val key=when(action) {AppointmentLifecycleAction.CONFIRM->confirmKey;AppointmentLifecycleAction.CANCEL->cancelKey;AppointmentLifecycleAction.RESCHEDULE->rescheduleKey;AppointmentLifecycleAction.COMPLETE,AppointmentLifecycleAction.NO_SHOW->null}
        if(!source.valid || business!=source.read.scope.business.id || appointment!=source.read.id || actor<=0 || !update || key==null || SourceTextTrim.pythonStrip(key).isEmpty())return null
        return SyntheticAppointmentLifecycleAuthorization(business,appointment,source.epoch,actor,action,key)
    }
}
data class SyntheticAppointmentLifecycleAuthorization internal constructor(val business:Int,val appointment:Int,val epoch:Int,val actor:Int,val action:AppointmentLifecycleAction,val key:String?)
data class AppointmentLifecycleReview(val source:AppointmentLifecycleSource,val action:AppointmentLifecycleAction,val visit:Int,val reschedule:AppointmentRescheduleInput?=null)
data class AppointmentLifecycleAttempt internal constructor(val localID:Int,val authorization:SyntheticAppointmentLifecycleAuthorization,val review:AppointmentLifecycleReview,val body:String) {
    val path get()="${if(authorization.action.isGenericTerminal)"/api/appointments/" else "/api/mobile/v1/appointments/"}${authorization.appointment}/${authorization.action.wire}/"
    val query:Map<String,String> get()=if(authorization.action.isGenericTerminal)mapOf("business" to authorization.business.toString())else emptyMap()
    val method get()="POST"
    override fun toString()="AppointmentLifecycleAttempt(localID=$localID)"
}
sealed interface SyntheticAppointmentLifecycleOutcome {data class Response(val status:Int,val body:String):SyntheticAppointmentLifecycleOutcome;data object RejectedWithoutWrite:SyntheticAppointmentLifecycleOutcome;data object Unknown:SyntheticAppointmentLifecycleOutcome}
interface SyntheticAppointmentLifecyclePort {val grants:List<SyntheticAppointmentLifecycleGrant>;val terminalGrants:List<SyntheticAppointmentTerminalGrant> get()=emptyList();suspend fun execute(attempt:AppointmentLifecycleAttempt):SyntheticAppointmentLifecycleOutcome}
data class AppointmentLifecycleItem(val id:Int,val title:String,val status:String,val clientID:Int?,val leadID:Int?,val serviceID:Int?,val startAt:String,val endAt:String,val href:String)
data class AppointmentLifecycleReceipt(val ok:Boolean,val appointment:AppointmentLifecycleItem,val replayed:Boolean) {
    fun matches(a:AppointmentLifecycleAttempt):Boolean {
        if(a.review.action.isGenericTerminal || !ok || appointment.id!=a.authorization.appointment || appointment.href!="/app/calendar?appointment=${appointment.id}" || listOf(appointment.clientID,appointment.leadID,appointment.serviceID).any {it!=null && it<=0} || runCatching {java.time.Instant.parse(appointment.startAt);java.time.Instant.parse(appointment.endAt)}.isFailure)return false
        if(a.review.action==AppointmentLifecycleAction.RESCHEDULE) {val input=a.review.reschedule ?: return false;return input.valid(a.review.source) && appointment.status==a.review.source.appointment.status && TaskSnoozeValue.parse(appointment.startAt)?.microseconds==input.start.microseconds}
        return appointment.status==a.authorization.action.expectedStatus
    }
    companion object {
        fun decode(json:String):AppointmentLifecycleReceipt {
            fun JSONObject.text(k:String)=get(k) as? String ?: throw IllegalArgumentException()
            fun JSONObject.integer(k:String):Int {val v=get(k);require(v is Number);return v.toString().toBigDecimal().intValueExact()}
            fun JSONObject.nullInteger(k:String):Int? {require(has(k));return if(isNull(k))null else integer(k)}
            val o=JSONObject(json);val x=o.getJSONObject("appointment")
            return AppointmentLifecycleReceipt(o.get("ok") as? Boolean ?: throw IllegalArgumentException(),AppointmentLifecycleItem(x.integer("id"),x.text("title"),x.text("status"),x.nullInteger("client_id"),x.nullInteger("lead_id"),x.nullInteger("service_id"),x.text("start_at"),x.text("end_at"),x.text("href")),o.get("replayed") as? Boolean ?: throw IllegalArgumentException())
        }
    }
}
enum class AppointmentLifecyclePhase {PENDING,ACCEPTED_FIXTURE,REJECTED_FIXTURE,UNKNOWN}
data class AppointmentLifecycleRecord(val attempt:AppointmentLifecycleAttempt,val phase:AppointmentLifecyclePhase,val receipt:AppointmentLifecycleReceipt?=null,val terminalReceipt:AppointmentTerminalReceipt?=null)
class AppointmentLifecycleLedger {
    private val rows=mutableListOf<AppointmentLifecycleRecord>();val records get()=rows.toList()
    private val active=mutableMapOf<String,Int>();private val consumed=mutableSetOf<String>()
    private fun target(s:AppointmentLifecycleSource)="${s.read.scope.business.id}/${s.read.id}"
    private fun actionKey(s:AppointmentLifecycleSource,a:AppointmentLifecycleAction)="${target(s)}/${a.wire}"
    fun blocked(s:AppointmentLifecycleSource)=target(s) in active
    fun used(s:AppointmentLifecycleSource,a:AppointmentLifecycleAction)=actionKey(s,a) in consumed
    fun visible(a:SyntheticAppointmentLifecycleAuthorization):AppointmentLifecycleRecord?=active["${a.business}/${a.appointment}"]?.let {rows[it].takeIf {r->r.attempt.authorization==a}}
    fun begin(review:AppointmentLifecycleReview,a:SyntheticAppointmentLifecycleAuthorization):AppointmentLifecycleAttempt? {
        val s=review.source
        if(!s.valid || review.visit<=0 || a.business!=s.read.scope.business.id || a.appointment!=s.read.id || a.epoch!=s.epoch || a.action!=review.action || blocked(s) || used(s,review.action))return null
        if(a.actor<=0 || (if(review.action.isGenericTerminal)a.key!=null else a.key==null || SourceTextTrim.pythonStrip(a.key).isEmpty()))return null
        val fields=if(review.action.isGenericTerminal)JSONObject()else JSONObject().put("business",a.business)
        if(review.action==AppointmentLifecycleAction.RESCHEDULE) {val input=review.reschedule?.takeIf {it.valid(s)} ?: return null;fields.put("start_at",input.start.raw);fields.put("reason",input.reason);fields.put("resource",input.resource.id ?: JSONObject.NULL)}else if(review.reschedule!=null)return null
        val attempt=AppointmentLifecycleAttempt(rows.size+1,a,review,fields.toString());active[target(s)]=rows.size;rows+=AppointmentLifecycleRecord(attempt,AppointmentLifecyclePhase.PENDING);return attempt
    }
    fun complete(attempt:AppointmentLifecycleAttempt,outcome:SyntheticAppointmentLifecycleOutcome) {
        val i=rows.indexOfFirst {it.attempt==attempt};if(i<0 || rows[i].phase!=AppointmentLifecyclePhase.PENDING)return
        var phase=AppointmentLifecyclePhase.UNKNOWN;var receipt:AppointmentLifecycleReceipt?=null;var terminal:AppointmentTerminalReceipt?=null
        when(outcome) {SyntheticAppointmentLifecycleOutcome.Unknown->Unit;SyntheticAppointmentLifecycleOutcome.RejectedWithoutWrite->phase=AppointmentLifecyclePhase.REJECTED_FIXTURE
            is SyntheticAppointmentLifecycleOutcome.Response->if(outcome.status==200) {
                if(attempt.review.action.isGenericTerminal)AppointmentTerminalReceipt.decode(outcome.body)?.takeIf {it.matches(attempt)}?.let {phase=AppointmentLifecyclePhase.ACCEPTED_FIXTURE;terminal=it}
                else runCatching {AppointmentLifecycleReceipt.decode(outcome.body)}.getOrNull()?.takeIf {it.matches(attempt)}?.let {phase=AppointmentLifecyclePhase.ACCEPTED_FIXTURE;receipt=it}
            }}
        rows[i]=AppointmentLifecycleRecord(attempt,phase,receipt,terminal)
    }
    fun acknowledge(record:AppointmentLifecycleRecord):Boolean {
        val s=record.attempt.review.source;val i=active[target(s)] ?: return false
        if(rows[i]!=record || record.phase !in listOf(AppointmentLifecyclePhase.ACCEPTED_FIXTURE,AppointmentLifecyclePhase.REJECTED_FIXTURE))return false
        if(record.phase==AppointmentLifecyclePhase.ACCEPTED_FIXTURE)consumed+=actionKey(s,record.attempt.review.action);active.remove(target(s));return true
    }
}
