package kz.zani.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.semantics.*
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun ClientEditEntry(model: ClientEditModel,context: ClientEditContext,copy: Map<String,String>,isCurrent:()->Boolean) {
    fun text(key: String)=copy[key] ?: key
    val state=model.state
    val entry=model.entryControl;val confirmation=model.confirmation
    if(!isCurrent() || entry?.context!=context)return
    if(state.available)TextButton(onClick={if(isCurrent())model.open(entry)}) {Text(text("clientEditTitle"))}
    else Text(text(if(state.needsReset)"clientEditOriginChanged" else "clientEditUnavailable"),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
    if(state.needsReset && model.hasStoredChanges)TextButton(modifier=Modifier.semantics {contentDescription=text("clientEditTitle")+": "+text("clientEditCancel")},onClick={if(isCurrent())model.askDiscard(entry)}) {Text(text("clientEditCancel"))}
    if(confirmation!=null && confirmation.entry==entry)ClientEditConfirmationDialog(model,confirmation,copy,isCurrent)
}
@Composable fun ClientEditContent(model: ClientEditModel,selection: ClientEditSelection,copy: Map<String,String>,modifier: Modifier,isCurrent:()->Boolean) {
    val state=model.state;val values=state.values ?: return
    val control=model.control;val input=model.inputControl;val confirmation=model.confirmation
    if(!isCurrent() || state.selection!=selection || !state.available)return
    fun text(key: String)=copy[key] ?: key
    fun label(field: ClientDraftField)=text(when(field){ClientDraftField.FULL_NAME->"clientName";ClientDraftField.PHONE->"clientPhone";ClientDraftField.EMAIL->"clientEmail";ClientDraftField.SOURCE->"clientDraftSource";ClientDraftField.NOTES->"notAvailable"})
    fun source(value: String)=when(value){"parser"->text("clientDraftSourceParser");"other"->text("clientDraftSourceOther");else->ReadChannelText.label(value,::text)}
    fun displayed(value: String,field: ClientDraftField)=if(value.isEmpty())text("clientEditEmpty") else if(field==ClientDraftField.SOURCE)source(value) else value
    fun issue(field: ClientDraftField)=state.issues.firstOrNull {it.field==field}?.let {when(it.problem){ClientDraftProblem.NAME->text("clientDraftNameError");ClientDraftProblem.NAME_LENGTH->text("clientDraftMaxLength").replace("{limit}","255");ClientDraftProblem.PHONE_LENGTH->text("clientDraftMaxLength").replace("{limit}","32");ClientDraftProblem.EMAIL->text("clientDraftEmailError");ClientDraftProblem.EMAIL_LENGTH->text("clientDraftMaxLength").replace("{limit}","254");ClientDraftProblem.CHARACTERS->text("taskCancelReasonCharacters");ClientDraftProblem.SOURCE->text("notAvailable")}}
    val focus=remember(selection) {ClientEditValues.fields.associateWith {FocusRequester()}}
    var menu by remember(input) {mutableStateOf(false)}
    fun back() {if(isCurrent()) {if(confirmation!=null)model.dismiss(confirmation) else model.back(expected=control)}}
    BackHandler {back()}
    Column(modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Text(text("clientEditTitle"),style=MaterialTheme.typography.titleLarge,modifier=Modifier.semantics {heading()})
        Text(text("clientDraftOnly"));TextButton(modifier=Modifier.semantics {contentDescription=text("clientEditTitle")+": "+text("back")},onClick={back()}) {Text(text("back"))}
        val review=state.review
        if(state.phase==ClientDraftPhase.REVIEW && review!=null && review.selection==selection) {
            if(review.changed.isEmpty())Text(text("clientEditNoChanges"))
            review.changed.forEach {field->
                Text(label(field),style=MaterialTheme.typography.titleMedium)
                Text("${text("clientEditOriginal")}: ${displayed(review.original.value(field),field)}")
                Text("${text("clientEditModified")}: ${displayed(review.values.value(field),field)}")
            }
        } else {
            listOf(ClientDraftField.FULL_NAME,ClientDraftField.PHONE,ClientDraftField.EMAIL).forEach {field->
                OutlinedTextField(value=values.value(field),onValueChange={if(isCurrent())model.update(field,it,input)},label={Text(label(field))},singleLine=true,isError=issue(field)!=null,supportingText={issue(field)?.let {Text(it,modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})}},keyboardOptions=KeyboardOptions(keyboardType=when(field){ClientDraftField.PHONE->KeyboardType.Phone;ClientDraftField.EMAIL->KeyboardType.Email;else->KeyboardType.Text}),modifier=Modifier.fillMaxWidth().focusRequester(focus.getValue(field)))
            }
            Box {
                OutlinedButton(onClick={if(isCurrent() && model.inputControl==input)menu=true}) {Text("${label(ClientDraftField.SOURCE)}: ${source(values.source)}")}
                DropdownMenu(expanded=menu,onDismissRequest={menu=false}) {ClientDraftValues.sources.forEach {value->DropdownMenuItem(modifier=Modifier.semantics {selected=value==values.source},text={Text(source(value))},onClick={if(isCurrent() && model.inputControl==input) {menu=false;model.update(ClientDraftField.SOURCE,value,input)}})}}
            }
            issue(ClientDraftField.SOURCE)?.let {Text(label(ClientDraftField.SOURCE)+": "+it,modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})}
            Button(onClick={if(isCurrent() && model.control==control) {model.prepare(expected=control);model.state.issues.firstOrNull()?.field?.takeIf {it!=ClientDraftField.SOURCE}?.let {focus.getValue(it).requestFocus()}}}) {Text(text("clientDraftReview"))}
        }
        TextButton(modifier=Modifier.semantics {contentDescription=text("clientEditTitle")+": "+text("clientEditCancel")},onClick={if(isCurrent())model.askCancel(control)}) {Text(text("clientEditCancel"))}
    }
    if(confirmation!=null && confirmation.control==control)ClientEditConfirmationDialog(model,confirmation,copy,isCurrent)
}

@Composable private fun ClientEditConfirmationDialog(model:ClientEditModel,confirmation:ClientEditConfirmation,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(key:String)=copy[key] ?: key
    AlertDialog(onDismissRequest={model.dismiss(confirmation)},title={Text(text("clientEditCancelQuestion"))},
        confirmButton={TextButton(modifier=Modifier.semantics {contentDescription=text("clientEditTitle")+": "+text("clientEditCancelQuestion")+": "+text("clientEditCancel")},onClick={if(isCurrent())model.confirm(confirmation)}) {Text(text("clientEditCancel"))}},
        dismissButton={TextButton(modifier=Modifier.semantics {contentDescription=text("clientEditTitle")+": "+text("clientEditCancelQuestion")+": "+text("clientDraftCancel")},onClick={model.dismiss(confirmation)}) {Text(text("clientDraftCancel"))}})
}
