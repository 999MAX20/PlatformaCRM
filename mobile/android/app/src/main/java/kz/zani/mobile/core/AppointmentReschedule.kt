package kz.zani.mobile.core

sealed interface AppointmentRescheduleResource {
    data object Clear:AppointmentRescheduleResource
    data class Linked(val detail:AppointmentReferenceDetail):AppointmentRescheduleResource
    val id:Int? get()=if(this is Linked)detail.id else null
}
data class AppointmentRescheduleInput private constructor(val start:TaskSnoozeValue,val rawReason:String,val resource:AppointmentRescheduleResource) {
    val reason get()=SourceTextTrim.pythonStrip(rawReason)
    fun valid(source:AppointmentLifecycleSource)=prepare(source,start.raw,rawReason,resource)==this
    companion object {
        fun prepare(source:AppointmentLifecycleSource,startAt:String,reason:String,resource:AppointmentRescheduleResource):AppointmentRescheduleInput? {
            val start=TaskSnoozeValue.parse(startAt) ?: return null
            if(!source.canReschedule || start.microseconds%1000L!=0L)return null
            if(resource is AppointmentRescheduleResource.Linked) {val id=source.linkedResourceID ?: return null;if(!resource.detail.validFor(source.read.scope.business.id,id))return null}
            return AppointmentRescheduleInput(start,reason,resource)
        }
    }
}
val AppointmentLifecycleSource.canReschedule:Boolean get()=valid && appointment.status !in listOf("cancelled","completed","no_show")
