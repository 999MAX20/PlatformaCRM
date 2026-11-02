package kz.zani.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun QuickReplyContent(model: QuickReplyModel,selection: QuickReplySelection,copy: Map<String,String>,insert: (QuickReplyChoice,QuickReplyControl?)->Unit,modifier: Modifier,isCurrent:()->Boolean) {
    val state=model.state
    val control=model.control;val input=model.inputControl
    if(!isCurrent() || state.selection!=selection)return
    fun text(key: String)=copy[key] ?: key
    val readScope=text("quickReplyTitle")
    fun error(problem: ReadProblem)=text(when(problem){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notAvailable";else->"unavailable"})
    val focus=remember(selection) {FocusRequester()}
    val announcement=Modifier.semantics {liveRegion=LiveRegionMode.Polite}
    BackHandler {if(isCurrent())model.close(expected=control)}
    Column(modifier,verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Text(text("quickReplyTitle"),style=MaterialTheme.typography.titleMedium,modifier=Modifier.semantics {heading()})
        TextButton(onClick={if(isCurrent())model.close(expected=control)}) {Text(text("clientDraftCancel"))}
        OutlinedTextField(value=state.query,onValueChange={if(isCurrent())model.search(it,input)},label={Text(text("quickReplySearch"))},singleLine=true,modifier=Modifier.fillMaxWidth().focusRequester(focus))
        if(state.loading)CircularProgressIndicator(Modifier.semantics {contentDescription=readScope+": "+text("loading");liveRegion=LiveRegionMode.Polite})
        else if(state.problem!=null) {
            Text(error(state.problem),modifier=announcement.semantics {contentDescription=readScope+": "+error(state.problem)})
            Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick={if(isCurrent())model.retry(expected=control)}) {Text(text("retry"))}
        } else if(state.loaded) {
            if(state.partial)Text(text("partial"),modifier=announcement.semantics {contentDescription=readScope+": "+text("partial")})
            if(model.showsEmpty)Text(text(if(state.query.isEmpty())"quickReplyEmpty" else "noResults"),modifier=announcement.semantics {contentDescription=readScope+": "+text(if(state.query.isEmpty())"quickReplyEmpty" else "noResults")})
            LazyColumn(Modifier.weight(1f)) {
                items(model.choices,key={it.template.id}) {choice->
                    ListItem(headlineContent={Text(choice.template.title)},supportingContent={Column {
                        Text(choice.template.text)
                        if(choice.template.category.isNotEmpty())Text(choice.template.category)
                        Text(if(choice.template.channel=="all")text("quickReplyAllChannels") else ReadChannelText.label(choice.template.channel,::text))
                    }},modifier=Modifier.clickable(role=Role.Button){if(isCurrent())insert(choice,control)})
                }
            }
        }
    }
    LaunchedEffect(selection) {focus.requestFocus()}
}
