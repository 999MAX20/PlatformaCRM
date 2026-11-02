package kz.zani.mobile
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import org.json.JSONObject
import org.junit.Test
import org.junit.Assert.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.*

@OptIn(ExperimentalCoroutinesApi::class) class InboxTaskSourceTest {
    private fun fixture(n:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$n.json")!!.bufferedReader().use {it.readText()}
    private fun context(o:JSONObject)=InboxConversationFilesContext(o.getInt("business"),o.getInt("conversation"),o.getInt("epoch"),o.getInt("revision"))
    private fun repository()=APIInboxTaskSourceRepository(FixtureInboxTaskSourceTransport.fromJSON(fixture("inbox-task-source")))
    private fun files()=APIInboxConversationFilesRepository(FixtureInboxConversationFilesTransport.fromJSON(fixture("inbox-conversation-files")))
    @Test fun exactGenericClientLeadSourceEmptyQueryErrorsAndScopedReference()=runTest {
        val d=JSONObject(fixture("inbox-task-source"));val a=context(d.getJSONObject("context"));val b=InboxConversationFilesContext(202,951,801,1);val cases=d.getJSONArray("source_cases")
        for(i in 0 until cases.length()){val x=cases.getJSONObject(i);assertEquals(x.getString("name"),x.getBoolean("valid"),InboxTaskSource.decode(x.getString("response_json"),context(x.getJSONObject("context")))!=null)}
        val calls=mutableListOf<ReadRequest>();val base=FixtureInboxTaskSourceTransport.fromJSON(fixture("inbox-task-source"));val repo=APIInboxTaskSourceRepository(ReadTransport {q->calls+=q;base.get(q)});val source=repo.source(a);val other=repo.source(b);assertEquals(listOf("/api/inbox/conversations/901/","/api/inbox/conversations/951/"),calls.map {it.path});assertTrue(calls.all {it.query.isEmpty()})
        val s=InboxTaskSourceSession();s.bind(a);s.show();val start=s.control;s.use(start);assertNull(s.state.source);assertNull(s.state.choice);val first=s.begin(start)!!;assertFalse(s.accept(other,first));assertEquals(ReadProblem.INVALID_PAYLOAD,s.state.problem);assertNull(s.state.source)
        val ticket=s.begin(s.control)!!;assertTrue(s.accept(source,ticket));assertTrue(s.canUse);assertNull(s.state.choice);val stale=s.control;s.use(s.control);val choice=s.state.choice!!;assertTrue(choice.valid);assertEquals(source,choice.source);assertEquals(ticket.revision,choice.readRevision);assertEquals(a,choice.context);s.clearChoice(stale);assertEquals(choice,s.state.choice);s.clearChoice(s.control);assertNull(s.state.choice);assertEquals(source,s.state.source)
        s.use(s.control);val next=s.begin(s.control)!!;assertNull(s.state.choice);assertNull(s.state.source);s.cancel(next);assertFalse(s.state.loading);assertNull(s.state.problem);assertFalse(s.accept(source,next));val late=s.begin(s.control)!!;s.hide();s.bind(b);s.show();val current=s.control;s.fail(ReadProblem.UNAVAILABLE,late);assertEquals(current,s.control);assertFalse(s.accept(source,late));assertNull(s.state.source);s.bind(a);s.show();assertFalse(s.accept(source,late));assertNull(s.state.choice)
        for((id,problem) in listOf(903 to ReadProblem.DENIED,904 to ReadProblem.NOT_FOUND,905 to ReadProblem.UNAVAILABLE,906 to ReadProblem.INVALID_PAYLOAD)){try{repo.source(a.copy(conversation=id));fail("Invalid read accepted")}catch(e:ReadException){assertEquals(problem,e.problem)}}
        assertFalse(source.copy(client=0).valid);assertFalse(choice.copy(readRevision=0).valid)
    }
    private inner class Reads:InboxRepository {override suspend fun inbox(business:Int)=JsonContracts.inbox(fixture("inbox-$business"));override suspend fun thread(business:Int,id:Int)=JsonContracts.thread(fixture("inbox-$business-$id"))}
    @Test fun actualParentExplicitReadUseClearFreezeAndBusinessSwitch()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val root=InboxViewModel(Reads(),files=files(),taskSourceRead=repository())
        try {root.load(101,800);runCurrent();root.open(901);runCurrent();val original=root.state.thread;val p=root.fileMetadata!!.taskSource!!;root.openFiles(root.filesEntryControl);assertNull(p.state.source);assertNull(p.state.choice);p.read(p.control);val stale=p.control;p.use(p.control);val choice=p.state.choice!!;assertEquals(701,choice.source.client);assertEquals(81,choice.source.lead);assertEquals(original,root.state.thread);p.controlsBlocked={true};p.clearChoice(p.control);p.read(p.control);assertEquals(choice,p.state.choice);p.controlsBlocked={false};p.clearChoice(stale);assertEquals(choice,p.state.choice);p.clearChoice(p.control);assertNotNull(p.state.source);assertNull(p.state.choice);p.use(p.control);root.closeFiles(root.filesPresentationControl);root.openFiles(root.filesEntryControl);assertNull(p.state.source);assertNull(p.state.choice);root.closeFiles(root.filesPresentationControl);root.load(202,801);runCurrent();root.open(951);runCurrent();root.openFiles(root.filesEntryControl);p.read(p.control);p.use(p.control);assertEquals(202,p.state.choice!!.context.business);assertEquals(1701,p.state.source!!.client);assertNull(p.state.source!!.lead)
        }finally{Dispatchers.resetMain()}
        assertNull(InboxConversationFilesModel(files(),ownerScope=this).taskSource)
    }
    @Test fun actualCancellationIgnoredCancelLateSuccessFailureABAAndNullSource()=runTest {
        val a=InboxConversationFilesContext(101,901,802,1);val b=InboxConversationFilesContext(202,951,803,1);val repo=repository();val source=repo.source(a)
        for(mode in 0..2){val pending=CompletableDeferred<InboxTaskSource>();val model=InboxTaskSourceModel(object:InboxTaskSourceRepository {override suspend fun source(c:InboxConversationFilesContext)=withContext(NonCancellable){pending.await()}});model.bind(a);model.show();val job=launch {model.read(model.control)};runCurrent();if(mode==0)job.cancel()else {model.hide();model.bind(b);model.show()};val current=model.control;if(mode==2)pending.completeExceptionally(ReadException(ReadProblem.UNAVAILABLE))else pending.complete(source);job.join();if(mode!=0)assertEquals(current,model.control);assertNull(model.state.source);assertNull(model.state.choice);assertNull(model.state.problem);model.bind(a);model.show();assertNull(model.state.choice)}
        val nulls=InboxTaskSourceModel(repo);nulls.bind(a.copy(conversation=902));nulls.show();nulls.read(nulls.control);nulls.use(nulls.control);assertNotNull(nulls.state.choice);assertNull(nulls.state.source!!.client);assertNull(nulls.state.source!!.lead)
        val denied=InboxTaskSourceModel(repo);denied.bind(a.copy(conversation=903));denied.show();denied.read(denied.control);denied.use(denied.control);assertEquals(ReadProblem.DENIED,denied.state.problem);assertNull(denied.state.choice)
    }
}
