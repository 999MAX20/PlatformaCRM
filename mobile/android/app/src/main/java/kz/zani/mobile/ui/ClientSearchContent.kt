package kz.zani.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun ClientSearchContent(model: ClientSearchModel,selection: ClientSearchSelection,copy: Map<String,String>,timezone: String?,language: String,modifier: Modifier,isCurrent:()->Boolean) {
    val state=model.state
    if(!isCurrent() || state.selection!=selection)return
    fun text(key: String)=copy[key] ?: key
    fun value(raw: String?)=raw?.takeIf {it.isNotBlank()} ?: text("notAvailable")
    fun error(problem: ReadProblem)=text(when(problem){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notAvailable";else->"unavailable"})
    val scroll=rememberLazyListState()
    val announcement=Modifier.semantics {liveRegion=LiveRegionMode.Polite}
    val control=model.control;val input=model.inputControl
    val readScope=text("clients")+": "+text("clientServerSearch")
    fun ownsControl()=control?.selection==selection && model.matches(control) && isCurrent()
    fun ownsInput()=input!=null && input.selection==selection && model.inputControl==input && isCurrent()
    val profileSelection=state.profileSelection
    val workReturn=model.profile.workReturnControl
    BackHandler {if(ownsControl())model.back(control=control,workReturn=workReturn)}
    Column(modifier,verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Text(text("clientServerSearch"),style=MaterialTheme.typography.titleMedium,modifier=Modifier.semantics {heading()})
        TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("back")},onClick={if(ownsControl())model.back(control=control,workReturn=workReturn)}) {Text(text("back"))}
        val id=profileSelection?.id
        if(id!=null && profileSelection!=null) {
            ClientProfileContent(model.profile,selection.context.business,id,copy,timezone,language,Modifier.weight(1f),onContact={_,_->},onRetry={if(ownsControl())model.retryProfile(expected=control)},isCurrent={ownsControl() && model.state.profileSelection==profileSelection})
        } else {
            OutlinedTextField(value=state.query,onValueChange={if(ownsInput())model.update(it,input=input)},label={Text(text("clientSearch"))},singleLine=true,modifier=Modifier.fillMaxWidth(),keyboardOptions=KeyboardOptions(imeAction=ImeAction.Search),keyboardActions=KeyboardActions(onSearch={if(ownsControl())model.submit(expected=control)}))
            Row(horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("searchSubmit")},onClick={if(ownsControl())model.submit(expected=control)},enabled=!state.loading) {Text(text("searchSubmit"))}
                TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("searchClear")},onClick={if(ownsControl())model.clear(expected=control)}) {Text(text("searchClear"))}
            }
            if(state.loading)CircularProgressIndicator(Modifier.semantics {contentDescription=readScope+": "+text("loading");liveRegion=LiveRegionMode.Polite})
            else if(state.problem!=null) {
                Text(error(state.problem),modifier=announcement.semantics {contentDescription=readScope+": "+error(state.problem)})
                Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick={if(ownsControl())model.submit(expected=control)}) {Text(text("retry"))}
            } else if(state.loaded) {
                Text(text("clientSearchCount").replace("{loaded}",state.items.size.toString()).replace("{total}",state.total.toString()),modifier=announcement)
                if(state.partial)Text(text("partial"),modifier=announcement)
                if(state.showsEmpty)Text(text(if(state.submitted?.isEmpty()==true)"clientsEmpty" else "noResults"),modifier=announcement)
                LazyColumn(Modifier.weight(1f),state=scroll) {
                    items(state.items,key={it.id}) {client->ListItem(headlineContent={Text(value(client.title))},supportingContent={Text("${text("clientPhone")}: ${value(client.phone)}")},modifier=Modifier.clickable(role=Role.Button){if(ownsControl())model.openClient(client.id,expected=control)})}
                }
            }
        }
    }
}
