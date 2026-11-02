package kz.zani.mobile.core

// Ephemeral presentation projection, never a server DTO, durable index or rights grant.
enum class LoadedSearchKind(val key: String, val tab: Int) { APPOINTMENTS("appointments", 1), CLIENTS("clients", 2), INBOX("inbox", 3), TASKS("tasks", 4) }
enum class LoadedSearchCoverage(val key: String) {
    NOT_LOADED("searchNotLoaded"), LOADING("loading"), LOADED("searchLoaded"), PARTIAL("partial"), DENIED("denied"), UNAVAILABLE("unavailable");
    val ready get() = this == LOADED || this == PARTIAL
}
// Raw title identity stays exact (including nil/empty); query collation is separate below.
data class LoadedSearchRow(val id: Int, val title: String?)
data class LoadedSearchToken(val kind: LoadedSearchKind, val business: Int, val epoch: Int, val generation: Int, val day: String? = null)
data class LoadedSearchIdentity(val kind: LoadedSearchKind, val business: Int, val id: Int)
data class LoadedSearchHit(val identity: LoadedSearchIdentity, val title: String, val token: LoadedSearchToken)
data class LoadedSearchSource(val kind: LoadedSearchKind, val token: LoadedSearchToken?, val coverage: LoadedSearchCoverage, val rows: List<LoadedSearchRow> = emptyList())
@ConsistentCopyVisibility
data class LoadedSearchFeed private constructor(val business: Int?, val epoch: Int, val sources: List<LoadedSearchSource>) {
    companion object {
        fun create(business: Int?, epoch: Int, sources: List<LoadedSearchSource>): LoadedSearchFeed = LoadedSearchFeed(business, epoch, LoadedSearchKind.entries.map { kind ->
            val candidates = sources.filter { it.kind == kind }
            val source = candidates.singleOrNull()
            val token = source?.token
            when {
                source == null -> LoadedSearchSource(kind, null, if (candidates.isEmpty()) LoadedSearchCoverage.NOT_LOADED else LoadedSearchCoverage.UNAVAILABLE)
                !source.coverage.ready -> source.copy(rows = emptyList())
                token == null || token.kind != kind || token.business <= 0 || token.business != business || epoch <= 0 || token.epoch != epoch || token.generation <= 0 ||
                    source.rows.any { it.id <= 0 } || source.rows.map { it.id }.distinct().size != source.rows.size -> LoadedSearchSource(kind, null, LoadedSearchCoverage.UNAVAILABLE)
                else -> source
            }
        })
    }
    val hasLoadedSource get() = sources.any { it.coverage.ready }
    fun source(kind: LoadedSearchKind) = sources.firstOrNull { it.kind == kind }
    fun contains(hit: LoadedSearchHit): Boolean {
        val source = source(hit.identity.kind) ?: return false
        return source.coverage.ready && source.token == hit.token && hit.identity.business == business && source.rows.any { it.id == hit.identity.id && it.title == hit.title }
    }
    fun matches(query: String, excluding: Set<LoadedSearchIdentity> = emptySet()): List<LoadedSearchHit> {
        val needle = query.trim()
        if (needle.isEmpty()) return emptyList()
        return sources.flatMap { source ->
            val token = source.token
            if (!source.coverage.ready || token == null) emptyList() else source.rows.mapNotNull { row ->
                val id = LoadedSearchIdentity(source.kind, token.business, row.id)
                row.title?.takeIf { it.isNotBlank() && it.contains(needle, ignoreCase = true) && id !in excluding }?.let { LoadedSearchHit(id, it, token) }
            }
        }
    }
}
