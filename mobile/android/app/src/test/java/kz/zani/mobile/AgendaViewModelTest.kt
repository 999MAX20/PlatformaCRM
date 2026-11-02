package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.cancel
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kz.zani.mobile.core.*
import kz.zani.mobile.data.AgendaRepository
import kz.zani.mobile.data.JsonContracts
import kz.zani.mobile.ui.AgendaViewModel
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class AgendaViewModelTest {
    private class ControlledRepository : AgendaRepository {
        val pending = mutableListOf<CompletableDeferred<AppointmentDetail>>()
        var listRequests = 0
        val listResults = ArrayDeque<Result<AppointmentList>>()
        fun fixture(name: String): String = javaClass.classLoader!!
            .getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use { it.readText() }
        override suspend fun bootstrap() = JsonContracts.bootstrap(fixture("bootstrap"))
        override suspend fun appointments(business: Int, day: String): AppointmentList {
            listRequests += 1
            if (listResults.isNotEmpty()) return listResults.removeFirst().getOrThrow()
            return JsonContracts.appointments(fixture("appointments-$business"))
        }
        override suspend fun appointment(business: Int, id: Int): AppointmentDetail =
            CompletableDeferred<AppointmentDetail>().also { pending += it }.await()
        fun detail() = JsonContracts.detail(fixture("appointment-101-501"))
    }

    private fun checkModel(block: suspend TestScope.(AgendaViewModel, ControlledRepository) -> Unit) = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val repository = ControlledRepository()
        val model = AgendaViewModel(repository, initialDay = { "2026-10-28" })
        try {
            model.start(); runCurrent()
            assertEquals(listOf(501, 502), model.state.items.map { it.id })
            block(model, repository)
        } finally {
            model.viewModelScope.cancel()
            Dispatchers.resetMain()
        }
    }

    @Test fun olderSameIdSuccessCannotRestoreRedactedDetail() = checkModel { model, repository ->
        model.detail(501); runCurrent()
        model.detail(501); runCurrent()
        val detail = repository.detail()
        repository.pending[1].complete(detail.copy(appointment = detail.appointment.copy(title = null)))
        runCurrent()
        repository.pending[0].complete(detail); runCurrent()
        assertEquals(501, model.state.detail!!.appointment.id)
        assertNull(model.state.detail!!.appointment.title)
        assertNull(model.state.items.first().title)
        assertFalse(model.state.detailLoading)
    }

    @Test fun olderErrorCannotStopNewerRequestAndCurrentFailureRemainsRetryable() = checkModel { model, repository ->
        model.detail(501); runCurrent()
        model.detail(501); runCurrent()
        repository.pending[0].completeExceptionally(ReadException(ReadProblem.UNAVAILABLE)); runCurrent()
        assertTrue(model.state.detailLoading); assertNull(model.state.detailProblem)
        repository.pending[1].completeExceptionally(ReadException(ReadProblem.DENIED)); runCurrent()
        assertFalse(model.state.detailLoading); assertEquals(ReadProblem.DENIED, model.state.detailProblem)
        model.detail(501); runCurrent()
        assertNull(model.state.detailProblem); assertTrue(model.state.detailLoading)
        repository.pending[2].complete(repository.detail()); runCurrent()
        assertEquals(501, model.state.detail!!.appointment.id)
    }

    @Test fun backAndReopenRejectResponsesFromPreviousVisit() = checkModel { model, repository ->
        model.detail(501); runCurrent(); model.back()
        repository.pending[0].completeExceptionally(ReadException(ReadProblem.UNAVAILABLE)); runCurrent()
        assertNull(model.state.detailID); assertNull(model.state.detail); assertNull(model.state.detailProblem)
        model.detail(501); runCurrent(); model.back()
        model.detail(501); runCurrent()
        repository.pending[1].complete(repository.detail()); runCurrent()
        assertTrue(model.state.detailLoading); assertNull(model.state.detail)
        repository.pending[2].complete(repository.detail()); runCurrent()
        assertEquals(501, model.state.detail!!.appointment.id); assertFalse(model.state.detailLoading)
    }

    @Test fun businessChangeRejectsLateDetailAndItsUiState() = checkModel { model, repository ->
        model.detail(501); runCurrent()
        model.load(202, "2026-10-28"); runCurrent()
        repository.pending[0].complete(repository.detail()); runCurrent()
        assertEquals(listOf(601), model.state.items.map { it.id })
        assertNull(model.state.detailID); assertNull(model.state.detail); assertNull(model.state.detailProblem)
        assertFalse(model.state.detailLoading)
    }

    @Test fun backFromRecoverableDetailErrorKeepsListContextWithoutReload() = checkModel { model, repository ->
        val listState = model.state
        model.detail(501); runCurrent()
        repository.pending[0].completeExceptionally(ReadException(ReadProblem.UNAVAILABLE)); runCurrent()
        assertEquals(ReadProblem.UNAVAILABLE, model.state.detailProblem)

        model.back(); runCurrent()

        assertEquals(listState.selection, model.state.selection)
        assertEquals(listState.items, model.state.items)
        assertEquals(listState.partial, model.state.partial)
        assertNull(model.state.detailID); assertNull(model.state.detail)
        assertNull(model.state.detailProblem); assertFalse(model.state.detailLoading)
        assertEquals(1, repository.listRequests)
        assertEquals(1, repository.pending.size)
    }

    @Test fun partialEmptyErrorAndRetryDoNotClaimAConfirmedEmptyDay() = checkModel { model, repository ->
        val original = model.state.selection!!
        repository.listResults.addLast(Result.success(JsonContracts.appointments(repository.fixture("appointments-partial-empty-101"))))
        model.load(original.business.id, original.day); runCurrent()
        assertTrue(model.state.partial); assertTrue(model.state.items.isEmpty())
        assertFalse("Partial zero items is not an empty day", model.state.showsEmptyResult)

        for (problem in listOf(ReadProblem.UNAVAILABLE, ReadProblem.DENIED)) {
            repository.listResults.addLast(Result.failure(ReadException(problem)))
            model.load(original.business.id, original.day)
            assertTrue(model.state.loading); assertFalse(model.state.showsEmptyResult)
            runCurrent()
            assertEquals(problem, model.state.problem); assertFalse(model.state.showsEmptyResult)
            assertEquals(original.business, model.state.selection!!.business)
            assertEquals(original.day, model.state.selection!!.day)
        }
        repository.listResults.addLast(Result.success(JsonContracts.appointments(repository.fixture("appointments-empty-101"))))
        model.load(original.business.id, original.day); runCurrent()
        assertTrue(model.state.showsEmptyResult); assertFalse(model.state.loading)
        assertNull(model.state.problem); assertFalse(model.state.partial)
        assertNull(model.state.detailID); assertNull(model.state.detail)
        assertEquals(original.business, model.state.selection!!.business)
        assertEquals(original.day, model.state.selection!!.day)
        assertFalse(kz.zani.mobile.ui.AgendaUiState().showsEmptyResult)
    }
}
