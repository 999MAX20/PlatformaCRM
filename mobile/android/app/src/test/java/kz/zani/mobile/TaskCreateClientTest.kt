package kz.zani.mobile

import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class TaskCreateClientTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun catalog()=JSONObject(fixture("task-create-client-cases"))
    private val context=TaskDraftContext(101,1)
    private fun profile(business:Int=101,id:Int=701)=JsonContracts.clientProfile(fixture("client-$business-$id"))
    private fun choice()=TaskDraftClientChoice.make(profile(),101,701)!!
    private fun repository()=APIReadRepository(ReadTransport {q->val b=q.query["business"]!!.toInt();val data=fixture("client-search-catalogue-$b");if(q.path.endsWith("/clients/"))FixtureClientSearch.list(data,b,q.query["search"] ?: "") else FixtureClientSearch.profile(data,b,q.path.trimEnd('/').substringAfterLast('/').toInt())})
    private class Port(create:Boolean=true):SyntheticTaskCreatePort {
        override val grants=listOf(SyntheticTaskCreateGrant(101,9001,create),SyntheticTaskCreateGrant(202,9002,create));val calls=mutableListOf<TaskCreateAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticTaskCreateOutcome>>()
        override suspend fun execute(attempt:TaskCreateAttempt):SyntheticTaskCreateOutcome {calls+=attempt;return CompletableDeferred<SyntheticTaskCreateOutcome>().also {pending+=it}.await()}
    }
    private class Reads(private val repo:ClientSearchRepository):ClientSearchRepository {
        val calls=mutableListOf<Pair<Int,Int>>();val pending=mutableListOf<CompletableDeferred<ClientProfile>>()
        override suspend fun searchClients(business:Int,search:String)=repo.searchClients(business,search)
        override suspend fun clientProfile(business:Int,id:Int):ClientProfile {calls+=business to id;return CompletableDeferred<ClientProfile>().also {pending+=it}.await()}
    }
    private fun fill(m:TaskDraftModel) {m.bind(context);m.open(context);val s=m.state.selection!!;m.update(TaskDraftField.TITLE,"  Client task\n",s);m.update(TaskDraftField.DESCRIPTION,"  Raw Client notes\n",s);m.chooseDue(TaskDraftDueMode.SET,m.inputControl);m.update(TaskDraftField.DUE_AT,"2026-11-02T09:30:00+05:00",m.inputControl);m.chooseReminder(TaskDraftDueMode.SET,m.inputControl);m.update(TaskDraftField.REMINDER_AT,"2026-11-01T14:00:00Z",m.inputControl)}
    private fun check(block:suspend TestScope.(TaskDraftModel,Port,Reads,APIReadRepository)->Unit)=runTest {
        val repo=repository();val reads=Reads(repo);val port=Port();val m=TaskDraftModel(port,this,reads);fill(m);try {block(m,port,reads,repo)}finally {m.close(expected=m.returnControl);m.bind(null)}
    }
    private fun response(a:TaskCreateAttempt,client:TaskCreateClientRead)=SyntheticTaskCreateOutcome.Response(201,WorkTask(88001,a.review.preview.title,"open",a.review.preview.priority,a.review.preview.dueAt,business=101,description=a.review.preview.description,createdBy=9001,createdAt="2026-10-30T12:00:00Z",updatedAt="2026-10-30T12:00:00Z"),a.review.preview.reminderAt,client)
    private fun TestScope.readToPicker(m:TaskDraftModel):Pair<TaskDraftClientPickerOwner,Int> {m.openClientPicker(m.inputControl);val owner=m.clientPickerOwner!!;val search=m.clients!!;search.submit(search.control);runCurrent();val id=search.state.items.first().id;search.openClient(id,search.control);runCurrent();return owner to id}
    @Test fun sharedIndependentProfileIdentityAndExactTitleCases() {
        val rows=catalog().getJSONArray("choice_cases")
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val p=JsonContracts.clientProfile(row.getString("profile_json"));val selected=TaskDraftClientChoice.make(p,row.getInt("business"),row.getInt("id"));assertEquals(row.getString("name"),row.getBoolean("valid"),selected!=null);if(selected!=null){assertEquals(row.getInt("id"),selected.id);assertEquals(if(row.getJSONObject("profile").getJSONObject("client").isNull("title"))null else row.getJSONObject("profile").getJSONObject("client").getString("title"),selected.title)}}
    }
    @Test fun genericClientReceiptMustMatchSelectedFkAndNotBoundedGetAlias() {
        val rows=catalog().getJSONArray("receipt_cases");val auth=SyntheticTaskCreateGrant(101,9001,true).authorization(context)!!
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val s=TaskDraftSession();s.bind(context);s.open(context);val q=s.state.selection!!;s.update(TaskDraftField.TITLE,"  Client task\n",q);s.update(TaskDraftField.DESCRIPTION,"  Raw Client notes\n",q);if(!row.isNull("selected"))s.chooseClient(choice(),q);s.prepare(q);val ledger=TaskCreateAttemptLedger();val a=ledger.begin(s.state.review!!,auth)!!;val body=JSONObject(a.preparedBody()!!);assertFalse(body.has("client_id"));assertEquals(!row.isNull("selected"),body.has("client"));if(body.has("client"))assertEquals(701,body.getInt("client"));val read=TaskCreateClientRead.decode(row.getString("body_json"));val kind=row.getString("kind");assertEquals(when(kind){"client"->TaskCreateClientRead.Client(row.getInt("id"));"notSet"->TaskCreateClientRead.NotSet;else->TaskCreateClientRead.Unknown},read)
            val v=a.review.preview;val t=WorkTask(88001,v.title,"open",v.priority,null,clientID=999,business=101,description=v.description,createdBy=9001,createdAt="2026-10-30T12:00:00Z",updatedAt="2026-10-30T12:00:00Z");ledger.complete(a,SyntheticTaskCreateOutcome.Response(row.getInt("status"),t,clientRead=read));val accepted=row.getBoolean("accepted");assertEquals(row.getString("name"),accepted,ledger.visible(auth)!!.phase==TaskCreateAttemptPhase.CONFIRMED);assertEquals(if(accepted && !row.isNull("selected"))701 else null,ledger.visible(auth)!!.clientID)
            if(!accepted){assertFalse(ledger.acknowledge(auth));assertTrue(ledger.blocked(context));assertNull(ledger.begin(s.state.review!!,auth));assertEquals(a,ledger.records.single().attempt);assertEquals(a.preparedBody(),ledger.records.single().attempt.preparedBody())}
        }
    }
    @Test fun clearingUnsentClientOmitsFieldAndPreservesRawTextAndDates() {
        val s=TaskDraftSession();s.bind(context);s.open(context);val q=s.state.selection!!;s.update(TaskDraftField.TITLE,"Raw task",q);s.update(TaskDraftField.DESCRIPTION,"Raw details",q);s.chooseDue(TaskDraftDueMode.SET,q);s.update(TaskDraftField.DUE_AT,"2026-11-02T09:30:00+05:00",q);s.chooseClient(choice(),q);val before=s.state.values;s.chooseClient(TaskDraftClientChoice.make(profile(202,801),202,801),q);assertEquals(before,s.state.values);s.chooseClient(null,q);assertEquals(before.copy(client=null),s.state.values);s.prepare(q);val a=TaskCreateAttemptLedger().begin(s.state.review!!,SyntheticTaskCreateGrant(101,9001,true).authorization(context)!!)!!;assertFalse(JSONObject(a.preparedBody()!!).has("client"))
    }
    @Test fun pickerStartsWithoutReadDefaultOrParentInputControl()=check {m,_,_,_->
        val before=m.state.values;val input=m.inputControl;val control=m.control;m.openClientPicker(input);assertNull(m.inputControl);assertNull(m.state.values.client);assertTrue(m.clients!!.state.items.isEmpty());assertFalse(m.clients.state.loading);m.update(TaskDraftField.TITLE,"overwrite",input);m.prepare(control);assertEquals(before,m.state.values);assertEquals(TaskDraftPhase.EDITING,m.state.phase)
    }
    @Test fun listAndPendingProfileCannotBecomeAChosenClient()=check {m,_,reads,_->
        m.openClientPicker(m.inputControl);val owner=m.clientPickerOwner!!;val search=m.clients!!;search.submit(search.control);runCurrent();val list=search.control;m.confirmClient(owner,list);assertNull(m.state.values.client);search.openClient(search.state.items.first().id,list);runCurrent();m.confirmClient(owner,search.control);assertNull(m.state.values.client);reads.pending[0].complete(profile(202,801));runCurrent()
    }
    @Test fun closedPickerRejectsLateReadAndOldConfirmation()=check {m,_,reads,repo->
        val before=m.state.values;val (owner,id)=readToPicker(m);val pending=m.clients!!.control;m.closeClientPicker(owner);val current=m.control;reads.pending[0].complete(repo.clientProfile(101,id));runCurrent();m.confirmClient(owner,pending);assertEquals(before,m.state.values);assertEquals(current,m.control);assertNull(m.clientPickerOwner)
    }
    @Test fun freshIndependentProfileSelectionRetainsAllRawFields()=check {m,_,reads,repo->
        val before=m.state.values;val (owner,id)=readToPicker(m);val old=m.clients!!.control;reads.pending[0].complete(repo.clientProfile(101,id));runCurrent();m.confirmClient(owner,m.clients.control);assertEquals(id,m.state.values.client!!.id);assertEquals(before.title,m.state.values.title);assertEquals(before.description,m.state.values.description);assertEquals(before.dueDate,m.state.values.dueDate);assertEquals(before.reminderDate,m.state.values.reminderDate);assertNull(m.clientPickerOwner);m.confirmClient(owner,old);assertEquals(id,m.state.values.client!!.id)
    }
    @Test fun foreignProfileAndBusinessSwitchCannotChangeDraft()=check {m,_,reads,repo->
        val (owner,_)=readToPicker(m);reads.pending[0].complete(profile(202,801));runCurrent();m.confirmClient(owner,m.clients!!.control);assertNull(m.state.values.client);assertEquals(ReadProblem.INVALID_PAYLOAD,m.clients.profile.state.problem);m.clients.retryProfile(m.clients.control);runCurrent();m.bind(TaskDraftContext(202,2));reads.pending[1].complete(repo.clientProfile(101,1754));runCurrent();m.confirmClient(owner,m.clients.control);assertNull(m.state.values.client);assertNull(m.clientPickerOwner);assertEquals(202,m.state.context!!.business)
    }
    @Test fun pendingCreateCannotReplaceClearOrResubmitSelectedClient()=check {m,p,reads,repo->
        val (owner,id)=readToPicker(m);reads.pending[0].complete(repo.clientProfile(101,id));runCurrent();m.confirmClient(owner,m.clients!!.control);m.prepare(m.control);val review=m.state.review!!;val sending=launch {m.submit(review)};runCurrent();val original=m.state.values;m.openClientPicker(m.inputControl);m.clearClient(m.inputControl);m.submit(review);runCurrent();assertEquals(1,p.calls.size);assertEquals(id,JSONObject(p.calls[0].preparedBody()!!).getInt("client"));assertEquals(original,m.state.values);p.pending[0].complete(response(p.calls[0],TaskCreateClientRead.Client(id)));runCurrent();sending.join();assertEquals(TaskCreateAttemptPhase.CONFIRMED,m.submission!!.phase);assertEquals(id,m.submission!!.clientID)
    }
    @Test fun mismatchedClientReceiptRetainsUnknownAttemptAndBlocksReopenBypass()=check {m,p,reads,repo->
        val (owner,id)=readToPicker(m);reads.pending[0].complete(repo.clientProfile(101,id));runCurrent();m.confirmClient(owner,m.clients!!.control);m.prepare(m.control);val review=m.state.review!!;val sending=launch {m.submit(review)};runCurrent();val attempt=p.calls[0];p.pending[0].complete(response(attempt,TaskCreateClientRead.Client(id+1)));runCurrent();sending.join();assertEquals(TaskCreateAttemptPhase.UNKNOWN,m.submission!!.phase);assertEquals(attempt,m.submission!!.attempt);m.close(m.state.selection!!);m.open(context);m.clearClient(m.inputControl);m.openClientPicker(m.inputControl);m.submit(review);runCurrent();assertEquals(1,p.calls.size);assertEquals(id,m.state.values.client!!.id);assertNull(m.clientPickerOwner);assertTrue(m.submissionBlocked);m.bind(TaskDraftContext(101,2));m.open(TaskDraftContext(101,2));assertTrue(m.submissionBlocked);assertNull(m.submission);assertEquals(1,m.retainedAttemptCount)
    }
    @Test fun clientGetDoesNotProvideSyntheticCreateGrant()=runTest {
        val m=TaskDraftModel(Port(false),this,repository());fill(m);m.openClientPicker(m.inputControl);val owner=m.clientPickerOwner;val search=m.clients!!;search.submit(search.control);runCurrent();val id=search.state.items.first().id;search.openClient(id,search.control);runCurrent();m.confirmClient(owner,search.control);m.prepare(m.control);assertEquals(id,m.state.review!!.preview.clientID);assertFalse(m.canSubmit);assertNull(m.submission);m.close(m.state.selection!!)
    }
    @Test fun stalePickerOwnerAndStaleProfileReadCannotChooseClient()=check {m,_,reads,repo->
        m.openClientPicker(m.inputControl);val old=m.clientPickerOwner;m.closeClientPicker(old);val (fresh,id)=readToPicker(m);val before=m.clients!!.control;reads.pending[0].complete(repo.clientProfile(101,id));runCurrent();m.confirmClient(old,m.clients.control);m.confirmClient(fresh,before);assertNull(m.state.values.client);m.confirmClient(fresh,m.clients.control);assertEquals(id,m.state.values.client!!.id)
    }
    @Test fun removedClientCanBeReviewedAsOmittedWithoutACommand()=check {m,p,reads,repo->
        val (owner,id)=readToPicker(m);reads.pending[0].complete(repo.clientProfile(101,id));runCurrent();m.confirmClient(owner,m.clients!!.control);m.clearClient(m.inputControl);m.prepare(m.control);assertNull(m.state.review!!.preview.clientID);assertNull(m.state.review!!.values.client);assertTrue(p.calls.isEmpty())
    }
    @Test fun missingIndependentReadPortHasNoPickerAction()=runTest {
        val m=TaskDraftModel(Port(),this);fill(m);m.openClientPicker(m.inputControl);assertFalse(m.clientPickerAvailable);assertNull(m.clientPickerOwner);assertNull(m.state.values.client);m.close(m.state.selection!!)
    }
}
