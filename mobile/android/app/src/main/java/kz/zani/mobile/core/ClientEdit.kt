package kz.zani.mobile.core

data class ClientEditValues(val fullName: String,val phone: String,val email: String,val source: String) {
    companion object {val fields=listOf(ClientDraftField.FULL_NAME,ClientDraftField.PHONE,ClientDraftField.EMAIL,ClientDraftField.SOURCE)}
    fun value(field: ClientDraftField)=when(field){ClientDraftField.FULL_NAME->fullName;ClientDraftField.PHONE->phone;ClientDraftField.EMAIL->email;ClientDraftField.SOURCE->source;ClientDraftField.NOTES->""}
    fun update(field: ClientDraftField,value: String)=when(field){ClientDraftField.FULL_NAME->copy(fullName=value);ClientDraftField.PHONE->copy(phone=value);ClientDraftField.EMAIL->copy(email=value);ClientDraftField.SOURCE->copy(source=value);ClientDraftField.NOTES->this}
    val issues get()=ClientDraftValues(fullName=fullName,phone=phone,email=email,source=source).issues.filter {it.field!=ClientDraftField.NOTES}
}
data class ClientEditReadFields(val fullName: String?,val phone: String?,val email: String?,val source: String?,val version: String?) {
    val complete: ClientEditOrigin? get() {
        if(fullName==null || phone==null || email==null || source==null || source !in ClientDraftValues.sources || version.isNullOrEmpty())return null
        return ClientEditOrigin(ClientEditValues(fullName,phone,email,source),version)
    }
}
data class ClientEditOrigin(val values: ClientEditValues,val version: String)
data class ClientEditContext(val business: Int,val client: Int,val epoch: Int) {val valid get()=business>0 && client>0 && epoch>0}
data class ClientEditSelection(val context: ClientEditContext,val generation: Int)
data class ClientEditReview(val selection: ClientEditSelection,val original: ClientEditValues,val values: ClientEditValues) {
    val changed get()=ClientEditValues.fields.filter {original.value(it)!=values.value(it)}
}
data class ClientEditState(val context: ClientEditContext?=null,val selection: ClientEditSelection?=null,val origin: ClientEditOrigin?=null,val values: ClientEditValues?=null,val available: Boolean=false,val needsReset: Boolean=false,val phase: ClientDraftPhase=ClientDraftPhase.CLOSED,val issues: List<ClientDraftIssue> = emptyList(),val review: ClientEditReview?=null)
class ClientEditSession {
    private data class Stored(val original: ClientEditOrigin,val values: ClientEditValues) {val dirty get()=original.values!=values}
    var state=ClientEditState();private set
    private var ownerBusiness: Int?=null;private var ownerEpoch: Int?=null;private var generation=0
    private val stored=mutableMapOf<Int,Stored>();private var fresh: ClientEditOrigin?=null
    val hasStoredChanges get()=state.context?.let {stored[it.client]?.dirty}==true
    private fun stash() {val c=state.context;val o=state.origin;val v=state.values;if(c!=null && o!=null && v!=null)stored[c.client]=Stored(o,v)}
    private fun hide() {++generation;fresh=null;state=ClientEditState(context=state.context)}
    fun begin(next: ClientEditContext?) {
        stash();hide()
        if(next==null || !next.valid) {state=ClientEditState();stored.clear();ownerBusiness=null;ownerEpoch=null;return}
        if(ownerBusiness!=next.business || ownerEpoch!=next.epoch)stored.clear()
        ownerBusiness=next.business;ownerEpoch=next.epoch;state=state.copy(context=next)
    }
    fun receive(next: ClientEditOrigin?,expected: ClientEditContext) {
        if(state.context!=expected)return
        stash();hide();fresh=next
        if(next==null) {state=state.copy(needsReset=hasStoredChanges);return}
        val previous=stored[expected.client]
        if(previous!=null && previous.dirty && previous.original!=next) {state=state.copy(needsReset=true);return}
        state=state.copy(origin=next,values=if(previous?.dirty==true)previous.values else next.values,available=true);stash()
    }
    fun pause() {stash();hide();state=state.copy(context=null)}
    fun open(expected: ClientEditContext): Boolean {
        if(state.context!=expected || !state.available || state.origin==null || state.values==null)return false
        state=state.copy(selection=ClientEditSelection(expected,++generation),phase=ClientDraftPhase.EDITING,issues=emptyList(),review=null);return true
    }
    fun update(field: ClientDraftField,value: String,expected: ClientEditSelection) {
        if(state.selection!=expected || !state.available || state.phase!=ClientDraftPhase.EDITING || field !in ClientEditValues.fields)return
        state=state.copy(values=state.values?.update(field,value),issues=state.issues.filterNot {it.field==field});stash()
    }
    fun prepare(expected: ClientEditSelection): Boolean {
        if(state.selection!=expected || !state.available || state.phase!=ClientDraftPhase.EDITING)return false
        val origin=state.origin ?: return false;val values=state.values ?: return false
        state=state.copy(issues=values.issues);if(state.issues.isNotEmpty())return false
        state=state.copy(review=ClientEditReview(expected,origin.values,values),phase=ClientDraftPhase.REVIEW);return true
    }
    fun back(expected: ClientEditSelection) {
        if(state.selection!=expected)return
        if(state.phase==ClientDraftPhase.REVIEW)state=state.copy(phase=ClientDraftPhase.EDITING,review=null) else close(expected)
    }
    fun close(expected: ClientEditSelection) {
        if(state.selection!=expected)return
        stash();++generation;state=state.copy(selection=null,phase=ClientDraftPhase.CLOSED,review=null)
    }
    fun cancel(expected: ClientEditSelection) {
        if(state.selection!=expected)return
        val origin=state.origin ?: return
        state=state.copy(values=origin.values,issues=emptyList());stash();close(expected)
    }
    fun discardStored(expected: ClientEditContext) {
        if(state.context!=expected)return
        stored.remove(expected.client);++generation
        state=ClientEditState(context=expected,origin=fresh,values=fresh?.values,available=fresh!=null);stash()
    }
}
