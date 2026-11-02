package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class AppointmentReferenceTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun catalog()=JSONObject(fixture("appointment-reference-read-cases"))
    private fun kind(row:JSONObject)=if(row.getString("kind")=="service")AppointmentReferenceKind.SERVICE else AppointmentReferenceKind.RESOURCE
    private class Controlled:AppointmentReferenceRepository {
        val calls=mutableListOf<Triple<AppointmentReferenceKind,Int,Int>>();val pending=mutableListOf<CompletableDeferred<AppointmentReferenceDetail>>()
        override suspend fun reference(kind:AppointmentReferenceKind,business:Int,id:Int):AppointmentReferenceDetail {calls+=Triple(kind,business,id);return CompletableDeferred<AppointmentReferenceDetail>().also {pending+=it}.await()}
    }
    private fun detail(kind:AppointmentReferenceKind,id:Int=if(kind==AppointmentReferenceKind.SERVICE)8001 else 9001)=AppointmentReferenceDetail.decode(fixture("${if(kind==AppointmentReferenceKind.SERVICE)"service" else "resource"}-reference-$id"),kind)!!
    private fun check(block:suspend TestScope.(AgendaViewModel,AppointmentRelationsViewModel,Controlled,MutableList<ReadRequest>)->Unit)=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val calls=mutableListOf<ReadRequest>();val base=APIReadRepository(ReadTransport {q->calls+=q;val name=when {q.path.endsWith("/bootstrap/")->"bootstrap";q.path.endsWith("/appointments/")->"appointments-${q.query["business"]}";else->"appointment-${q.query["business"]}-${q.path.trimEnd('/').substringAfterLast('/')}"};ReadResponse(200,fixture(name))});val port=Controlled();val links=AppointmentRelationsViewModel(base,port);val m=AgendaViewModel(base,initialDay={"2026-10-28"},relations=links)
        try {m.start();runCurrent();m.openDetail(501,m.control);runCurrent();block(m,links,port,calls)}finally {links.clear();links.profile.viewModelScope.cancel();links.viewModelScope.cancel();m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun sharedStrictPayloadStatusAndUnknownFlagsFollowExistingDetailRoutes()=runTest {
        val rows=catalog().getJSONArray("cases")
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val k=kind(row);val parsed=AppointmentReferenceDetail.decode(row.getString("response_json"),k);val id=row.getLong("id");if(id>Int.MAX_VALUE){assertNull(parsed);continue};val calls=mutableListOf<ReadRequest>();val repo=APIAppointmentReferenceRepository(ReadTransport {q->calls+=q;ReadResponse(row.getInt("status"),row.getString("response_json"))});var value:AppointmentReferenceDetail?=null;var problem:ReadProblem?=null
            try {value=repo.reference(k,row.getInt("business"),id.toInt())}catch(e:ReadException){problem=e.problem};assertEquals(row.getString("name"),row.getBoolean("valid"),value!=null);assertEquals(listOf(ReadRequest(k.path(id.toInt())!!)),calls)
            if(value!=null){assertEquals(row.getJSONObject("response").getString("name"),value.name);assertEquals(if(row.isNull("active"))null else row.getBoolean("active"),value.isActive);assertEquals(row.getString("type_key"),value.resourceTypeCopyKey)}else assertEquals(when(row.getInt("status")){403->ReadProblem.DENIED;404->ReadProblem.NOT_FOUND;200->ReadProblem.INVALID_PAYLOAD;else->ReadProblem.UNAVAILABLE},problem)}
    }
    @Test fun invalidContextCannotIssueBusinessCatalogueOrZeroReferenceGet()=runTest {
        val calls=mutableListOf<ReadRequest>();val repo=APIAppointmentReferenceRepository(ReadTransport {q->calls+=q;ReadResponse(200,"")})
        for((b,id) in listOf(0 to 8001,101 to 0,101 to -1)){try {repo.reference(AppointmentReferenceKind.SERVICE,b,id);fail("Invalid context accepted")}catch(e:ReadException){assertEquals(ReadProblem.INVALID_CONTEXT,e.problem)}};assertTrue(calls.isEmpty())
    }
    @Test fun parentNullNegativeAndZeroReferencesNeverDefaultFromLabel() {
        val rows=catalog().getJSONArray("parent_cases")
        for(i in 0 until rows.length()){val row=rows.getJSONObject(i);val base=JSONObject(fixture("appointment-101-501"));val fields=base.getJSONObject("details");for(key in listOf("service","resource"))fields.getJSONObject(key).put("id",row.get(key));val parent=JsonContracts.detail(base.toString());assertEquals(row.getBoolean("service_valid"),parent.referenceID(AppointmentReferenceKind.SERVICE)!=null);assertEquals(row.getBoolean("resource_valid"),parent.referenceID(AppointmentReferenceKind.RESOURCE)!=null)}
    }
    @Test fun pendingReadCannotRepeatOrBeDisplacedByOldEntryClientOrBack()=check {_,l,p,_->
        val entry=l.presentation!!;l.openReference(AppointmentReferenceKind.SERVICE,entry);runCurrent();val pending=l.presentation!!;l.openReference(AppointmentReferenceKind.RESOURCE,entry);l.openClient(presentation=pending);l.retry(pending);l.back(entry);runCurrent();assertEquals(1,p.calls.size);assertTrue(l.state.loading);assertEquals(AppointmentRelatedTarget.Service(8001),l.state.selected);p.pending[0].complete(detail(AppointmentReferenceKind.SERVICE));runCurrent()
    }
    @Test fun deniedRetryGetsFreshVisitAndOldErrorBackCannotChangeParent()=check {m,l,p,reads->
        val parent=m.control;val body=m.state.detail;val before=reads.size;l.openReference(AppointmentReferenceKind.SERVICE,l.presentation);runCurrent();val old=l.presentation!!;p.pending[0].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();assertNull(l.state.reference);assertEquals(ReadProblem.DENIED,l.state.problem);l.retry(l.presentation);runCurrent();val current=l.presentation;l.back(old);l.retry(old);runCurrent();assertEquals(2,p.calls.size);p.pending[1].complete(detail(AppointmentReferenceKind.SERVICE));runCurrent();assertEquals(current,l.presentation);assertEquals(body,m.state.detail);assertEquals(parent,m.control);assertEquals(before,reads.size)
    }
    @Test fun lateServiceFailureCannotOverwriteReopenedResourceOrItsStatus()=check {_,l,p,_->
        l.openReference(AppointmentReferenceKind.SERVICE,l.presentation);runCurrent();val old=l.presentation;l.back(old);l.openReference(AppointmentReferenceKind.RESOURCE,l.presentation);runCurrent();val fresh=l.presentation;l.back(old);l.retry(old);runCurrent();p.pending[1].complete(detail(AppointmentReferenceKind.RESOURCE));runCurrent();p.pending[0].completeExceptionally(ReadException(ReadProblem.UNAVAILABLE));runCurrent();assertEquals(fresh,l.presentation);assertEquals(9001,l.state.reference!!.id);assertNull(l.state.problem);assertEquals(2,p.calls.size)
    }
    @Test fun parentRefreshInvalidatesLateReadAndEveryOldCapturedCallback()=check {m,l,p,_->
        l.openReference(AppointmentReferenceKind.SERVICE,l.presentation);runCurrent();val old=l.presentation;m.retryDetail(m.control);runCurrent();val current=l.presentation;p.pending[0].complete(detail(AppointmentReferenceKind.SERVICE));runCurrent();l.openReference(AppointmentReferenceKind.SERVICE,old);l.back(old);l.retry(old);runCurrent();assertEquals(current,l.presentation);assertNull(l.state.selected);assertNull(l.state.reference);assertEquals(1,p.calls.size)
    }
    @Test fun cancellationClearsOnlyCurrentReferenceWithoutAnErrorOrAutomaticRetry()=check {_,l,p,_->
        l.openReference(AppointmentReferenceKind.SERVICE,l.presentation);runCurrent();val old=l.presentation;p.pending[0].completeExceptionally(CancellationException("Synthetic cancellation"));runCurrent();l.retry(old);runCurrent();assertNull(l.state.selected);assertFalse(l.state.loading);assertNull(l.state.problem);assertEquals(1,p.calls.size)
    }
    @Test fun newBusinessCannotReceivePriorOwnerReferenceOrStartFromOldEntry()=check {m,l,p,_->
        val entry=l.presentation;l.openReference(AppointmentReferenceKind.SERVICE,entry);runCurrent();val old=l.presentation;m.load(202,"2026-10-28");runCurrent();m.openDetail(601,m.control);runCurrent();val current=l.presentation;p.pending[0].complete(detail(AppointmentReferenceKind.SERVICE));runCurrent();l.openReference(AppointmentReferenceKind.SERVICE,entry);l.back(old);l.retry(old);runCurrent();assertEquals(current,l.presentation);assertNull(l.state.reference);assertEquals(202,l.state.parent!!.business);assertEquals(1,p.calls.size)
    }
    @Test fun unchangedLegacySharedIdFailsBusinessScopeInsteadOfInventingAQuery()=runTest {
        val calls=mutableListOf<ReadRequest>();val repo=APIAppointmentReferenceRepository(ReadTransport {q->calls+=q;ReadResponse(200,fixture("service-reference-8001"))});try {repo.reference(AppointmentReferenceKind.SERVICE,202,8001);fail("Shared id changed Business")}catch(e:ReadException){assertEquals(ReadProblem.INVALID_PAYLOAD,e.problem)};assertEquals(listOf(ReadRequest("/api/services/8001/")),calls)
    }
    @Test fun inactive202DetailIsReadableWithoutBecomingSlotOrPermissionEvidence()=runTest {
        val parent=JsonContracts.detail(catalog().getString("parent_202_variant_json"));assertEquals(8002,parent.referenceID(AppointmentReferenceKind.SERVICE));val repo=APIAppointmentReferenceRepository(ReadTransport {ReadResponse(200,fixture("service-reference-8002"))});val result=repo.reference(AppointmentReferenceKind.SERVICE,202,8002);assertEquals(false,result.isActive);assertEquals("referenceInactive",result.activityCopyKey);assertNull(result.resourceType)
    }
    @Test fun missingReadPortDoesNotInferAuthorityFromAppointmentReference()=runTest {
        val base=object:AppointmentRelatedRepository {override suspend fun clientProfile(business:Int,id:Int)=JsonContracts.clientProfile(fixture("client-101-7001"));override suspend fun taskDetails(business:Int,id:Int)=JsonContracts.taskDetails(fixture("task-101-1301"))};val links=AppointmentRelationsViewModel(base)
        try {assertFalse(links.referenceAvailable(AppointmentReferenceKind.SERVICE));links.openReference(AppointmentReferenceKind.SERVICE,null);runCurrent();assertNull(links.state.selected)}finally {links.profile.viewModelScope.cancel();links.viewModelScope.cancel()}
    }
}
