package kz.zani.mobile.core

// Retained local field observations only, separate from CREATE/actor/grants/wire fields.
data class AppointmentBookingDirectorySelection private constructor(val source:AppointmentBookingSource,val service:ServiceDirectoryItem?,val resource:ResourceDirectoryItem?) {
    fun matches(source:AppointmentBookingSource,service:AppointmentReferenceDetail,resource:AppointmentRescheduleResource):Boolean {
        if(this.source!=source)return false
        if(this.service!=null && this.service.reference!=service)return false
        if(this.resource!=null && resource!=AppointmentRescheduleResource.Linked(this.resource.reference))return false
        return true
    }
    companion object {fun make(source:AppointmentBookingSource,service:ServiceDirectoryItem?,resource:ResourceDirectoryItem?):AppointmentBookingDirectorySelection? {
        if(!source.valid || service==null && resource==null)return null
        if(service!=null && (service.business!=source.read.scope.business.id || service.id<=0))return null
        if(resource!=null && (resource.business!=source.read.scope.business.id || resource.id<=0))return null
        return AppointmentBookingDirectorySelection(source,service,resource)
    }}
}
