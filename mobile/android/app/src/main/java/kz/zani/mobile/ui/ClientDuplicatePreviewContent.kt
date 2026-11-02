package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kz.zani.mobile.core.*

// Local result visit only, not a server revision or command attempt.
data class ClientDuplicatePreviewVisit(val generation:Int)
class ClientDuplicatePreviewModel(private val source:SyntheticClientDuplicatePreviewSource) {
    var result by mutableStateOf<ClientDuplicateResponse?>(null);private set
    var loading by mutableStateOf(false);private set
    var problem by mutableStateOf<ReadProblem?>(null);private set
    private var generation by mutableStateOf(0)
    val visit get()=ClientDuplicatePreviewVisit(generation)
    fun clear() {generation++;result=null;loading=false;problem=null}
    suspend fun load(input:ClientDuplicatePreviewInput,expected:ClientDuplicatePreviewVisit) {
        if(visit!=expected || loading || !input.context.valid)return
        clear();val ticket=generation;loading=true
        try {
            val value=source.preview(input);currentCoroutineContext().ensureActive()
            if(ticket!=generation)return
            if(value==null)throw ReadException(ReadProblem.UNAVAILABLE)
            if(!value.valid)throw ReadException(ReadProblem.INVALID_PAYLOAD)
            result=value;loading=false
        } catch(error:Exception) {
            if(ticket==generation) {loading=false;if(error !is CancellationException)problem=(error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE}
            if(error is CancellationException)throw error
        }
    }
}
@Composable fun ClientDuplicatePreviewContent(model:ClientDuplicatePreviewModel,copy:Map<String,String>,isCurrent:()->Boolean,onLoad:(ClientDuplicatePreviewVisit)->Unit) {
    fun text(key:String)=copy[key] ?: key
    val readScope=text("clientDuplicatePreview")
    fun label(field:String)=when(field) {"phone"->text("clientPhone");"email"->text("clientEmail");"whatsapp_id"->"WhatsApp";"telegram_id"->"Telegram";"instagram_id"->"Instagram";else->text("notAvailable")}
    val visit=model.visit
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("clientDuplicatePreview"),style=MaterialTheme.typography.titleMedium,modifier=Modifier.semantics {heading()})
        Text(text("clientDuplicateFixtureOnly"))
        if(model.loading)CircularProgressIndicator(Modifier.semantics {contentDescription=readScope+": "+text("loading");liveRegion=LiveRegionMode.Polite})
        else {
            model.problem?.let {problem->Text(text(when(problem) {ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notAvailable";else->"unavailable"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite;contentDescription=readScope+": "+text(when(problem) {ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notAvailable";else->"unavailable"})})}
            model.result?.let {result->
                if(result.duplicates.isEmpty())Text(text("clientDuplicateEmptyFixture"),modifier=Modifier.semantics {contentDescription=readScope+": "+text("clientDuplicateEmptyFixture")})
                result.duplicates.forEach {row->Column {
                    Text(row.fullName);Text("${text("clientPhone")}: ${row.phone.ifEmpty {text("notAvailable")}}")
                    Text("${text("clientEmail")}: ${row.email.ifEmpty {text("notAvailable")}}")
                    Text("${text("clientDuplicateMatches")}: ${row.matchedFields.joinToString(", ",transform=::label)}")
                }}
            }
            Button(modifier=Modifier.semantics {contentDescription=if(model.problem==null)readScope else readScope+": "+text("retry")},onClick={if(isCurrent())onLoad(visit)}) {Text(text(if(model.problem==null)"clientDuplicatePreview" else "retry"))}
        }
    }
}
