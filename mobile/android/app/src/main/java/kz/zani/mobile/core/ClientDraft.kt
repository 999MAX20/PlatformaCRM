package kz.zani.mobile.core

// Local input/review only, never a server entity/CREATE grant or persisted queue.
data class ClientDraftContext(val business: Int,val epoch: Int) { val valid get() = business > 0 && epoch > 0 }
data class ClientDraftSelection(val context: ClientDraftContext,val generation: Int)
enum class ClientDraftField { FULL_NAME, PHONE, EMAIL, SOURCE, NOTES }
enum class ClientDraftProblem { NAME, NAME_LENGTH, PHONE_LENGTH, EMAIL, SOURCE, EMAIL_LENGTH, CHARACTERS }
data class ClientDraftIssue(val field: ClientDraftField,val problem: ClientDraftProblem)
data class ClientDraftValues(val fullName: String = "",val phone: String = "",val email: String = "",val source: String = "manual",val notes: String = "") {
    companion object {
        val sources = listOf("manual","website","telegram","whatsapp","instagram","parser","other")
        // Existing ClientForm's pinned zod3.25.76 email pattern, no dependency added.
        private val emailPattern = Regex("""^(?!\.)(?!.*\.\.)([A-Z0-9_'+\-\.]*)[A-Z0-9_+-]@([A-Z0-9][A-Z0-9\-]*\.)+[A-Z]{2,}$""",RegexOption.IGNORE_CASE)
    }
    private fun webEmailAccepted(value:String)=value.isEmpty() || (value.all {it.code<128} && emailPattern.matches(value))
    val preview get()=ClientDraftPreview(SourceTextTrim.pythonStrip(fullName),SourceTextTrim.pythonStrip(phone),SourceTextTrim.pythonStrip(email),source,SourceTextTrim.pythonStrip(notes))
    val webIssues: List<ClientDraftIssue> get()=buildList {
        if(fullName.length<2)add(ClientDraftIssue(ClientDraftField.FULL_NAME,ClientDraftProblem.NAME))
        if(!webEmailAccepted(email))add(ClientDraftIssue(ClientDraftField.EMAIL,ClientDraftProblem.EMAIL))
    }
    val sourceIssues: List<ClientDraftIssue> get()=buildList {
        val v=preview
        if(v.fullName.isEmpty())add(ClientDraftIssue(ClientDraftField.FULL_NAME,ClientDraftProblem.NAME))
        if(v.fullName.codePointCount(0,v.fullName.length)>255)add(ClientDraftIssue(ClientDraftField.FULL_NAME,ClientDraftProblem.NAME_LENGTH))
        if(v.phone.codePointCount(0,v.phone.length)>32)add(ClientDraftIssue(ClientDraftField.PHONE,ClientDraftProblem.PHONE_LENGTH))
        if(v.email.codePointCount(0,v.email.length)>254)add(ClientDraftIssue(ClientDraftField.EMAIL,ClientDraftProblem.EMAIL_LENGTH))
        // Accepted raw Zod ASCII subset only; no general IDNA/email validation claim.
        if(email.isNotEmpty() && webEmailAccepted(email) && v.email.substringAfterLast('@').split('.').any {it.length>63 || it.endsWith('-')})add(ClientDraftIssue(ClientDraftField.EMAIL,ClientDraftProblem.EMAIL))
        for((field,text) in listOf(ClientDraftField.FULL_NAME to v.fullName,ClientDraftField.PHONE to v.phone,ClientDraftField.EMAIL to v.email,ClientDraftField.NOTES to v.notes)) {
            if(text.codePoints().anyMatch {it==0 || it in 0xD800..0xDFFF})add(ClientDraftIssue(field,ClientDraftProblem.CHARACTERS))
        }
        if(source !in sources)add(ClientDraftIssue(ClientDraftField.SOURCE,ClientDraftProblem.SOURCE))
    }
    val issues get()=(webIssues+sourceIssues).distinct()
}
enum class ClientDraftPhase { CLOSED, EDITING, REVIEW }
data class ClientDraftPreview(val fullName:String,val phone:String,val email:String,val source:String,val notes:String)
data class ClientDraftReview(val selection: ClientDraftSelection,val values: ClientDraftValues,val preview:ClientDraftPreview=values.preview)
data class ClientDraftState(val context: ClientDraftContext? = null,val selection: ClientDraftSelection? = null,val values: ClientDraftValues = ClientDraftValues(),val issues: List<ClientDraftIssue> = emptyList(),val review: ClientDraftReview? = null,val phase: ClientDraftPhase = ClientDraftPhase.CLOSED)
class ClientDraftSession {
    var state = ClientDraftState(); private set
    private var generation = 0
    fun bind(next: ClientDraftContext?) {
        val valid = next?.takeIf { it.valid }
        if (state.context == valid) return
        ++generation; state = ClientDraftState(context=valid)
    }
    fun open(expected: ClientDraftContext): Boolean {
        if (!expected.valid || expected != state.context) return false
        state = state.copy(selection=ClientDraftSelection(expected,++generation),phase=ClientDraftPhase.EDITING,issues=emptyList(),review=null); return true
    }
    fun update(field: ClientDraftField,value: String,expected: ClientDraftSelection) {
        if (state.selection != expected || state.phase != ClientDraftPhase.EDITING) return
        val v = state.values
        val next = when(field) { ClientDraftField.FULL_NAME -> v.copy(fullName=value); ClientDraftField.PHONE -> v.copy(phone=value); ClientDraftField.EMAIL -> v.copy(email=value); ClientDraftField.SOURCE -> v.copy(source=value); ClientDraftField.NOTES -> v.copy(notes=value) }
        state = state.copy(values=next,issues=state.issues.filterNot { it.field==field })
    }
    fun prepare(expected: ClientDraftSelection): Boolean {
        if (state.selection != expected || state.phase != ClientDraftPhase.EDITING) return false
        val issues = state.values.issues; state = state.copy(issues=issues)
        if (issues.isNotEmpty()) return false
        state = state.copy(review=ClientDraftReview(expected,state.values),phase=ClientDraftPhase.REVIEW); return true
    }
    fun back(expected: ClientDraftSelection) {
        if (state.selection != expected) return
        if (state.phase==ClientDraftPhase.REVIEW) state = state.copy(review=null,phase=ClientDraftPhase.EDITING) else close(expected)
    }
    fun close(expected: ClientDraftSelection) {
        if (state.selection != expected) return
        ++generation; state = state.copy(selection=null,review=null,phase=ClientDraftPhase.CLOSED)
    }
    fun discard(expected: ClientDraftSelection) {
        if (state.selection != expected) return
        close(expected); state = state.copy(values=ClientDraftValues(),issues=emptyList())
    }
}
