package kz.zani.mobile.core

// Explicit read-to-draft time choice only, never authority/reservation/resource default.
data class AppointmentBookingCandidateTime private constructor(val source:AppointmentBookingSource,val review:AppointmentSlotCandidateReview,val rawStart:String) {
    fun validFor(source:AppointmentBookingSource)=this.source==source && make(source,review)==this
    companion object {fun make(source:AppointmentBookingSource,review:AppointmentSlotCandidateReview):AppointmentBookingCandidateTime? {
        val c=review.context
        if(!source.valid || !review.validFor(c) || !c.valid || c.business.id!=source.read.scope.business.id || c.business.timezone!=source.read.scope.business.timezone || !c.service.validFor(source.read.scope.business.id,source.serviceID) || c.read.intent.service!=source.serviceID)return null
        if(c.resource!=null && (source.resourceID!=c.resource.id || !c.resource.validFor(source.read.scope.business.id,c.resource.id)))return null
        val raw=review.candidate?.startAt ?: return null;val value=TaskSnoozeValue.parse(raw) ?: return null;if(value.microseconds%1000L!=0L)return null
        return AppointmentBookingCandidateTime(source,review,raw)
    }}
}
