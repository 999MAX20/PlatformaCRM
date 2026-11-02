import Foundation
import CRMCore

actor SearchTransport: ReadTransport {
    let fixture: FixtureTransport
    private var requests: [ReadRequest] = []
    private var held = false, next = 0
    private var pending: [Int: CheckedContinuation<ReadResponse, any Error>] = [:]
    private var waiters: [Int: CheckedContinuation<Void, Never>] = [:]
    private var overrides: [String: ReadResponse] = [:]
    init(_ directory: URL) { fixture = FixtureTransport(directory: directory) }
    func holdDetails() { held = true }
    func override(_ path: String, _ response: ReadResponse) { overrides[path] = response }
    func get(_ request: ReadRequest) async throws -> ReadResponse {
        requests.append(request)
        if let response = overrides.removeValue(forKey: request.path) { return response }
        if held && Int(request.path.split(separator: "/").last ?? "") != nil {
            let id = next; next += 1
            return try await withCheckedThrowingContinuation { pending[id] = $0; waiters.removeValue(forKey: id)?.resume() }
        }
        return try await fixture.get(request)
    }
    func wait(_ id: Int) async { if pending[id] == nil { await withCheckedContinuation { waiters[id] = $0 } } }
    func resolve(_ id: Int, _ response: ReadResponse) { pending.removeValue(forKey: id)!.resume(returning: response) }
    func cancel(_ id: Int) { pending.removeValue(forKey: id)!.resume(throwing: CancellationError()) }
    func recorded() -> [ReadRequest] { requests }
}

@MainActor func checkLoadedSearch(directory: URL) async throws -> Int {
    var count = 0
    func expect(_ value: Bool, _ message: String) throws { guard value else { throw ViewModelCheckFailure(message: message) }; count += 1 }
    func response(_ name: String, change: ((inout [String:Any]) -> Void)? = nil) throws -> ReadResponse {
        var data = try Data(contentsOf: directory.appendingPathComponent(name + ".json"))
        if let change { var object = try JSONSerialization.jsonObject(with: data) as! [String:Any]; change(&object); data = try JSONSerialization.data(withJSONObject: object) }
        return ReadResponse(status: 200, data: data)
    }
    let transport = SearchTransport(directory), repo = APIReadRepository(transport: transport)
    let agenda = AgendaViewModel(repository: repo, initialDate: Appointment.instant("2026-10-28T07:00:00Z")!)
    let clients = ClientDirectoryViewModel(repository: repo), inbox = InboxViewModel(repository: repo), tasks = TaskListViewModel(repository: repo)
    let search = LoadedSearchViewModel(repository: repo)
    func feed() -> LoadedSearchFeed { LoadedSearchSources.feed(agenda: agenda, clients: clients, inbox: inbox, tasks: tasks) }
    search.reconcile(feed()); search.query = "absent"
    try expect(!search.showsNoMatches && !search.feed.hasLoadedSource, "Unloaded sources asserted no matches")
    await agenda.start(); let epoch = agenda.businessEpoch; agenda.mode = .calendar
    search.reconcile(feed()); search.query = "synthetic"
    try expect(search.matches.count == 2 && search.feed.sources.filter { $0.coverage.ready }.count == 1, "Search auto-loaded missing modules")
    try expect(await transport.recorded().count == 2, "Projection/query made a request")
    await clients.load(business: 101, epoch: epoch); await inbox.load(business: 101, epoch: epoch); await tasks.load(business: 101, epoch: epoch)
    clients.query = "Beta"; inbox.query = "response"; inbox.unreadOnly = true; tasks.query = "review"; tasks.status = "done"
    search.reconcile(feed())
    try expect(search.matches.count == 9, "Module-local filters restricted loaded title search")
    for hidden in ["+70000000001", "alpha@example.invalid", "operator response", "profile note", "follow-up comment", "task context", "7001", "/app/calendar"] {
        search.query = hidden; try expect(search.matches.isEmpty, "Non-title field leaked into search: \(hidden)")
    }
    search.query = "beta"
    try expect(search.matches.map(\.id.kind) == [.clients,.inbox,.tasks], "Same title joined kinds or changed source order")
    search.query = "synthetic"
    let hits = search.matches
    let before = await transport.recorded().count
    for kind in LoadedSearchKind.allCases {
        let hit = hits.first { $0.id.kind == kind }!; await search.open(hit)
        try expect(search.failure == nil && !search.loading && (search.detail != nil || search.profile.detail != nil), "Independent result read failed: \(kind)")
        search.back(); try expect(search.query == "synthetic" && search.matches == hits && search.profile.detail == nil, "Back lost query/order or retained profile")
    }
    let reads = await transport.recorded()
    try expect(reads.count == before + 4 && reads.suffix(4).map(\.path) == ["/api/mobile/v1/appointments/501/","/api/mobile/v1/clients/701/","/api/mobile/v1/inbox/901/","/api/mobile/v1/tasks/1101/"], "Search invented a route or list request")
    try expect(clients.query == "Beta" && inbox.query == "response" && inbox.unreadOnly && tasks.query == "review" && tasks.status == "done" && agenda.mode == .calendar && agenda.session.selection?.day == "2026-10-28", "Search changed originating module context")
    try expect(clients.selectedID == nil && inbox.selectedID == nil && tasks.selectedID == nil && agenda.session.detail == nil, "Search reused mutable module detail route")
    await transport.holdDetails()
    let task = hits.first { $0.id.kind == .tasks }!, thread = hits.first { $0.id.kind == .inbox }!, client = hits.first { $0.id.kind == .clients }!
    let denied = Task { await search.open(task) }; await transport.wait(0); await transport.resolve(0, ReadResponse(status: 403, data: Data())); await denied.value
    try expect(search.failure == .denied && search.detail == nil && !search.matches.contains(task), "Denied result fell back to list candidate/body")
    let retry = Task { await search.open(task, retry: true) }; await transport.wait(1); await transport.resolve(1, try response("task-101-1101")); await retry.value
    try expect(search.detail != nil && !search.matches.contains(task), "Retry reintroduced denied old snapshot")
    search.back(); await tasks.load(business: 101, epoch: epoch); search.reconcile(feed())
    try expect(search.matches.contains(where: { $0.id == task.id }) && search.query == "synthetic", "New confirmed list did not clear scoped suppression")
    let old = Task { await search.open(thread) }; await transport.wait(2); search.back()
    let newer = Task { await search.open(thread) }; await transport.wait(3)
    let redacted = try response("inbox-101-901") { object in var row = object["conversation"] as! [String:Any]; row["title"] = NSNull(); object["conversation"] = row }
    await transport.resolve(3, redacted); await newer.value; await transport.resolve(2, ReadResponse(status: 403, data: Data())); await old.value
    try expect(search.detail?.title == nil && search.failure == nil && !search.matches.contains(thread), "Late failure restored title or replaced newer detail")
    search.back()
    let currentTask = search.matches.first { $0.id.kind == .tasks }!
    let refreshing = Task { await search.open(currentTask) }; await transport.wait(4)
    await transport.override("/api/mobile/v1/tasks/", ReadResponse(status: 403, data: Data())); await tasks.load(business: 101, epoch: epoch); search.reconcile(feed())
    await transport.resolve(4, try response("task-101-1101")); await refreshing.value
    try expect(search.selected == nil && search.detail == nil && search.feed.source(.tasks)?.coverage == .denied && !search.matches.contains(where: { $0.id.kind == .tasks }), "Refresh/denied source accepted late result or stale candidates")
    let pendingClient = Task { await search.open(client) }; await transport.wait(5)
    await agenda.load(business: 202); search.reconcile(feed()); await transport.resolve(5, try response("client-101-701")); await pendingClient.value
    try expect(search.profile.detail == nil && search.selected == nil && search.query.isEmpty && search.feed.business == 202, "Business switch accepted foreign profile/query")
    await agenda.load(business: 101); search.reconcile(feed()); search.query = "synthetic"
    try expect(agenda.businessEpoch > epoch && search.matches.count == 2 && search.feed.source(.clients)?.coverage == .notLoaded && search.feed.source(.inbox)?.coverage == .notLoaded, "Same-ID Business round trip reindexed old lists")
    await clients.load(business: 101); search.reconcile(feed())
    try expect(search.feed.source(.clients)?.coverage == .notLoaded, "Untagged list became current search source")
    await clients.load(business: 101, epoch: agenda.businessEpoch); search.reconcile(feed())
    let scopedClient = search.matches.first { $0.id.kind == .clients }!
    let wrong = Task { await search.open(scopedClient) }; await transport.wait(6)
    await transport.resolve(6, try response("client-101-701") { $0["business"] = 202 }); await wrong.value
    try expect(search.failure == .invalidPayload && search.profile.detail == nil && !search.matches.contains(scopedClient), "Independent Client GET skipped Business guard")
    search.back()
    let appointment = search.matches.first { $0.id.kind == .appointments }!
    let cancelled = Task { await search.open(appointment) }; await transport.wait(7); await transport.cancel(7); await cancelled.value
    try expect(search.selected == nil && !search.loading && search.matches.contains(appointment), "Cancellation stranded result or denied valid candidate")
    let wrongID = Task { await search.open(appointment) }; await transport.wait(8)
    await transport.resolve(8, try response("appointment-101-502")); await wrongID.value
    try expect(search.failure == .invalidPayload && search.detail == nil && !search.matches.contains(appointment), "Independent Appointment GET skipped ID guard")
    search.back(); search.query = "no-such-title"
    try expect(search.showsNoMatches && search.coverage(search.feed.source(.appointments)!) == .partial, "No-match or suppressed-source coverage misleading")
    return count
}
