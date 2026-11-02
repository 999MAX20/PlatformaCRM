package kz.zani.mobile.core

// Local profile relation observation only. Search/read selections are not wire versions or grants.
data class AppointmentBookingClientSelection private constructor(val source:AppointmentBookingSource,val selected:ClientSearchProfileSelection,val read:ClientReadSelection,val rawQuery:String,val choice:TaskDraftClientChoice) {
    fun matches(source:AppointmentBookingSource,client:TaskDraftClientChoice)=this.source==source && choice==client
    companion object {fun make(source:AppointmentBookingSource,selected:ClientSearchProfileSelection,read:ClientReadSelection,rawQuery:String,profile:ClientProfile):AppointmentBookingClientSelection? {
        if(!source.valid || selected.selection.context!=ClientSearchContext(source.read.scope.business.id,source.epoch) || selected.selection.generation<=0 || selected.generation<=0 || read.business!=source.read.scope.business.id || read.id!=selected.id || read.revision<=0)return null
        val choice=TaskDraftClientChoice.make(profile,read.business,read.id) ?: return null
        return AppointmentBookingClientSelection(source,selected,read,rawQuery,choice)
    }}
}
