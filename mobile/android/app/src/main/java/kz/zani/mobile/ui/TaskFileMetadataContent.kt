package kz.zani.mobile.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp

@Composable fun TaskFileMetadataContent(model:TaskFileMetadataModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(key:String)=copy[key] ?: key
    val control=model.control
    val fileScope=text("taskFileMetadata");val detailScope=fileScope+": "+text("details")
    if(isCurrent() && control!=null)Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("taskFileMetadata"),style=MaterialTheme.typography.titleSmall)
        Text(text("fixtureMode"),style=MaterialTheme.typography.labelSmall)
        Text(text("fileMetadataWindow"),style=MaterialTheme.typography.labelSmall)
        Text(text("fileVerificationUnknown"))
        val row=model.selected
        when {
            model.loading->Text(text("loading"),modifier=Modifier.semantics {contentDescription=fileScope+": "+text("loading")})
            row!=null->{Text(text("fileOriginalName")+": "+row.originalName);Text(text("fileContentType")+": "+row.contentType.ifEmpty {text("notAvailable")});Text(text("fileSizeBytes")+": "+row.size.toString());Text(text("fileCreatedAt")+": "+row.createdAt);TextButton(modifier=Modifier.semantics {contentDescription=detailScope+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}}
            else->{if(model.failed)Text(text("fileMetadataReadFailed"),modifier=Modifier.semantics {contentDescription=fileScope+": "+text("fileMetadataReadFailed");liveRegion=LiveRegionMode.Polite});if(model.loaded && model.items.isEmpty())Text(text("fileMetadataEmpty"),modifier=Modifier.semantics {contentDescription=fileScope+": "+text("fileMetadataEmpty")});model.items.forEach {item->TextButton(onClick={if(isCurrent())model.select(item,control)}) {Text(item.originalName)}};TextButton(modifier=Modifier.semantics {contentDescription=fileScope+": "+text("fileMetadataLoad")},onClick={if(isCurrent())model.launchLoad(control)}) {Text(text("fileMetadataLoad"))}}
        }
    }
}
