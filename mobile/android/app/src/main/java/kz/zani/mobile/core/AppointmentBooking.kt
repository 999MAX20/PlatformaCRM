package kz.zani.mobile.core

import org.json.JSONObject

data class AppointmentBookingSource(val read:DetailSelection,val epoch:Int,val clientID:Int,val serviceID:Int,val resourceID:Int?) {val valid get()=epoch>0 && read.revision>0 && read.scope.revision>0 && listOf(read.scope.business.id,read.id,clientID,serviceID).all {it>0} && (resourceID==null || resourceID>0)}
data class AppointmentBookingInput private constructor(val client:TaskDraftClientChoice,val service:AppointmentReferenceDetail,val resource:AppointmentRescheduleResource,val start:TaskSnoozeValue,val directory:AppointmentBookingDirectorySelection?,val clientSelection:AppointmentBookingClientSelection?) {
    fun valid(s:AppointmentBookingSource)=prepare(s,client,service,resource,start.raw,directory,clientSelection)==this
    fun body(business:Int):String?=if(!client.validFor(business) || service.business!=business)null else JSONObject().put("business",business).put("client",client.id).put("service",service.id).put("start_at",start.raw).put("resource",resource.id ?: JSONObject.NULL).toString()
    companion object {fun prepare(s:AppointmentBookingSource,client:TaskDraftClientChoice,service:AppointmentReferenceDetail,resource:AppointmentRescheduleResource,startAt:String,directory:AppointmentBookingDirectorySelection?=null,clientSelection:AppointmentBookingClientSelection?=null):AppointmentBookingInput? {
        val start=TaskSnoozeValue.parse(startAt) ?: return null
        if(!s.valid || !client.validFor(s.read.scope.business.id) || client.id!=(clientSelection?.choice?.id ?: s.clientID) || !service.validFor(s.read.scope.business.id,directory?.service?.id ?: s.serviceID) || start.microseconds%1000L!=0L)return null
        if(clientSelection!=null && !clientSelection.matches(s,client))return null
        if(directory!=null && !directory.matches(s,service,resource))return null
        if(resource is AppointmentRescheduleResource.Linked && ((directory?.resource?.id ?: s.resourceID)!=resource.detail.id || !resource.detail.validFor(s.read.scope.business.id,resource.detail.id)))return null
        return AppointmentBookingInput(client,service,resource,start,directory,clientSelection)
    }}
}
data class SyntheticAppointmentBookingGrant(val business:Int,val fromAppointment:Int,val actor:Int,val create:Boolean) {
    fun authorization(s:AppointmentBookingSource):SyntheticAppointmentBookingAuthorization?=if(!s.valid || business!=s.read.scope.business.id || fromAppointment!=s.read.id || actor<=0 || !create)null else SyntheticAppointmentBookingAuthorization(business,fromAppointment,s.epoch,actor)
}
data class SyntheticAppointmentBookingAuthorization internal constructor(val business:Int,val fromAppointment:Int,val epoch:Int,val actor:Int)
data class AppointmentBookingReview(val source:AppointmentBookingSource,val input:AppointmentBookingInput,val visit:Int)
data class AppointmentBookingAttempt internal constructor(val localID:Int,val authorization:SyntheticAppointmentBookingAuthorization,val review:AppointmentBookingReview,val body:String) {
    val path get()="/api/appointments/";val method get()="POST";val query:Map<String,String> get()=emptyMap()
    override fun toString()="AppointmentBookingAttempt(localID=$localID)"
}
sealed interface SyntheticAppointmentBookingOutcome {data class Response(val status:Int,val body:String):SyntheticAppointmentBookingOutcome;data object RejectedWithoutWrite:SyntheticAppointmentBookingOutcome;data object Unknown:SyntheticAppointmentBookingOutcome}
interface SyntheticAppointmentBookingPort {val grants:List<SyntheticAppointmentBookingGrant>;suspend fun execute(attempt:AppointmentBookingAttempt):SyntheticAppointmentBookingOutcome}
data class AppointmentBookingReceipt(val appointment:AppointmentTerminalReceipt) {
    fun matches(a:AppointmentBookingAttempt):Boolean {val p=appointment;val i=a.review.input;return p.business==a.authorization.business && p.client==i.client.id && p.service==i.service.id && p.resource==i.resource.id && TaskSnoozeValue.parse(p.startAt)?.microseconds==i.start.microseconds}
    companion object {fun decode(json:String)=AppointmentTerminalReceipt.decode(json)?.let {AppointmentBookingReceipt(it)}}
}
enum class AppointmentBookingPhase {PENDING,ACCEPTED_FIXTURE,REJECTED_FIXTURE,UNKNOWN}
data class AppointmentBookingRecord(val attempt:AppointmentBookingAttempt,val phase:AppointmentBookingPhase,val receipt:AppointmentBookingReceipt?=null)
class AppointmentBookingLedger {
    private val rows=mutableListOf<AppointmentBookingRecord>();val records get()=rows.toList();private val active=mutableMapOf<String,Int>();private val consumed=mutableSetOf<String>()
    private fun target(s:AppointmentBookingSource)="${s.read.scope.business.id}/${s.read.id}"
    fun blocked(s:AppointmentBookingSource)=target(s) in active
    fun used(s:AppointmentBookingSource)=target(s) in consumed
    fun visible(a:SyntheticAppointmentBookingAuthorization):AppointmentBookingRecord?=active["${a.business}/${a.fromAppointment}"]?.let {rows[it].takeIf {r->r.attempt.authorization==a}}
    fun begin(review:AppointmentBookingReview,a:SyntheticAppointmentBookingAuthorization):AppointmentBookingAttempt? {
        val s=review.source;if(!s.valid || review.visit<=0 || !review.input.valid(s) || a.business!=s.read.scope.business.id || a.fromAppointment!=s.read.id || a.epoch!=s.epoch || a.actor<=0 || blocked(s) || used(s))return null
        val body=review.input.body(a.business) ?: return null;val attempt=AppointmentBookingAttempt(rows.size+1,a,review,body);active[target(s)]=rows.size;rows+=AppointmentBookingRecord(attempt,AppointmentBookingPhase.PENDING);return attempt
    }
    fun complete(attempt:AppointmentBookingAttempt,outcome:SyntheticAppointmentBookingOutcome) {
        val i=rows.indexOfFirst {it.attempt==attempt};if(i<0 || rows[i].phase!=AppointmentBookingPhase.PENDING)return;var phase=AppointmentBookingPhase.UNKNOWN;var receipt:AppointmentBookingReceipt?=null
        when(outcome) {SyntheticAppointmentBookingOutcome.Unknown->Unit;SyntheticAppointmentBookingOutcome.RejectedWithoutWrite->phase=AppointmentBookingPhase.REJECTED_FIXTURE
            is SyntheticAppointmentBookingOutcome.Response->if(outcome.status==201)AppointmentBookingReceipt.decode(outcome.body)?.takeIf {it.matches(attempt)}?.let {phase=AppointmentBookingPhase.ACCEPTED_FIXTURE;receipt=it}}
        rows[i]=AppointmentBookingRecord(attempt,phase,receipt)
    }
    fun acknowledge(record:AppointmentBookingRecord):Boolean {val s=record.attempt.review.source;val i=active[target(s)] ?: return false;if(rows[i]!=record || record.phase !in listOf(AppointmentBookingPhase.ACCEPTED_FIXTURE,AppointmentBookingPhase.REJECTED_FIXTURE))return false;if(record.phase==AppointmentBookingPhase.ACCEPTED_FIXTURE)consumed+=target(s);active.remove(target(s));return true}
}
