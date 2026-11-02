package kz.zani.mobile.core

data class ClientSearchContext(val business: Int,val epoch: Int) { val valid get()=business>0 && epoch>0 }
data class ClientSearchSelection(val context: ClientSearchContext,val generation: Int)
data class ClientSearchRequest(val selection: ClientSearchSelection,val revision: Int,val query: String)
data class ClientSearchProfileSelection(val selection: ClientSearchSelection,val id: Int,val generation: Int)
data class ClientSearchState(
    val context: ClientSearchContext?=null,val selection: ClientSearchSelection?=null,
    val query: String="",val submitted: String?=null,val items: List<ClientContact> = emptyList(),val total: Int=0,
    val loading: Boolean=false,val loaded: Boolean=false,val problem: ReadProblem?=null,val selectedID: Int?=null,val profileSelection: ClientSearchProfileSelection?=null
) {
    val partial get()=loaded && total>items.size
    val showsEmpty get()=loaded && !loading && problem==null && !partial && items.isEmpty()
}
// One server response window per applied query; not Directory.items filtering.
class ClientSearchSession {
    var state=ClientSearchState();private set
    private var generation=0
    private var revision=0
    private var profileGeneration=0
    private var pending: ClientSearchRequest?=null
    private fun invalidate() {
        ++revision;pending=null;state=state.copy(submitted=null,items=emptyList(),total=0,loading=false,loaded=false,problem=null,selectedID=null,profileSelection=null)
    }
    fun bind(next: ClientSearchContext?) {
        val next=next?.takeIf {it.valid}
        if(next==state.context)return
        invalidate();++generation;state=ClientSearchState(context=next)
    }
    fun open(expected: ClientSearchContext): Boolean {
        if(!expected.valid || state.context!=expected)return false
        invalidate();state=state.copy(selection=ClientSearchSelection(expected,++generation));return true
    }
    fun update(value: String,expected: ClientSearchSelection) {
        // Exact raw sequence: do not normalize NFC/NFD or discard combining edits.
        if(state.selection!=expected || state.query==value)return
        invalidate();state=state.copy(query=value)
    }
    fun clear(expected: ClientSearchSelection) {
        if(state.selection!=expected)return
        invalidate();state=state.copy(query="")
    }
    fun begin(expected: ClientSearchSelection): ClientSearchRequest? {
        if(state.selection!=expected)return null
        invalidate();val query=SourceTextTrim.pythonStrip(state.query)
        state=state.copy(submitted=query,loading=true)
        return ClientSearchRequest(expected,revision,query).also {pending=it}
    }
    fun accept(page: ClientList,request: ClientSearchRequest): Boolean {
        if(pending!=request || state.selection!=request.selection)return false
        if(page.business!=request.selection.context.business || page.total<page.items.size || page.items.size>50 || page.items.any {it.id<=0} || page.items.map {it.id}.distinct().size!=page.items.size) {
            fail(ReadProblem.INVALID_PAYLOAD,request);return false
        }
        pending=null;state=state.copy(items=page.items,total=page.total,loading=false,loaded=true,problem=null);return true
    }
    fun fail(problem: ReadProblem,request: ClientSearchRequest) {
        if(pending!=request || state.selection!=request.selection)return
        pending=null;state=state.copy(loading=false,loaded=false,items=emptyList(),total=0,selectedID=null,profileSelection=null,problem=problem)
    }
    fun cancel(request: ClientSearchRequest) {
        if(pending==request && state.selection==request.selection)invalidate()
    }
    fun select(id: Int,expected: ClientSearchSelection): Boolean {
        if(state.selection!=expected || !state.loaded || state.loading || state.problem!=null || state.items.none {it.id==id})return false
        state=state.copy(selectedID=id,profileSelection=ClientSearchProfileSelection(expected,id,++profileGeneration));return true
    }
    fun backProfile(expected: ClientSearchSelection) {if(state.selection==expected)state=state.copy(selectedID=null,profileSelection=null)}
    fun backProfile(expected: ClientSearchSelection,profile: ClientSearchProfileSelection) {if(state.profileSelection==profile)backProfile(expected)}
    fun close(expected: ClientSearchSelection) {
        if(state.selection!=expected)return
        invalidate();++generation;state=state.copy(selection=null)
    }
}
