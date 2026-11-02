package kz.zani.mobile.ui

import kz.zani.mobile.core.*

object LoadedSearchSources {
    fun feed(agenda: AgendaUiState, clients: ClientDirectoryState, inbox: InboxState, tasks: TaskListState): LoadedSearchFeed {
        val business = agenda.selection?.business?.id; val epoch = agenda.businessEpoch
        fun source(kind: LoadedSearchKind, sourceBusiness: Int?, sourceEpoch: Int?, generation: Int, loading: Boolean, loaded: Boolean,
                   problem: ReadProblem?, partial: Boolean, rows: List<LoadedSearchRow>, day: String? = null): LoadedSearchSource {
            if (business == null || business != sourceBusiness || sourceEpoch != epoch) return LoadedSearchSource(kind, null, LoadedSearchCoverage.NOT_LOADED)
            val coverage = when { loading -> LoadedSearchCoverage.LOADING; problem == ReadProblem.DENIED -> LoadedSearchCoverage.DENIED
                problem != null -> LoadedSearchCoverage.UNAVAILABLE; !loaded -> LoadedSearchCoverage.NOT_LOADED; partial -> LoadedSearchCoverage.PARTIAL; else -> LoadedSearchCoverage.LOADED }
            return LoadedSearchSource(kind, LoadedSearchToken(kind, business, epoch, generation, day), coverage, rows)
        }
        val day = agenda.selection?.day
        return LoadedSearchFeed.create(business, epoch, listOf(
            source(LoadedSearchKind.APPOINTMENTS, business, epoch, agenda.searchRevision, agenda.loading, day != null && agenda.responseDay == day,
                agenda.problem ?: if (agenda.responseDay != null && agenda.responseDay != day) ReadProblem.INVALID_PAYLOAD else null, agenda.partial, agenda.items.map { LoadedSearchRow(it.id, it.title) }, day),
            source(LoadedSearchKind.CLIENTS, clients.business, clients.scopeEpoch, clients.searchRevision, clients.loading, clients.loaded,
                clients.problem, clients.partial, clients.items.map { LoadedSearchRow(it.id, it.title) }),
            source(LoadedSearchKind.INBOX, inbox.business, inbox.scopeEpoch, inbox.searchRevision, inbox.loading, inbox.loaded,
                inbox.problem, inbox.partial, inbox.items.map { LoadedSearchRow(it.id, it.title) }),
            source(LoadedSearchKind.TASKS, tasks.business, tasks.scopeEpoch, tasks.searchRevision, tasks.loading, tasks.loaded,
                tasks.problem, tasks.partial, tasks.items.map { LoadedSearchRow(it.id, it.title) })
        ))
    }
}
