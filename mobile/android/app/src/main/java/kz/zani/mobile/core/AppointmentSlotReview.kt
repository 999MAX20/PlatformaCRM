package kz.zani.mobile.core

// Local evidence from one returned READ. No new server DTO, grant or version.
data class AppointmentSlotReadContext private constructor(val business:Business,val service:AppointmentReferenceDetail,val resource:AppointmentReferenceDetail?,val read:AppointmentSlotRead) {
    val valid:Boolean get()=AppointmentSlotIntent.make(business,service,resource,read.intent.day)?.let {read.validFor(it)}==true
    fun review(index:Int)=AppointmentSlotCandidateReview.make(this,index)
    companion object {fun make(business:Business,service:AppointmentReferenceDetail,resource:AppointmentReferenceDetail?,read:AppointmentSlotRead):AppointmentSlotReadContext? {
        val snapshot=read.copy(candidates=read.candidates.toList());val context=AppointmentSlotReadContext(business,service,resource,snapshot)
        return context.takeIf {it.valid}
    }}
}
data class AppointmentSlotCandidateReview private constructor(val context:AppointmentSlotReadContext,val index:Int) {
    val candidate:AppointmentSlotCandidate? get()=context.read.candidates.getOrNull(index)
    fun validFor(expected:AppointmentSlotReadContext)=context==expected && expected.valid && index in expected.read.candidates.indices
    companion object {fun make(context:AppointmentSlotReadContext,index:Int):AppointmentSlotCandidateReview?=if(context.valid && index in context.read.candidates.indices)AppointmentSlotCandidateReview(context,index) else null}
}
