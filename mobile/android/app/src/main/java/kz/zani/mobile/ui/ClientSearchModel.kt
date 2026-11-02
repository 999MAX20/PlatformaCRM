package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*
import kz.zani.mobile.data.ClientSearchRepository

// Local UI visits, never wire versions, grants or request keys.
data class ClientSearchInputControl(val selection:ClientSearchSelection,val generation:Int)
data class ClientSearchControl(val selection:ClientSearchSelection,val generation:Int,val profile:ClientSearchProfileSelection?,val read:ClientReadSelection?)

// Child of the existing Directory owner and its coroutine scope.
class ClientSearchModel(private val repository: ClientSearchRepository,private val ownerScope: CoroutineScope) {
    private val session=ClientSearchSession()
    private var windowRevision by mutableStateOf(0)
    private var inputRevision by mutableStateOf(0)
    var state by mutableStateOf(session.state);private set
    val profile=ClientProfileViewModel(repository,ownerScope)
    fun bind(context: ClientSearchContext?) {
        if(state.context!=context)profile.clear()
        val previous=state.context;session.bind(context);state=session.state;if(state.context!=previous){++windowRevision;++inputRevision}
    }
    fun open(context: ClientSearchContext) {
        if(state.context!=context)return
        profile.clear();if(session.open(context)){++windowRevision;++inputRevision};state=session.state
    }
    fun update(query: String,selection: ClientSearchSelection) {
        if(state.selection!=selection)return
        // Keep the raw query and its window distinct for every code-unit change.
        if(query!=state.query){++windowRevision;if(state.profileSelection!=null)++inputRevision;profile.clear()}
        session.update(query,selection);state=session.state
    }
    fun clear(selection: ClientSearchSelection) {
        if(state.selection!=selection)return
        ++windowRevision;++inputRevision;profile.clear();session.clear(selection);state=session.state
    }
    fun submit(selection: ClientSearchSelection) {
        val hadProfile=state.profileSelection!=null
        val request=session.begin(selection) ?: return
        val ticket=++windowRevision;if(hadProfile)++inputRevision
        profile.clear();state=session.state
        ownerScope.launch {
            try {session.accept(repository.searchClients(selection.context.business,request.query),request)}
            catch(error: Exception) {
                if(error is CancellationException) {session.cancel(request);state=session.state;if(windowRevision==ticket)++windowRevision;throw error}
                session.fail((error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE,request)
            }
            state=session.state;if(windowRevision==ticket)++windowRevision
        }
    }
    fun openClient(id: Int,selection: ClientSearchSelection) {
        if(!session.select(id,selection))return
        val ticket=++windowRevision;++inputRevision;profile.clear();state=session.state;val selected=state.profileSelection
        profile.loadObserved(selection.context.business,id) {if(windowRevision==ticket && state.profileSelection==selected)++windowRevision}
    }
    fun retryProfile(selection: ClientSearchSelection,expectedProfile: ClientSearchProfileSelection) {
        if(state.selection!=selection || state.profileSelection!=expectedProfile)return
        val ticket=++windowRevision
        profile.loadObserved(selection.context.business,expectedProfile.id) {if(windowRevision==ticket && state.profileSelection==expectedProfile)++windowRevision}
    }
    fun backProfile(selection: ClientSearchSelection) {
        val current=state.profileSelection ?: return
        backProfile(selection,current)
    }
    fun backProfile(selection: ClientSearchSelection,expectedProfile: ClientSearchProfileSelection) {
        if(state.selection!=selection || state.profileSelection!=expectedProfile)return
        ++windowRevision;++inputRevision;profile.clear();session.backProfile(selection,expectedProfile);state=session.state
    }
    fun back(selection: ClientSearchSelection,expectedProfile: ClientSearchProfileSelection?) {
        if(state.selection!=selection || state.profileSelection!=expectedProfile)return
        if(expectedProfile!=null) {if(!profile.backWork())backProfile(selection,expectedProfile)} else close(selection)
    }
    fun back(selection:ClientSearchSelection,expectedProfile:ClientSearchProfileSelection?,workReturn:ClientWorkReturnControl?) {
        if(state.selection!=selection || state.profileSelection!=expectedProfile)return
        if(expectedProfile!=null) {if(profile.backWork(workReturn)==ClientWorkBack.NO_CHILD)backProfile(selection,expectedProfile)} else close(selection)
    }
    val inputControl:ClientSearchInputControl? get()=state.selection?.let {ClientSearchInputControl(it,inputRevision)}
    val control:ClientSearchControl? get()=state.selection?.let {ClientSearchControl(it,windowRevision,state.profileSelection,profile.readSelection)}
    fun matches(expected:ClientSearchControl?)=expected!=null && control==expected
    fun update(value:String,input:ClientSearchInputControl?) {if(input!=null && inputControl==input && state.profileSelection==null)update(value,input.selection)}
    fun clear(expected:ClientSearchControl?) {if(expected!=null && matches(expected) && state.profileSelection==null)clear(expected.selection)}
    fun submit(expected:ClientSearchControl?) {if(expected!=null && matches(expected) && !state.loading && state.profileSelection==null)submit(expected.selection)}
    fun openClient(id:Int,expected:ClientSearchControl?) {if(expected!=null && matches(expected) && state.profileSelection==null)openClient(id,expected.selection)}
    fun retryProfile(expected:ClientSearchControl?) {val selected=state.profileSelection;if(expected!=null && matches(expected) && !profile.state.loading && selected!=null)retryProfile(expected.selection,selected)}
    fun backProfile(expected:ClientSearchControl?) {val selected=state.profileSelection;if(expected!=null && matches(expected) && selected!=null)backProfile(expected.selection,selected)}
    fun back(control:ClientSearchControl?,workReturn:ClientWorkReturnControl?) {if(control==null || !matches(control))return;if(state.profileSelection!=null){if(profile.backWork(workReturn)==ClientWorkBack.NO_CHILD)backProfile(control)} else close(control)}
    fun close(expected:ClientSearchControl?) {if(expected!=null && matches(expected))close(expected.selection)}
    fun close(selection: ClientSearchSelection) {
        if(state.selection!=selection)return
        ++windowRevision;++inputRevision;profile.clear();session.close(selection);state=session.state
    }
}
