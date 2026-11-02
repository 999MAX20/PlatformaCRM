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
class ResourceDirectoryTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private val catalog get()=JSONObject(fixture("resource-directory"))
    private fun reader(calls:MutableList<ReadRequest> = mutableListOf())=APIResourceDirectoryRepository(ReadTransport {q->calls.add(q);val reads=catalog.getJSONArray("reads");val row=(0 until reads.length()).map {reads.getJSONObject(it)}.firstOrNull {it.getString("path")==q.path && q.query.isEmpty()};ReadResponse(if(row==null)404 else 200,row?.getString("response_json") ?: "")})
    private fun serviceReader()=APIServiceDirectoryRepository(ReadTransport {q->val rows=JSONObject(fixture("service-directory")).getJSONArray("reads");val row=(0 until rows.length()).map {rows.getJSONObject(it)}.first {it.getString("path")==q.path && q.query.isEmpty()};ReadResponse(200,row.getString("response_json"))})
    private fun scope(business:Int=101):Selection {val s=AgendaSession();s.install(JsonContracts.bootstrap(fixture("bootstrap")));return s.begin(business,"2026-10-28")}
    private class Held:ResourceDirectoryRepository {
        val calls=mutableListOf<String>();val windows=mutableMapOf<Int,CompletableDeferred<ResourceDirectoryWindow>>();val details=mutableMapOf<Int,CompletableDeferred<ResourceDirectoryItem>>()
        override suspend fun resources(business:Int):ResourceDirectoryWindow {val i=calls.size;calls.add("list:$business");return CompletableDeferred<ResourceDirectoryWindow>().also {windows[i]=it}.await()}
        override suspend fun resource(business:Int,id:Int):ResourceDirectoryItem {val i=calls.size;calls.add("detail:$business/$id");return CompletableDeferred<ResourceDirectoryItem>().also {details[i]=it}.await()}
    }
    @Test fun sharedStrictWindowsProjectionMetadataAndExactReadRequests()=runTest {
        val cases=catalog.getJSONArray("cases")
        for(i in 0 until cases.length()) {val c=cases.getJSONObject(i);val w=ResourceDirectoryWindow.decode(c.getString("response_json"),c.getInt("business"));assertEquals(c.getString("name"),c.getBoolean("valid"),w!=null);if(w!=null) {val ids=c.getJSONArray("ids");assertEquals((0 until ids.length()).map {ids.getInt(it)},w.items.map {it.id});assertTrue(w.items.all {it.business==w.business})}}
        val calls=mutableListOf<ReadRequest>();val r=reader(calls);val a=r.resources(101);val b=r.resources(202);val detail=r.resource(101,9001);val zero=r.resource(101,9003)
        assertEquals(3,a.receivedCount);assertEquals(999L,a.observedCount);assertEquals(ResourceDirectoryLinkPresence.PRESENT,a.next);assertEquals(ResourceDirectoryLinkPresence.NULL,a.previous);assertEquals(listOf(9002),b.items.map {it.id});assertNotEquals(a.items.first(),detail);assertEquals("legacy/unknown",zero.resourceType);assertFalse(zero.isActive);assertFalse(zero.hasKnownType);assertEquals("notAvailable",zero.typeCopyKey)
        try {r.resource(101,9002);fail("Foreign Resource")}catch(e:ReadException){assertEquals(ReadProblem.INVALID_PAYLOAD,e.problem)}
        try {r.resources(0);fail("Invalid Business")}catch(e:ReadException){assertEquals(ReadProblem.INVALID_CONTEXT,e.problem)}
        assertEquals(listOf(ReadRequest("/api/resources/"),ReadRequest("/api/resources/"),ReadRequest("/api/resources/9001/"),ReadRequest("/api/resources/9003/"),ReadRequest("/api/resources/9002/")),calls)
        assertNotEquals(zero,zero.copy(name="Cafe\u0301"));assertNotEquals(zero,zero.copy(createdAt="2026-10-01T04:00:00+00:00"))
        for((status,problem) in listOf(403 to ReadProblem.DENIED,404 to ReadProblem.NOT_FOUND,500 to ReadProblem.UNAVAILABLE)) {var count=0;val port=APIResourceDirectoryRepository(ReadTransport {++count;ReadResponse(status,"")});try {port.resources(101);fail("Read status converted to empty")}catch(e:ReadException){assertEquals(problem,e.problem)};assertEquals(1,count)}
    }
    @Test fun actualModelLateListDetailBackRereadAndBusinessOwnership()=runTest {
        val repo=reader();val a=repo.resources(101);val b=repo.resources(202);val changed=repo.resource(101,9001);val held=Held();val m=ResourceDirectoryModel(held);val owner=ResourceDirectoryOwner(scope(),1);m.bind(owner);assertTrue(m.open(m.control));assertTrue(held.calls.isEmpty());assertNull(m.selected)
        val oldNav=m.presentation;val first=launch {m.reload(m.control)};runCurrent();assertTrue(m.loading);assertEquals(oldNav,m.presentation);assertTrue(m.close(oldNav));m.open(m.control);val nav=m.presentation;val second=launch {m.reload(m.control)};runCurrent();held.windows[0]!!.complete(a);first.join();assertTrue(m.loading);assertNull(m.window);assertFalse(m.close(oldNav));held.windows[1]!!.completeExceptionally(ReadException(ReadProblem.DENIED));second.join();assertEquals(ReadProblem.DENIED,m.problem);assertNull(m.window);assertEquals(2,held.calls.size)
        val retry=launch {m.reload(m.control)};runCurrent();held.windows[2]!!.complete(a);retry.join();val row=a.items.first();val rowControl=m.control;val read=launch {m.select(row,rowControl)};runCurrent();assertNull(m.detail);m.backToWindow(m.control);held.details[3]!!.complete(changed);read.join();assertNull(m.detail);assertNull(m.selected);assertEquals(a,m.window);m.select(row,rowControl);assertEquals(4,held.calls.size)
        val fresh=launch {m.select(row,m.control)};runCurrent();held.details[4]!!.complete(changed);fresh.join();assertNotEquals(m.selected,m.detail);assertNull(m.choice);val choose=m.control;m.choose(choose);assertEquals(changed,m.choice!!.item);assertEquals(row,m.choice!!.listed);val chosen=m.choice;m.choose(choose);assertEquals(chosen,m.choice);m.backToWindow(m.control);assertNull(m.choice)
        val before=m.control;val reread=launch {m.reload(m.control)};runCurrent();held.windows[5]!!.complete(a);reread.join();m.select(row,before);m.select(changed,m.control);assertEquals(6,held.calls.size);assertNull(m.selected)
        val late=launch {m.select(row,m.control)};runCurrent();val oldControl=m.control;m.bind(ResourceDirectoryOwner(scope(202),2));held.details[6]!!.complete(changed);late.join();assertNull(m.detail);assertNull(m.choice);assertFalse(m.presented);m.choose(oldControl);assertFalse(m.close(nav));m.open(m.control)
        val next=launch {m.reload(m.control)};runCurrent();held.windows[7]!!.complete(b);next.join();val foreign=launch {m.select(b.items.first(),m.control)};runCurrent();held.details[8]!!.complete(changed);foreign.join();assertEquals(ReadProblem.INVALID_PAYLOAD,m.problem);assertNull(m.detail);assertNull(m.choice);m.close(m.presentation);assertNull(m.window)
    }
    @Test fun parentCalendarFailureDoesNotParkIndependentResourceReadOrInventCreate()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val base=APIReadRepository(ReadTransport {q->ReadResponse(200,fixture(if(q.path.endsWith("/bootstrap/"))"bootstrap" else "appointment-${q.query["business"]}-${q.path.trimEnd('/').substringAfterLast('/')}"))})
        val failing=object:AgendaRepository {override suspend fun bootstrap()=base.bootstrap();override suspend fun appointments(business:Int,day:String):AppointmentList=throw ReadException(ReadProblem.DENIED);override suspend fun appointment(business:Int,id:Int)=base.appointment(business,id)}
        val repo=reader();val parent=AgendaViewModel(failing,initialDay={"2026-10-28"},resourceRepository=repo,serviceRepository=serviceReader())
        try {
            parent.start();runCurrent();assertEquals(ReadProblem.DENIED,parent.state.problem);assertNotNull(parent.resourceEntry);val m=parent.resources!!;parent.openResources(parent.resourceEntry,m.control);runCurrent();assertTrue(m.presented);assertEquals(listOf(9001,9003),m.window!!.items.map {it.id});assertNull(parent.booking);assertNull(parent.lifecycle);assertEquals(ReadProblem.DENIED,parent.state.problem)
            val nav=m.presentation;m.select(m.window!!.items[1],m.control);m.choose(m.control);assertEquals("legacy/unknown",m.choice!!.item.resourceType);assertFalse(m.choice!!.item.hasKnownType);assertFalse(m.choice!!.item.isActive);assertEquals(nav,m.presentation);parent.closeResources(nav)
            val old=parent.control;val child=m.control;parent.load(202,"2026-10-28");runCurrent();parent.openResources(old,child);runCurrent();assertFalse(m.presented);assertNull(m.choice);parent.openResources(parent.resourceEntry,m.control);runCurrent();parent.closeResources(nav);assertTrue(m.presented);assertEquals(listOf(9002),m.window!!.items.map {it.id});parent.closeResources(m.presentation)
            parent.load(101,"2026-10-29");runCurrent();assertEquals("2026-10-29",m.owner!!.scope.day);assertNull(m.window);assertNull(m.choice);assertFalse(m.presented)
            val services=parent.services!!;val oldServiceEntry=parent.serviceEntry;val oldServiceChild=services.control
            parent.openResources(parent.resourceEntry,m.control);runCurrent();val firstResourceNav=m.presentation;assertNull(parent.serviceEntry);parent.openServices(oldServiceEntry,oldServiceChild);runCurrent();assertFalse(services.presented);assertTrue(m.presented)
            parent.closeResources(firstResourceNav);val oldResourceEntry=parent.resourceEntry;val oldResourceChild=m.control;parent.openServices(parent.serviceEntry,services.control);runCurrent();val serviceNav=services.presentation;assertTrue(services.presented);assertNull(parent.resourceEntry);parent.openResources(oldResourceEntry,oldResourceChild);runCurrent();assertFalse(m.presented)
            parent.closeServices(serviceNav);parent.openResources(parent.resourceEntry,m.control);runCurrent();parent.closeResources(firstResourceNav);assertTrue(m.presented);assertFalse(services.presented)
            parent.detail(501);runCurrent();assertNull(m.owner);assertNull(services.owner);assertNull(m.window);assertNull(services.window);parent.back();assertNotNull(parent.resourceEntry);assertNotNull(parent.serviceEntry);assertNull(m.window);assertNull(services.window)
        } finally {parent.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
