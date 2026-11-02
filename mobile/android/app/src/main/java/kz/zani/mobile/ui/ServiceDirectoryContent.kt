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

@Composable fun ServiceDirectoryContent(model:ServiceDirectoryModel,copy:Map<String,String>,onClose:()->Unit,useChoiceLabel:String?=null,useChoice:((ServiceDirectoryReadChoice,ServiceDirectoryControl?)->Unit)?=null,isCurrent:()->Boolean={true}) {
    fun text(key:String)=copy[key] ?: key
    val control=model.control
    val readScope=text("services")+(if(model.selected==null)"" else ": "+text("details"))
    val scope=rememberCoroutineScope()
    val announcement=Modifier.semantics {liveRegion=LiveRegionMode.Polite}
    BackHandler(enabled=model.presented,onBack=onClose)
    Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        TextButton(onClick=onClose) {Text(text("serviceClose"))}
        Text(text("services"),style=MaterialTheme.typography.titleLarge)
        model.owner?.let {Text(it.scope.business.name)}
        Text(text("serviceWindowBoundary"),style=MaterialTheme.typography.bodySmall)
        if(model.selected!=null)TextButton(onClick={if(isCurrent())model.backToWindow(control)}) {Text(text("serviceBackToWindow"))}
        val problem=model.problem;val detail=model.detail;val window=model.window
        when {
            model.loading->CircularProgressIndicator(modifier=announcement.semantics {contentDescription=readScope+": "+text("loading")})
            problem!=null->{Text(text(when(problem){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}),modifier=announcement.semantics {contentDescription=readScope+": "+text(when(problem){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"})});if(model.selected==null)Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick={scope.launch {if(isCurrent())model.reload(control)}}) {Text(text("retry"))}}
            detail!=null->{
                if(detail!=model.selected)Text(text("serviceObservedChange"),modifier=announcement)
                Text(detail.name);if(detail.description.isNotEmpty())Text(detail.description)
                Text("${text("serviceDurationMinutes")}: ${detail.durationMinutes}")
                Text("${text("servicePriceFrom")}: ${detail.priceFrom ?: text("notAvailable")}")
                Text(text(if(detail.isActive)"referenceActive" else "referenceInactive"))
                val choice=model.choice
                if(choice!=null) {Text(text("serviceReadChoice"),modifier=announcement);Text(choice.item.name);Text(text("serviceReadOnlyBoundary"),style=MaterialTheme.typography.bodySmall);if(useChoiceLabel!=null && useChoice!=null)Button(onClick={if(isCurrent())useChoice(choice,control)}) {Text(useChoiceLabel)}}
                else Button(onClick={if(isCurrent())model.choose(control)}) {Text(text("serviceChooseRead"))}
            }
            window!=null->{
                Text("${text("serviceWindowCount")}: ${window.items.size}")
                if(window.items.isEmpty())Text(text("serviceWindowEmpty"),modifier=announcement)
                window.items.forEach {row->TextButton(onClick={scope.launch {if(isCurrent())model.select(row,control)}}) {Column {Text(row.name);Text(text(if(row.isActive)"referenceActive" else "referenceInactive"))}}}
                Button(onClick={scope.launch {if(isCurrent())model.reload(control)}}) {Text(text("serviceRefresh"))}
            }
        }
    }
}
