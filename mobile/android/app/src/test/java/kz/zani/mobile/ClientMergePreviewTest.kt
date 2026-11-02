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
class ClientMergePreviewTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    @Test fun exactPreviewRequiresAll13CountsAndArchivePolicyWithoutOutcomeOrScopeInference()=runTest {
        val catalog=JSONObject(fixture("client-merge-preview"));val cases=catalog.getJSONArray("decode_cases")
        for(n in 0 until cases.length()) {val row=cases.getJSONObject(n);val value=runCatching {ClientMergePreview.decode(row.getString("response_json"))}.getOrNull();assertEquals(row.getString("name"),row.getBoolean("valid"),value!=null);if(value!=null)assertEquals(13,value.transferred.provided.size)}
        val pairs=catalog.getJSONArray("snapshot_identity_pairs")
        for(n in 0 until pairs.length()) {val row=pairs.getJSONObject(n);assertNotEquals(ClientMergePreview.decode(row.getString("before_json")),ClientMergePreview.decode(row.getString("after_json")))}
        val source=FixtureClientMergePreviewSource.fromFixture(fixture("client-merge-preview"));val context=ClientMergePreviewContext(101,701,5,1)
        assertEquals(listOf(702,703),source.candidates(context)!!.map {it.id});assertNull(source.preview(context,999));assertNull(source.candidates(ClientMergePreviewContext(202,701,5,1)));assertTrue(source.candidates(ClientMergePreviewContext(101,702,5,1))!!.isEmpty());assertEquals(listOf(802),source.candidates(ClientMergePreviewContext(202,801,5,1))!!.map {it.id})
        val original=source.preview(context,702)!!.transferred;val map=original.provided.toMutableMap();val frozen=ClientMergeTransferCounts(map);map["leads"]=999;val exposed=frozen.provided.toMutableMap();exposed["tasks"]=999;assertEquals(original,frozen)
    }
    @Test fun actualProfilePreviewRequiresExplicitChoiceAndRevokesVisitsAcrossEditorWorkReadAndBusiness()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val requests=mutableListOf<ReadRequest>();val repo=APIReadRepository(ReadTransport {r->requests+=r;ReadResponse(200,fixture("${if(r.path.contains("/appointments/"))"appointment" else "client"}-${r.query["business"]}-${r.path.split('/').filter {it.isNotEmpty()}.last()}"))})
        val source=FixtureClientMergePreviewSource.fromFixture(fixture("client-merge-preview"));val origin=object:ClientEditOriginProvider {override suspend fun origin(profile:ClientProfile)=FixtureClientEditOriginProvider.verified(profile,JsonContracts.clientProfile(fixture("client-${profile.business}-${profile.client.id}")))};val owner=ClientProfileViewModel(repo,this,editOriginSource=origin,mergeSource=source)
        try {
            assertNull(owner.mergeEntry);owner.loadScoped(101,701,5);runCurrent();val read=owner.readSelection;val entry=owner.mergeEntry!!;owner.openMerge(entry);val child=owner.merge!!;val catalogControl=child.control!!
            assertEquals(listOf(702,703),child.candidates.map {it.id});assertNull(child.selected);assertNull(child.result);owner.previewMerge(catalogControl);assertNull(child.result)
            owner.chooseMerge(999,catalogControl);assertNull(child.selected);owner.chooseMerge(702,catalogControl);val selected=child.control!!;owner.previewMerge(selected);assertEquals(702,child.result!!.duplicate.id);assertEquals(13,child.result!!.transferred.provided.size);assertFalse(child.result!!.willDeleteDuplicate)
            val ready=child.control;owner.chooseMerge(703,selected);assertEquals(ready,child.control);assertEquals(1,requests.size);assertEquals("/api/mobile/v1/clients/701/",requests.single().path);assertEquals(mapOf("business" to "101"),requests.single().query)
            assertTrue(owner.closeMerge(ready));assertEquals(read,owner.readSelection);assertEquals(701,owner.state.detail!!.client.id);owner.openMerge(entry);assertNull(child.context)
            owner.openMerge(owner.mergeEntry);val reopened=child.control;assertFalse(owner.closeMerge(ready));assertEquals(reopened,child.control);owner.closeMerge(reopened)
            val beforeEdit=owner.mergeEntry!!;val editModel=owner.edit!!;editModel.open(ClientEditContext(101,701,5));val editSelection=editModel.state.selection!!;owner.openMerge(beforeEdit);assertNull(child.context);editModel.close(editSelection);owner.openMerge(beforeEdit);assertNull(child.context);assertNotEquals(beforeEdit,owner.mergeEntry)
            val beforeWork=owner.mergeEntry!!;owner.work!!.open(ClientWorkTarget.Appointment(5101),presentation=owner.work!!.presentation);runCurrent();owner.openMerge(beforeWork);assertNull(child.context);owner.work!!.back();owner.openMerge(beforeWork);assertNull(child.context);assertNotEquals(beforeWork,owner.mergeEntry)
            val c=ClientMergePreviewContext(101,701,5,1);val rows=source.candidates(c)!!;val pending=mutableListOf<CompletableDeferred<ClientMergePreview?>>()
            val held=object:SyntheticClientMergePreviewSource {
                override suspend fun candidates(context:ClientMergePreviewContext)=rows
                override suspend fun preview(context:ClientMergePreviewContext,duplicate:Int)=CompletableDeferred<ClientMergePreview?>().also {pending+=it}.await()
            }
            val late=ClientProfileViewModel(repo,this,mergeSource=held);late.loadScoped(101,701,7);runCurrent();late.openMerge(late.mergeEntry);val model=late.merge!!;late.chooseMerge(702,model.control);val old=model.control!!
            val first=launch {late.previewMerge(old)};runCurrent();late.chooseMerge(703,model.control);val next=model.control;pending[0].complete(source.preview(c,702));runCurrent();first.join();assertEquals(next,model.control);assertNull(model.result);assertEquals(703,model.selected);assertFalse(model.loading)
            val second=launch {late.previewMerge(model.control)};runCurrent();pending[1].complete(source.preview(c,703));runCurrent();second.join();assertEquals(703,model.result!!.duplicate.id)
            late.chooseMerge(702,model.control);late.previewMerge(old);assertEquals(2,pending.size);assertNull(model.result)
            val last=launch {late.previewMerge(model.control)};runCurrent();late.loadScoped(202,801,8);runCurrent();pending[2].complete(source.preview(c,702));runCurrent();last.join();assertNull(model.context);assertNull(model.result);assertEquals(801,late.state.detail!!.client.id)
            late.loadScoped(101,702,9);runCurrent();late.openMerge(late.mergeEntry);assertEquals(ReadProblem.INVALID_PAYLOAD,model.problem);assertFalse(model.catalogReady);assertNull(model.result)
            val empty=ClientProfileViewModel(repo,this,mergeSource=source);empty.loadScoped(101,702,9);runCurrent();empty.openMerge(empty.mergeEntry);assertTrue(empty.merge!!.catalogReady);assertTrue(empty.merge!!.candidates.isEmpty());assertNull(empty.merge!!.result)
            val plain=ClientProfileViewModel(repo,this);plain.loadScoped(101,701,5);runCurrent();assertNull(plain.merge);assertNull(plain.mergeEntry)
        } finally {owner.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
