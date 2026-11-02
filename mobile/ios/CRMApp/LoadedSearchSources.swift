import CRMCore

@MainActor enum LoadedSearchSources {
    static func feed(agenda: AgendaViewModel, clients: ClientDirectoryViewModel, inbox: InboxViewModel, tasks: TaskListViewModel) -> LoadedSearchFeed {
        let business = agenda.session.selection?.business.id, epoch = agenda.businessEpoch
        func source(_ kind: LoadedSearchKind, business sourceBusiness: Int?, epoch sourceEpoch: Int?, generation: Int,
                    loading: Bool, loaded: Bool, failure: ReadFailure?, partial: Bool, rows: [LoadedSearchRow], day: String? = nil) -> LoadedSearchSource {
            guard let business, business == sourceBusiness, sourceEpoch == epoch else { return LoadedSearchSource(kind: kind, token: nil, coverage: .notLoaded) }
            let coverage: LoadedSearchCoverage = loading ? .loading : failure != nil ? (failure == .denied ? .denied : .unavailable) : !loaded ? .notLoaded : partial ? .partial : .loaded
            return LoadedSearchSource(kind: kind, token: LoadedSearchToken(kind: kind, business: business, epoch: epoch, generation: generation, day: day), coverage: coverage, rows: rows)
        }
        let day = agenda.session.selection?.day
        return LoadedSearchFeed(business: business, epoch: epoch, sources: [
            source(.appointments, business: business, epoch: epoch, generation: agenda.searchRevision, loading: agenda.loading,
                   loaded: day != nil && agenda.session.responseDay == day, failure: agenda.failure ?? (agenda.session.sourceDayMismatch ? .invalidPayload : nil), partial: agenda.session.isPartial,
                   rows: agenda.session.items.map { LoadedSearchRow(id: $0.id, title: $0.title) }, day: day),
            source(.clients, business: clients.business, epoch: clients.scopeEpoch, generation: clients.searchRevision, loading: clients.loading,
                   loaded: clients.loaded, failure: clients.failure, partial: clients.partial, rows: clients.items.map { LoadedSearchRow(id: $0.id, title: $0.title) }),
            source(.inbox, business: inbox.business, epoch: inbox.scopeEpoch, generation: inbox.searchRevision, loading: inbox.loading,
                   loaded: inbox.loaded, failure: inbox.failure, partial: inbox.partial, rows: inbox.items.map { LoadedSearchRow(id: $0.id, title: $0.title) }),
            source(.tasks, business: tasks.business, epoch: tasks.scopeEpoch, generation: tasks.searchRevision, loading: tasks.loading,
                   loaded: tasks.loaded, failure: tasks.failure, partial: tasks.partial, rows: tasks.items.map { LoadedSearchRow(id: $0.id, title: $0.title) })
        ])
    }
}
