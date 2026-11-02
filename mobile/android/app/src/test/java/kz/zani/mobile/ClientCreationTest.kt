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
class ClientCreationTest {
    private val context=ClientDraftContext(101,1)
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private class ControlledPort(create:Boolean=true):SyntheticClientCreatePort {
        override val grants=listOf(SyntheticClientCreateGrant(101,9001,create),SyntheticClientCreateGrant(202,9002,create))
        val attempts=mutableListOf<ClientCreateAttempt>();val replies=mutableListOf<CompletableDeferred<SyntheticClientCreateOutcome>>()
        override suspend fun execute(attempt:ClientCreateAttempt):SyntheticClientCreateOutcome {attempts+=attempt;val r=CompletableDeferred<SyntheticClientCreateOutcome>();replies+=r;return r.await()}
    }
    private fun editor(port:SyntheticClientCreatePort?):Pair<ClientDraftModel,ClientDraftReview> {val m=ClientDraftModel(port);m.bind(context);m.open(context);val s=m.state.selection!!;m.update(ClientDraftField.FULL_NAME,"  Manual client\n",s);m.update(ClientDraftField.PHONE,"  +7 123\n",s);m.update(ClientDraftField.EMAIL,"alpha@example.invalid",s);m.update(ClientDraftField.NOTES,"  Manual notes\n",s);m.prepare(s);return m to m.state.review!!}
    private fun response(a:ClientCreateAttempt):SyntheticClientCreateOutcome {val v=a.review.preview;return SyntheticClientCreateOutcome.Response(201,ClientContact(87001,null,v.phone,v.email,a.authorization.context.business,v.fullName,v.source,v.notes,"2026-10-30T12:00:00Z","2026-10-30T12:00:00Z"))}
    @Test fun existingSerializerFieldsValidateExactPreviewWithoutInventedActorEcho() {
        val (_,r)=editor(null);val auth=SyntheticClientCreateGrant(101,9001,true).authorization(context)!!;val rows=JSONObject(fixture("client-create-outcome")).getJSONArray("validation_cases")
        for(n in 0 until rows.length()) {val row=rows.getJSONObject(n);val l=ClientCreateAttemptLedger();val a=l.begin(r,auth)!!;val c=runCatching {JsonContracts.clientCreateAction(row.getJSONObject("response").toString())}.getOrNull();l.complete(a,if(c!=null)SyntheticClientCreateOutcome.Response(row.getInt("status"),c) else SyntheticClientCreateOutcome.Unknown)
            assertEquals(row.getString("name"),if(row.getString("expected")=="confirmed")ClientCreateAttemptPhase.CONFIRMED else ClientCreateAttemptPhase.UNKNOWN,l.visible(auth)!!.phase);assertEquals(r.values,l.records[0].attempt.review.values)
            if(row.getString("expected")=="unknown") {assertFalse(l.acknowledge(auth));assertNull(l.begin(r,auth))}
        }
        val bounded=JsonContracts.clientProfile(fixture("client-101-701")).client;assertNull(bounded.business);assertNull(bounded.fullName);assertNull(bounded.notes);assertNull(bounded.createdAt)
        assertNull(ClientCreateAttemptLedger().begin(r.copy(preview=r.preview.copy(fullName="Other")),auth))
    }
    @Test fun defaultReadAndDeniedCreateOrOldInvalidReviewNeverInvokePort()=runTest {
        for(p in listOf(null,ControlledPort(false))) {val (m,r)=editor(p);m.submit(r);assertFalse(m.canSubmit);assertEquals(0,m.retainedAttemptCount)}
        val p=ControlledPort();val (m,r)=editor(p);m.back(r.selection);m.update(ClientDraftField.FULL_NAME,"Changed",r.selection);m.prepare(r.selection);m.submit(r);assertTrue(p.attempts.isEmpty())
        m.back(r.selection);m.update(ClientDraftField.NOTES,"Bad\u0000notes",r.selection);m.prepare(r.selection);m.submit(r);assertTrue(p.attempts.isEmpty())
    }
    @Test fun pendingDoubleClickBackReopenAndSyntheticResultPreserveOnlyOwnRaw()=runTest {
        val p=ControlledPort();val (m,r)=editor(p);val job=launch {m.submit(r)};runCurrent();m.submit(r);m.update(ClientDraftField.NOTES,"overwrite",r.selection);m.discard(r.selection);assertEquals(1,p.attempts.size);assertEquals(r.values,m.state.values)
        m.back(r.selection);m.open(context);val fresh=m.state.selection!!;p.replies[0].complete(response(p.attempts[0]));job.join();assertEquals(ClientCreateAttemptPhase.CONFIRMED,m.submission!!.phase)
        m.acknowledge(r.selection,1);assertNotNull(m.submission);m.acknowledge(fresh,1);assertEquals(ClientDraftValues(),m.state.values);assertNull(m.state.selection);assertEquals(1,m.retainedAttemptCount)
    }
    @Test fun reopenedNoWriteErrorRequiresExplicitReviewAndUnknownCannotClearOrReplay()=runTest {
        val p=ControlledPort();val (m,r)=editor(p);val job=launch {m.submit(r)};runCurrent();p.replies[0].complete(SyntheticClientCreateOutcome.RejectedWithoutWrite);job.join();m.close(r.selection);m.open(context);val fresh=m.state.selection!!;m.acknowledge(fresh,1)
        assertEquals(ClientDraftPhase.EDITING,m.state.phase);assertEquals(fresh,m.state.selection);assertEquals(r.values,m.state.values);m.submit(r);assertEquals(1,p.attempts.size)
        m.prepare(fresh);val nr=m.state.review!!;val sending=launch {m.submit(nr)};runCurrent();p.replies[1].complete(SyntheticClientCreateOutcome.Unknown);sending.join();m.acknowledge(fresh,1);m.acknowledge(fresh,2);m.discard(fresh);m.submit(nr);assertEquals(2,p.attempts.size);assertEquals(ClientCreateAttemptPhase.UNKNOWN,m.submission!!.phase)
    }
    @Test fun lostReplyCancellationAndLateEpochRetainUnknownOrHideOldOutcome()=runTest {
        val p=ControlledPort();val (m,r)=editor(p);val job=launch {m.submit(r)};runCurrent();p.replies[0].completeExceptionally(IllegalStateException("lost"));job.join();assertEquals(ClientCreateAttemptPhase.UNKNOWN,m.submission!!.phase);m.close(r.selection);m.open(context);assertFalse(m.canSubmit);assertEquals(r.values,m.state.values)
        val p2=ControlledPort();val (cancelled,c)=editor(p2);val cancelling=launch {cancelled.submit(c)};runCurrent();cancelling.cancelAndJoin();assertEquals(ClientCreateAttemptPhase.UNKNOWN,cancelled.submission!!.phase)
        val p3=ControlledPort();val (late,l)=editor(p3);val pending=launch {late.submit(l)};runCurrent();late.bind(ClientDraftContext(202,2));p3.replies[0].complete(response(p3.attempts[0]));pending.join();assertNull(late.submission);assertEquals(ClientDraftValues(),late.state.values);assertFalse(late.submissionBlocked);late.bind(context.copy(epoch=3));late.open(context.copy(epoch=3));assertNull(late.submission);assertTrue(late.submissionBlocked)
    }
    @Test fun fullNotesEchoRequiredWithoutInventedReadOrInputCaps() {
        val (_,base)=editor(null);val auth=SyntheticClientCreateGrant(101,9001,true).authorization(context)!!;val values=base.values.copy(notes="N".repeat(2001));val r=base.copy(values=values,preview=values.preview)
        for(cap in listOf(160,1000,2001)) {val l=ClientCreateAttemptLedger();val a=l.begin(r,auth)!!;val v=r.preview;l.complete(a,SyntheticClientCreateOutcome.Response(201,ClientContact(87001,null,v.phone,v.email,101,v.fullName,v.source,v.notes.take(cap),"2026-10-30T12:00:00Z","2026-10-30T12:00:00Z")));assertEquals(if(cap==2001)ClientCreateAttemptPhase.CONFIRMED else ClientCreateAttemptPhase.UNKNOWN,l.visible(auth)!!.phase)}
    }
    @Test fun offTabDirectoryProfileRootOwnerRevokesPendingAndDraftWithoutReads()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val page=CompletableDeferred<ClientList>();var calls=0
        val directory=ClientDirectoryViewModel(object:ClientRepository {override suspend fun clients(business:Int):ClientList {calls++;return page.await()}})
        val detail=CompletableDeferred<ClientProfile>();val profile=ClientProfileViewModel(object:ClientProfileRepository {override suspend fun clientProfile(business:Int,id:Int):ClientProfile {calls++;return detail.await()}},ownerScope=backgroundScope)
        try {
            directory.load(101,1);runCurrent();directory.draft.open(context);val s=directory.draft.state.selection!!;directory.draft.update(ClientDraftField.FULL_NAME,"Private",s)
            profile.loadScoped(101,701,1);runCurrent();val before=calls;directory.reconcileOwner(202,2);profile.reconcileOwner(101,2)
            assertEquals(before,calls);assertNull(directory.state.business);assertTrue(directory.state.items.isEmpty());assertNull(directory.draft.state.context);assertEquals(ClientDraftValues(),directory.draft.state.values)
            page.complete(JsonContracts.clients(fixture("clients-101")));detail.complete(JsonContracts.clientProfile(fixture("client-101-701")));runCurrent();assertNull(directory.state.business);assertNull(profile.state.detail);assertNull(profile.state.business)
        } finally {directory.viewModelScope.cancel();profile.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
