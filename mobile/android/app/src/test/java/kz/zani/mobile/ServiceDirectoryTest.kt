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
class ServiceDirectoryTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private val catalog get()=JSONObject(fixture("service-directory"))
    private fun reader(calls:MutableList<ReadRequest> = mutableListOf())=APIServiceDirectoryRepository(ReadTransport {q->calls.add(q);val reads=catalog.getJSONArray("reads");val row=(0 until reads.length()).map {reads.getJSONObject(it)}.firstOrNull {it.getString("path")==q.path && q.query.isEmpty()};ReadResponse(if(row==null)404 else 200,row?.getString("response_json") ?: "")})
    private fun scope(business:Int=101):Selection {val s=AgendaSession();s.install(JsonContracts.bootstrap(fixture("bootstrap")));return s.begin(business,"2026-10-28")}
    private class Held:ServiceDirectoryRepository {
        val calls=mutableListOf<String>();val windows=mutableMapOf<Int,CompletableDeferred<ServiceDirectoryWindow>>();val details=mutableMapOf<Int,CompletableDeferred<ServiceDirectoryItem>>()
        override suspend fun services(business:Int):ServiceDirectoryWindow {val i=calls.size;calls.add("list:$business");return CompletableDeferred<ServiceDirectoryWindow>().also {windows[i]=it}.await()}
        override suspend fun service(business:Int,id:Int):ServiceDirectoryItem {val i=calls.size;calls.add("detail:$business/$id");return CompletableDeferred<ServiceDirectoryItem>().also {details[i]=it}.await()}
    }
    @Test fun sharedStrictWindowsProjectionMetadataAndExactReadRequests()=runTest {
        val cases=catalog.getJSONArray("cases")
        for(i in 0 until cases.length()) {val c=cases.getJSONObject(i);val w=ServiceDirectoryWindow.decode(c.getString("response_json"),c.getInt("business"));assertEquals(c.getString("name"),c.getBoolean("valid"),w!=null);if(w!=null) {val ids=c.getJSONArray("ids");assertEquals((0 until ids.length()).map {ids.getInt(it)},w.items.map {it.id});assertTrue(w.items.all {it.business==w.business})}}
        val calls=mutableListOf<ReadRequest>();val r=reader(calls);val a=r.services(101);val b=r.services(202);val detail=r.service(101,8001);val zero=r.service(101,8003)
        assertEquals(3,a.receivedCount);assertEquals(999L,a.observedCount);assertEquals(ServiceDirectoryLinkPresence.PRESENT,a.next);assertEquals(ServiceDirectoryLinkPresence.NULL,a.previous);assertEquals(listOf(8002),b.items.map {it.id});assertNotEquals(a.items.first(),detail);assertEquals(0,zero.durationMinutes);assertFalse(zero.isActive);assertNull(zero.priceFrom)
        try {r.service(101,8002);fail("Foreign Service")}catch(e:ReadException){assertEquals(ReadProblem.INVALID_PAYLOAD,e.problem)}
        try {r.services(0);fail("Invalid Business")}catch(e:ReadException){assertEquals(ReadProblem.INVALID_CONTEXT,e.problem)}
        assertEquals(listOf(ReadRequest("/api/services/"),ReadRequest("/api/services/"),ReadRequest("/api/services/8001/"),ReadRequest("/api/services/8003/"),ReadRequest("/api/services/8002/")),calls)
        assertNotEquals(zero,zero.copy(name="Cafe\u0301"));assertNotEquals(zero,zero.copy(createdAt="2026-10-01T04:00:00+00:00"))
        for((status,problem) in listOf(403 to ReadProblem.DENIED,404 to ReadProblem.NOT_FOUND,500 to ReadProblem.UNAVAILABLE)) {var count=0;val port=APIServiceDirectoryRepository(ReadTransport {++count;ReadResponse(status,"")});try {port.services(101);fail("Read status converted to empty")}catch(e:ReadException){assertEquals(problem,e.problem)};assertEquals(1,count)}
    }
    @Test fun actualModelLateListDetailBackRereadAndBusinessOwnership()=runTest {
        val repo=reader();val a=repo.services(101);val b=repo.services(202);val changed=repo.service(101,8001);val held=Held();val m=ServiceDirectoryModel(held);val owner=ServiceDirectoryOwner(scope(),1);m.bind(owner);assertTrue(m.open(m.control));assertTrue(held.calls.isEmpty());assertNull(m.selected)
        val oldNav=m.presentation;val first=launch {m.reload(m.control)};runCurrent();assertTrue(m.loading);assertEquals(oldNav,m.presentation);assertTrue(m.close(oldNav));m.open(m.control);val nav=m.presentation;val second=launch {m.reload(m.control)};runCurrent();held.windows[0]!!.complete(a);first.join();assertTrue(m.loading);assertNull(m.window);assertFalse(m.close(oldNav));held.windows[1]!!.completeExceptionally(ReadException(ReadProblem.DENIED));second.join();assertEquals(ReadProblem.DENIED,m.problem);assertNull(m.window);assertEquals(2,held.calls.size)
        val retry=launch {m.reload(m.control)};runCurrent();held.windows[2]!!.complete(a);retry.join();val row=a.items.first();val rowControl=m.control;val read=launch {m.select(row,rowControl)};runCurrent();assertNull(m.detail);m.backToWindow(m.control);held.details[3]!!.complete(changed);read.join();assertNull(m.detail);assertNull(m.selected);assertEquals(a,m.window);m.select(row,rowControl);assertEquals(4,held.calls.size)
        val fresh=launch {m.select(row,m.control)};runCurrent();held.details[4]!!.complete(changed);fresh.join();assertNotEquals(m.selected,m.detail);assertNull(m.choice);val choose=m.control;m.choose(choose);assertEquals(changed,m.choice!!.item);assertEquals(row,m.choice!!.listed);val chosen=m.choice;m.choose(choose);assertEquals(chosen,m.choice);m.backToWindow(m.control);assertNull(m.choice)
        val before=m.control;val reread=launch {m.reload(m.control)};runCurrent();held.windows[5]!!.complete(a);reread.join();m.select(row,before);m.select(changed,m.control);assertEquals(6,held.calls.size);assertNull(m.selected)
        val late=launch {m.select(row,m.control)};runCurrent();val oldControl=m.control;m.bind(ServiceDirectoryOwner(scope(202),2));held.details[6]!!.complete(changed);late.join();assertNull(m.detail);assertNull(m.choice);assertFalse(m.presented);m.choose(oldControl);assertFalse(m.close(nav));m.open(m.control)
        val next=launch {m.reload(m.control)};runCurrent();held.windows[7]!!.complete(b);next.join();val foreign=launch {m.select(b.items.first(),m.control)};runCurrent();held.details[8]!!.complete(changed);foreign.join();assertEquals(ReadProblem.INVALID_PAYLOAD,m.problem);assertNull(m.detail);assertNull(m.choice);m.close(m.presentation);assertNull(m.window)
    }
    @Test fun parentCalendarFailureDoesNotParkIndependentServiceReadOrInventCreate()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val base=APIReadRepository(ReadTransport {q->ReadResponse(200,fixture(if(q.path.endsWith("/bootstrap/"))"bootstrap" else "appointment-${q.query["business"]}-${q.path.trimEnd('/').substringAfterLast('/')}"))})
        val failing=object:AgendaRepository {override suspend fun bootstrap()=base.bootstrap();override suspend fun appointments(business:Int,day:String):AppointmentList=throw ReadException(ReadProblem.DENIED);override suspend fun appointment(business:Int,id:Int)=base.appointment(business,id)}
        val repo=reader();val parent=AgendaViewModel(failing,initialDay={"2026-10-28"},serviceRepository=repo)
        try {
            parent.start();runCurrent();assertEquals(ReadProblem.DENIED,parent.state.problem);assertNotNull(parent.serviceEntry);val m=parent.services!!;parent.openServices(parent.serviceEntry,m.control);runCurrent();assertTrue(m.presented);assertEquals(listOf(8001,8003),m.window!!.items.map {it.id});assertNull(parent.booking);assertNull(parent.lifecycle);assertEquals(ReadProblem.DENIED,parent.state.problem)
            val nav=m.presentation;m.select(m.window!!.items[1],m.control);m.choose(m.control);assertEquals(0,m.choice!!.item.durationMinutes);assertFalse(m.choice!!.item.isActive);assertEquals(nav,m.presentation);parent.closeServices(nav)
            val old=parent.control;val child=m.control;parent.load(202,"2026-10-28");runCurrent();parent.openServices(old,child);runCurrent();assertFalse(m.presented);assertNull(m.choice);parent.openServices(parent.serviceEntry,m.control);runCurrent();parent.closeServices(nav);assertTrue(m.presented);assertEquals(listOf(8002),m.window!!.items.map {it.id});parent.closeServices(m.presentation)
            parent.load(101,"2026-10-29");runCurrent();assertEquals("2026-10-29",m.owner!!.scope.day);assertNull(m.window);assertNull(m.choice);assertFalse(m.presented)
        } finally {parent.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
