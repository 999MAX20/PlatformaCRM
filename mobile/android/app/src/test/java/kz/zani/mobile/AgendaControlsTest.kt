package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.AgendaViewModel
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class AgendaControlsTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun page(b:Int=101)=JsonContracts.appointments(fixture("appointments-$b"))
    private fun detail()=JsonContracts.detail(fixture("appointment-101-501"))
    private inner class Controlled:AgendaRepository {
        val pages=mutableListOf<CompletableDeferred<AppointmentList>>();val details=mutableListOf<CompletableDeferred<AppointmentDetail>>()
        override suspend fun bootstrap()=JsonContracts.bootstrap(fixture("bootstrap"))
        override suspend fun appointments(business:Int,day:String)=CompletableDeferred<AppointmentList>().also {pages+=it}.await()
        override suspend fun appointment(business:Int,id:Int)=CompletableDeferred<AppointmentDetail>().also {details+=it}.await()
    }
    private fun check(block:suspend TestScope.(AgendaViewModel,Controlled)->Unit)=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val r=Controlled();val m=AgendaViewModel(r,initialDay={"2026-10-28"})
        try {block(m,r)} finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun pendingAndModeRoundTripRejectOldListRowWithoutChangingSource()=check {m,r->
        val bootstrap=m.control;assertFalse(m.matches(null));m.start();runCurrent();m.retryList(m.control);m.openDetail(501,m.control);runCurrent();assertEquals(1,r.pages.size);assertTrue(r.details.isEmpty());r.pages[0].complete(page());runCurrent();val list=m.control;val rows=m.state.items
        m.retryList(bootstrap);m.setMode(AgendaMode.CALENDAR,AgendaMode.LIST,list);val calendar=m.control;m.setMode(AgendaMode.LIST,AgendaMode.CALENDAR,list);assertEquals(AgendaMode.CALENDAR,m.state.mode)
        m.setMode(AgendaMode.LIST,AgendaMode.CALENDAR,calendar);m.openDetail(501,list);runCurrent();assertEquals(1,r.pages.size);assertTrue(r.details.isEmpty());assertEquals(rows,m.state.items);assertEquals(list.selection,m.state.selection)
    }
    @Test fun sameIdReopenRejectsOldBackRetryAndLateWithheldFieldsRestore()=check {m,r->
        m.start();runCurrent();r.pages[0].complete(page());runCurrent();val list=m.control;m.openDetail(501,list);runCurrent();val first=m.control;m.retryDetail(first);m.retryList(list);m.openDetail(501,list);runCurrent();assertEquals(1,r.details.size)
        m.back(first);m.openDetail(501,m.control);runCurrent();val second=m.control;m.back(second);m.openDetail(501,m.control);runCurrent();val current=m.control;m.back(second);m.retryDetail(second);runCurrent();assertEquals(3,r.details.size);assertEquals(current,m.control)
        val j=JSONObject(fixture("appointment-101-501"));j.getJSONObject("appointment").put("title",JSONObject.NULL).put("start_at",JSONObject.NULL).put("end_at",JSONObject.NULL);r.details[2].complete(JsonContracts.detail(j.toString()));runCurrent();r.details[1].complete(detail());r.details[0].complete(detail());runCurrent()
        assertNull(m.state.detail!!.appointment.title);assertNull(m.state.items.first().startAt);assertEquals(current,m.control);assertNull(m.state.detailProblem)
    }
    @Test fun oldDayBusinessAndLateListCannotOverwriteCurrentReadScope()=check {m,r->
        m.start();runCurrent();r.pages[0].complete(page());runCurrent();val list=m.control;val epoch=m.state.businessEpoch;m.changeDay("2026-10-29","2026-10-28",list);runCurrent();m.changeDay("2026-10-30","2026-10-29",list);m.retryList(m.control);runCurrent();assertEquals(2,r.pages.size)
        r.pages[1].complete(page());runCurrent();assertEquals("2026-10-29",m.state.selection!!.day);assertEquals(epoch,m.state.businessEpoch);assertEquals("2026-10-28",m.state.responseDay);assertFalse(m.state.showsEmptyResult);assertEquals(page().items,m.state.items)
        val old=m.control;m.switchBusiness(202,old);runCurrent();m.switchBusiness(101,old);runCurrent();assertEquals(3,r.pages.size);m.switchBusiness(101,m.control);runCurrent();r.pages[3].complete(page());runCurrent();r.pages[2].complete(page(202));runCurrent();m.retryList(old);m.openDetail(501,old);m.setMode(AgendaMode.CALENDAR,AgendaMode.LIST,old);runCurrent()
        assertEquals(4,r.pages.size);assertTrue(r.details.isEmpty());assertEquals(101,m.state.selection!!.business.id);assertTrue(m.state.businessEpoch>epoch);assertEquals(AgendaMode.LIST,m.state.mode)
    }
    @Test fun rawUncertainRowsStillOpenFreshDetailWithoutInventedTimesOrUnknownBusiness()=check {m,r->
        m.start();runCurrent();val j=JSONObject(fixture("appointments-101"));j.getJSONArray("items").getJSONObject(0).put("start_at",JSONObject.NULL).put("end_at",JSONObject.NULL);val raw=JsonContracts.appointments(j.toString());r.pages[0].complete(raw);runCurrent();val list=m.control;m.switchBusiness(999,list);runCurrent();assertEquals(1,r.pages.size);assertEquals(raw.items,m.state.items)
        m.openDetail(501,list);runCurrent();val response=JSONObject(fixture("appointment-101-501"));response.getJSONObject("appointment").put("start_at",JSONObject.NULL).put("end_at",JSONObject.NULL);r.details[0].complete(JsonContracts.detail(response.toString()));runCurrent();assertNotNull(m.state.detail);assertNull(m.state.detail!!.appointment.startAt);assertNull(m.state.detail!!.appointment.endAt);assertNull(m.state.detailProblem);assertEquals(list.selection,m.state.selection)
    }
}
