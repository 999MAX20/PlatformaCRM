import Foundation

// Ephemeral presentation projection. Never a server DTO, durable index or rights grant.
public enum LoadedSearchKind: String, CaseIterable, Sendable {
    case appointments, clients, inbox, tasks
    public var tab: Int { Self.allCases.firstIndex(of: self)! + 1 }
}
public enum LoadedSearchCoverage: String, Sendable {
    case notLoaded = "searchNotLoaded", loading, loaded = "searchLoaded", partial, denied, unavailable
    public var ready: Bool { self == .loaded || self == .partial }
}
// Header identity is exact; text-query collation remains in matches(_:excluding:).
public enum LoadedSearchHeader {
    public static func same(_ lhs:String?,_ rhs:String?)->Bool {
        SourceTextIdentity.same(lhs,rhs)
    }
}
public struct LoadedSearchRow: Equatable, Sendable {
    public let id: Int
    public let title: String?
    public init(id: Int, title: String?) { self.id = id; self.title = title }
    public static func ==(lhs:Self,rhs:Self)->Bool {lhs.id==rhs.id && LoadedSearchHeader.same(lhs.title,rhs.title)}
}
public struct LoadedSearchToken: Hashable, Sendable {
    public let kind: LoadedSearchKind
    public let business: Int
    public let epoch: Int
    public let generation: Int
    public let day: String?
    public init(kind: LoadedSearchKind, business: Int, epoch: Int, generation: Int, day: String? = nil) {
        self.kind = kind; self.business = business; self.epoch = epoch; self.generation = generation; self.day = day
    }
}
public struct LoadedSearchIdentity: Hashable, Sendable {
    public let kind: LoadedSearchKind
    public let business: Int
    public let id: Int
    public init(kind: LoadedSearchKind, business: Int, id: Int) { self.kind = kind; self.business = business; self.id = id }
}
public struct LoadedSearchHit: Equatable, Identifiable, Sendable {
    public let id: LoadedSearchIdentity
    public let title: String
    public let token: LoadedSearchToken
    public static func ==(lhs:Self,rhs:Self)->Bool {lhs.id==rhs.id && lhs.token==rhs.token && LoadedSearchHeader.same(lhs.title,rhs.title)}
}
public struct LoadedSearchSource: Equatable, Sendable {
    public let kind: LoadedSearchKind
    public let token: LoadedSearchToken?
    public let coverage: LoadedSearchCoverage
    public let rows: [LoadedSearchRow]
    public init(kind: LoadedSearchKind, token: LoadedSearchToken?, coverage: LoadedSearchCoverage, rows: [LoadedSearchRow] = []) {
        self.kind = kind; self.token = token; self.coverage = coverage; self.rows = rows
    }
}
public struct LoadedSearchFeed: Equatable, Sendable {
    public let business: Int?
    public let epoch: Int
    public let sources: [LoadedSearchSource]
    public init(business: Int?, epoch: Int, sources: [LoadedSearchSource]) {
        self.business = business; self.epoch = epoch
        self.sources = LoadedSearchKind.allCases.map { kind in
            let matches = sources.filter { $0.kind == kind }
            guard matches.count == 1, let source = matches.first else { return LoadedSearchSource(kind: kind, token: nil, coverage: matches.isEmpty ? .notLoaded : .unavailable) }
            guard source.coverage.ready else { return LoadedSearchSource(kind: kind, token: source.token, coverage: source.coverage) }
            guard let token = source.token, token.kind == kind, token.business > 0, token.business == business,
                  epoch > 0, token.epoch == epoch, token.generation > 0,
                  source.rows.allSatisfy({ $0.id > 0 }), Set(source.rows.map(\.id)).count == source.rows.count else {
                return LoadedSearchSource(kind: kind, token: nil, coverage: .unavailable)
            }
            return source
        }
    }
    public var hasLoadedSource: Bool { sources.contains { $0.coverage.ready } }
    public func source(_ kind: LoadedSearchKind) -> LoadedSearchSource? { sources.first { $0.kind == kind } }
    public func contains(_ hit: LoadedSearchHit) -> Bool {
        guard let source = source(hit.id.kind), source.coverage.ready, source.token == hit.token,
              hit.id.business == business else { return false }
        return source.rows.contains { $0.id == hit.id.id && LoadedSearchHeader.same($0.title,hit.title) }
    }
    public func matches(_ query: String, excluding: Set<LoadedSearchIdentity> = []) -> [LoadedSearchHit] {
        let needle = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !needle.isEmpty else { return [] }
        return sources.flatMap { source -> [LoadedSearchHit] in
            guard source.coverage.ready, let token = source.token else { return [] }
            return source.rows.compactMap { row in
                let id = LoadedSearchIdentity(kind: source.kind, business: token.business, id: row.id)
                guard !excluding.contains(id), let title = row.title, !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
                      title.range(of: needle, options: .caseInsensitive) != nil else { return nil }
                return LoadedSearchHit(id: id, title: title, token: token)
            }
        }
    }
}
