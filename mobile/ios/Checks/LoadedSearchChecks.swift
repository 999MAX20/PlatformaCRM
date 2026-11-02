import Foundation
import CRMCore

func runLoadedSearchChecks(directory:URL) throws -> Int {
    var count = 0
    func expect(_ value: Bool, _ message: String) throws { guard value else { throw CheckFailure(message: message) }; count += 1 }
    func source(_ kind: LoadedSearchKind, _ rows: [LoadedSearchRow], business: Int = 101, epoch: Int = 1, coverage: LoadedSearchCoverage = .loaded) -> LoadedSearchSource {
        LoadedSearchSource(kind: kind, token: LoadedSearchToken(kind: kind, business: business, epoch: epoch, generation: 1), coverage: coverage, rows: rows)
    }
    let same = [LoadedSearchRow(id: 9, title: "Same title")]
    let feed = LoadedSearchFeed(business: 101, epoch: 1, sources: [source(.tasks, same), source(.inbox, same), source(.clients, same), source(.appointments, [LoadedSearchRow(id: 12, title: "same title"), same[0]])])
    try expect(feed.matches("  SAME  ").map(\.id.kind) == [.appointments,.appointments,.clients,.inbox,.tasks], "Search reordered or merged kinds/titles")
    try expect(feed.matches("same").map(\.id.id) == [12,9,9,9,9], "Source row order changed")
    try expect(Set(feed.matches("same").map(\.id)).count == 5, "Same numeric IDs across kinds collapsed")
    try expect(feed.matches(" \n").isEmpty && feed.hasLoadedSource, "Blank query returned all indexed objects")
    try expect(feed.matches("absent").isEmpty, "Invented fuzzy/relevance match")
    let hit = feed.matches("same").last!
    try expect(feed.contains(hit) && feed.matches("same", excluding: [hit.id]).count == 4, "Exact suppressed identity crossed kinds")
    let stale = LoadedSearchFeed(business: 101, epoch: 2, sources: feed.sources)
    try expect(!stale.hasLoadedSource && stale.matches("same").isEmpty && !stale.contains(hit), "Old Business epoch reentered search")
    let foreign = LoadedSearchFeed(business: 202, epoch: 1, sources: feed.sources)
    try expect(!foreign.hasLoadedSource && foreign.matches("same").isEmpty, "Foreign Business searchable")
    for status in [LoadedSearchCoverage.notLoaded,.loading,.denied,.unavailable] {
        let f = LoadedSearchFeed(business: 101, epoch: 1, sources: [source(.tasks, same, coverage: status)])
        try expect(f.source(.tasks)?.coverage == status && f.source(.tasks)?.rows.isEmpty == true && !f.hasLoadedSource, "Unavailable source retained candidates")
    }
    let partial = LoadedSearchFeed(business: 101, epoch: 1, sources: [source(.tasks, same, coverage: .partial)])
    try expect(partial.matches("same").count == 1 && partial.source(.tasks)?.coverage == .partial, "Partial became complete or unsearchable")
    let duplicates = LoadedSearchFeed(business: 101, epoch: 1, sources: [source(.tasks, same + same)])
    try expect(!duplicates.hasLoadedSource && duplicates.matches("same").isEmpty, "Duplicate IDs silently deduplicated")
    let ambiguous = LoadedSearchFeed(business: 101, epoch: 1, sources: [source(.tasks, same), source(.tasks, same)])
    try expect(ambiguous.source(.tasks)?.coverage == .unavailable && !ambiguous.hasLoadedSource, "Ambiguous source treated as unloaded/confirmed")
    let invalid = LoadedSearchFeed(business: 101, epoch: 1, sources: [source(.tasks, [LoadedSearchRow(id: 0, title: "same")])])
    try expect(!invalid.hasLoadedSource, "Nonpositive ID granted navigation")
    let nulls = LoadedSearchFeed(business: 101, epoch: 1, sources: [source(.tasks, [LoadedSearchRow(id: 1, title: nil),LoadedSearchRow(id: 2, title: "  ")])])
    try expect(nulls.matches("unavailable").isEmpty && nulls.matches(" ").isEmpty, "Unknown title indexed as placeholder")
    let noToken = LoadedSearchFeed(business: 101, epoch: 1, sources: [LoadedSearchSource(kind: .tasks, token: nil, coverage: .loaded, rows: same)])
    try expect(!noToken.hasLoadedSource, "Untagged source searchable")
    let empty = LoadedSearchFeed(business: 101, epoch: 1, sources: [])
    try expect(!empty.hasLoadedSource && empty.sources.count == 4 && empty.matches("same").isEmpty, "Missing sources pretended loaded empty")
    let cases=(try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("loaded-search-exact-header-cases.json"))) as! [String:Any])["cases"] as! [[String:Any]]
    for row in cases {
        let before=row["before_title"] as! String,after=row["after_title"] as? String,changed=row["changed"] as! Bool
        for kind in LoadedSearchKind.allCases {
            let a=LoadedSearchRow(id:9,title:before),b=LoadedSearchRow(id:9,title:after)
            let f=LoadedSearchFeed(business:101,epoch:1,sources:[source(kind,[a])]),g=LoadedSearchFeed(business:101,epoch:1,sources:[source(kind,[b])])
            let hit=f.matches(" SHARED ").first!
            try expect((a != b)==changed && (f != g)==changed,"Exact raw header identity collapsed in row/source/feed")
            try expect(g.contains(hit) == !changed,"Old hit accepted byte-different/withheld provided header")
            try expect(hit.title.utf8.elementsEqual(before.utf8) && f.matches(" SHARED ")==[hit],"Header identity changed raw title or text matching")
            if let after,!after.isEmpty {
                let current=g.matches("shared").first!
                try expect((hit != current)==changed && current.title.utf8.elementsEqual(after.utf8),"Hit equality lost exact title bytes")
            } else {try expect(g.matches("shared").isEmpty,"Withheld/empty title became placeholder match")}
            try expect(g.sources.count==4 && g.source(kind)?.token==hit.token && g.source(kind)?.coverage == .loaded,"Header equality invented source/token/coverage changes")
        }
    }
    try expect(LoadedSearchHeader.same(nil,nil) && !LoadedSearchHeader.same(nil,"") && !LoadedSearchHeader.same("",nil),"Nil/empty header identity collapsed")
    try expect(LoadedSearchRow(id:9,title:nil) != LoadedSearchRow(id:9,title:""),"Row equated withheld and empty headers")
    return count
}
