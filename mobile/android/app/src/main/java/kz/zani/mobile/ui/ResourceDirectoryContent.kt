package kz.zani.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*

@Composable fun ResourceDirectoryContent(model:ResourceDirectoryModel,copy:Map<String,String>,onClose:()->Unit,useChoiceLabel:String?=null,useChoice:((ResourceDirectoryReadChoice,ResourceDirectoryControl?)->Unit)?=null,isCurrent:()->Boolean={true}) {
    fun text(key:String)=copy[key] ?: key
    val control=model.control
    val readScope=text("resources")+(if(model.selected==null)"" else ": "+text("details"))
    val scope=rememberCoroutineScope()
    val announcement=Modifier.semantics {liveRegion=LiveRegionMode.Polite}
    BackHandler(enabled=model.presented,onBack=onClose)
    Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        TextButton(onClick=onClose) {Text(text("resourceDirectoryClose"))}
        Text(text("resources"),style=MaterialTheme.typography.titleLarge)
        model.owner?.let {Text(it.scope.business.name)}
        Text(text("resourceDirectoryWindowBoundary"),style=MaterialTheme.typography.bodySmall)
        if(model.selected!=null)TextButton(onClick={if(isCurrent())model.backToWindow(control)}) {Text(text("resourceDirectoryBackToWindow"))}
        val problem=model.problem;val detail=model.detail;val window=model.window
        when {
            model.loading->CircularProgressIndicator(modifier=announcement.semantics {contentDescription=readScope+": "+text("loading")})
            problem!=null->{Text(text(when(problem){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}),modifier=announcement.semantics {contentDescription=readScope+": "+text(when(problem){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"})});if(model.selected==null)Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick={scope.launch {if(isCurrent())model.reload(control)}}) {Text(text("retry"))}}
            detail!=null->{
                if(detail!=model.selected)Text(text("resourceDirectoryObservedChange"),modifier=announcement)
                Text(detail.name)
                Text("${text("resourceDirectoryType")}: ${text(if(detail.hasKnownType)detail.typeCopyKey else "resourceDirectoryTypeUnknown")}")
                Text(text(if(detail.isActive)"referenceActive" else "referenceInactive"))
                val choice=model.choice
                if(choice!=null) {Text(text("resourceDirectoryReadChoice"),modifier=announcement);Text(choice.item.name);Text(text("resourceDirectoryReadOnlyBoundary"),style=MaterialTheme.typography.bodySmall);if(useChoiceLabel!=null && useChoice!=null)Button(onClick={if(isCurrent())useChoice(choice,control)}) {Text(useChoiceLabel)}}
                else Button(onClick={if(isCurrent())model.choose(control)}) {Text(text("resourceDirectoryChooseRead"))}
            }
            window!=null->{
                Text("${text("resourceDirectoryWindowCount")}: ${window.items.size}")
                if(window.items.isEmpty())Text(text("resourceDirectoryWindowEmpty"),modifier=announcement)
                window.items.forEach {row->TextButton(onClick={scope.launch {if(isCurrent())model.select(row,control)}}) {Column {Text(row.name);Text(text(if(row.isActive)"referenceActive" else "referenceInactive"))}}}
                Button(onClick={scope.launch {if(isCurrent())model.reload(control)}}) {Text(text("resourceDirectoryRefresh"))}
            }
        }
    }
}
