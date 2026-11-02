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

@Composable fun ClientDraftEntry(model:ClientDraftModel,context:ClientDraftContext,copy:Map<String,String>,isCurrent:()->Boolean,onOpen:(ClientDraftEntryControl)->Unit) {
    val entry=model.entryControl
    if(isCurrent() && entry!=null && entry.context==context)TextButton(onClick={if(isCurrent() && model.entryControl==entry)onOpen(entry)}) {Text(copy["clientDraftTitle"] ?: "clientDraftTitle")}
}
@Composable fun ClientDraftContent(model: ClientDraftModel,selection: ClientDraftSelection,copy: Map<String,String>,modifier: Modifier,isCurrent:()->Boolean) {
    val state=model.state
    val control=model.control;val input=model.inputControl;val returnControl=model.returnControl;val question=model.clearConfirmation
    if(!isCurrent() || state.selection!=selection)return
    fun text(key: String)=copy[key] ?: key
    fun source(raw: String)=when(raw) { "parser" -> text("clientDraftSourceParser"); "other" -> text("clientDraftSourceOther"); else -> ReadChannelText.label(raw,::text) }
    fun issue(field: ClientDraftField): String? = state.issues.firstOrNull { it.field==field }?.let { when(it.problem) {
        ClientDraftProblem.NAME -> text("clientDraftNameError")
        ClientDraftProblem.NAME_LENGTH -> text("clientDraftMaxLength").replace("{limit}","255")
        ClientDraftProblem.PHONE_LENGTH -> text("clientDraftMaxLength").replace("{limit}","32")
        ClientDraftProblem.EMAIL -> text("clientDraftEmailError")
        ClientDraftProblem.EMAIL_LENGTH -> text("clientDraftMaxLength").replace("{limit}","254")
        ClientDraftProblem.CHARACTERS -> text("taskCancelReasonCharacters")
        ClientDraftProblem.SOURCE -> text("notAvailable")
    } }
    val focus=remember(selection) { ClientDraftField.entries.associateWith { FocusRequester() } }
    var sourceMenu by remember(input) { mutableStateOf(false) }
    BackHandler(onBack={if(isCurrent())model.back(expected=returnControl)})
    Column(modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Text(text("clientDraftTitle"),style=MaterialTheme.typography.titleLarge,modifier=Modifier.semantics { heading() })
        Text(text("clientDraftOnly"),modifier=Modifier.semantics { liveRegion=LiveRegionMode.Polite })
        TextButton(modifier=Modifier.semantics {contentDescription=text("clientDraftTitle")+": "+text("back")},onClick={if(isCurrent())model.back(expected=returnControl)}) { Text(text("back")) }
        val submission=model.submission
        if(model.submissionBlocked) {
            if(submission!=null) {
                Text(submission.attempt.review.preview.fullName)
                val key=when(submission.phase) {ClientCreateAttemptPhase.PENDING->"taskCommentFakePending";ClientCreateAttemptPhase.CONFIRMED->"clientCreateFakeConfirmed";ClientCreateAttemptPhase.REJECTED->"taskCommentFakeRejected";ClientCreateAttemptPhase.UNKNOWN->"taskCommentFakeUnknown"}
                Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                if(submission.phase==ClientCreateAttemptPhase.CONFIRMED || submission.phase==ClientCreateAttemptPhase.REJECTED)Button(modifier=Modifier.semantics {contentDescription=text("clientDraftTitle")+": "+text(if(submission.phase==ClientCreateAttemptPhase.CONFIRMED)"taskCommentFakeDone" else "taskCommentFakeEdit")},onClick={if(isCurrent())model.acknowledge(control,submission)}) {Text(text(if(submission.phase==ClientCreateAttemptPhase.CONFIRMED)"taskCommentFakeDone" else "taskCommentFakeEdit"))}
            } else Text(text("taskCommentFakeQuarantined"))
        } else if (state.phase==ClientDraftPhase.REVIEW && state.review?.selection==selection) {
            val review=state.review!!.preview
            Text("${text("clientName")}: ${review.fullName}"); Text("${text("clientPhone")}: ${review.phone.ifBlank { text("notAvailable") }}")
            Text("${text("clientEmail")}: ${review.email.ifBlank { text("notAvailable") }}"); Text("${text("clientDraftSource")}: ${source(review.source)}")
            Text("${text("notes")}: ${review.notes}")
            model.duplicates?.let {ClientDuplicatePreviewContent(it,copy,isCurrent={isCurrent() && model.control==control && model.clearConfirmation==null},onLoad={visit->model.launchDuplicates(control,visit)})}
            val snapshot=state.review!!;if(model.canSubmit)Button(onClick={if(isCurrent())model.launchSubmit(snapshot,control)}) {Text(text("clientCreateFakeSubmit"))}
        } else {
            val fields=listOf(ClientDraftField.FULL_NAME to "clientName",ClientDraftField.PHONE to "clientPhone",ClientDraftField.EMAIL to "clientEmail",ClientDraftField.NOTES to "notes")
            fields.forEach { (field,key) ->
                val value=when(field) { ClientDraftField.FULL_NAME -> state.values.fullName; ClientDraftField.PHONE -> state.values.phone; ClientDraftField.EMAIL -> state.values.email; else -> state.values.notes }
                val error=issue(field)
                OutlinedTextField(value=value,onValueChange={if(isCurrent())model.update(field,it,input)},label={Text(text(key))},isError=error!=null,
                    supportingText={if(error!=null)Text(error,modifier=Modifier.semantics { liveRegion=LiveRegionMode.Polite })},
                    keyboardOptions=KeyboardOptions(keyboardType=when(field){ClientDraftField.PHONE -> KeyboardType.Phone;ClientDraftField.EMAIL -> KeyboardType.Email;else -> KeyboardType.Text}),
                    singleLine=field!=ClientDraftField.NOTES,minLines=if(field==ClientDraftField.NOTES)4 else 1,modifier=Modifier.fillMaxWidth().focusRequester(focus.getValue(field)))
            }
            Box {
                OutlinedButton(onClick={if(isCurrent() && model.inputControl==input)sourceMenu=true}) { Text("${text("clientDraftSource")}: ${source(state.values.source)}") }
                DropdownMenu(expanded=sourceMenu,onDismissRequest={sourceMenu=false}) {
                    ClientDraftValues.sources.forEach { value -> DropdownMenuItem(modifier=Modifier.semantics {selected=value==state.values.source},text={Text(source(value))},onClick={if(isCurrent() && model.inputControl==input) {sourceMenu=false;model.update(ClientDraftField.SOURCE,value,input)}}) }
                }
            }
            issue(ClientDraftField.SOURCE)?.let { Text(text("clientDraftSource")+": "+it,modifier=Modifier.semantics { liveRegion=LiveRegionMode.Polite }) }
            Button(onClick={if(isCurrent() && model.control==control) {model.prepare(expected=control);model.state.issues.firstOrNull()?.field?.takeIf {it!=ClientDraftField.SOURCE}?.let {focus.getValue(it).requestFocus()}}}) { Text(text("clientDraftReview")) }
        }
        if(!model.submissionBlocked)TextButton(modifier=Modifier.semantics {contentDescription=text("clientDraftTitle")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.askClear(control)}) { Text(text("clientDraftClear")) }
    }
    if(question!=null)AlertDialog(onDismissRequest={model.dismissClear(question)},title={Text(text("clientDraftClearQuestion"))},confirmButton={TextButton(modifier=Modifier.semantics {contentDescription=text("clientDraftTitle")+": "+text("clientDraftClearQuestion")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.confirmClear(question)}){Text(text("clientDraftClear"))}},dismissButton={TextButton(modifier=Modifier.semantics {contentDescription=text("clientDraftTitle")+": "+text("clientDraftClearQuestion")+": "+text("clientDraftCancel")},onClick={model.dismissClear(question)}){Text(text("clientDraftCancel"))}})
}
