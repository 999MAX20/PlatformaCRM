import Foundation
import CRMCore

@MainActor func checkClientWork(directory: URL) async throws -> Int {
    var count = 0, pending = 0
    func expect(_ value: Bool, _ message: String) throws { guard value else { throw ViewModelCheckFailure(message: message) }; count += 1 }
    func response(_ name: String, change: ((inout [String:Any]) -> Void)? = nil) throws -> ReadResponse {
        var data = try Data(contentsOf: directory.appendingPathComponent(name + ".json"))
        if let change { var object = try JSONSerialization.jsonObject(with: data) as! [String:Any]; change(&object); data = try JSONSerialization.data(withJSONObject: object) }
        return ReadResponse(status: 200,data: data)
    }
    let transport = SearchTransport(directory), repo = APIReadRepository(transport: transport)
    let model = ClientProfileViewModel(repository: repo), directoryModel = ClientDirectoryViewModel(repository: repo)
    await directoryModel.load(business: 101); directoryModel.query = "Alpha"
    await model.load(business: 101,id: 701)
    let work = model.work!, first = work.selection!
    for target in [ClientWorkTarget.task(1401),.conversation(931),.appointment(5101)] {
        await work.open(target,expected: first)
        try expect(work.detail != nil && work.failure == nil && !work.loading, "Provided relation did not perform an independent read")
        try expect(work.back(expected: first) && work.detail == nil && model.detail?.client.id == 701 && work.selection == first, "Child Back lost independent profile/selection")
    }
    let requests = await transport.recorded()
    try expect(requests.suffix(3).map(\.path) == ["/api/mobile/v1/tasks/1401/","/api/mobile/v1/inbox/931/","/api/mobile/v1/appointments/5101/"], "Client relation invented a route or auto-loaded lists")
    try expect(requests.suffix(3).map(\.query) == [["business":"101"],["business":"101","limit":"30"],["business":"101"]] && directoryModel.query == "Alpha" && directoryModel.selectedID == nil, "Child flow changed scope or originating query")
    await work.open(.task(1101)); await work.open(.conversation(901)); await work.open(.appointment(501))
    try expect(await transport.recorded().count == requests.count && work.selected == nil, "Client guessed relations from matching titles or hrefs")
    await model.load(business: 202,id: 801)
    for target in [ClientWorkTarget.task(2401),.conversation(1031),.appointment(5201)] { await work.open(target); try expect(work.detail != nil, "Second Business relation used first Business scope"); work.back() }
    await model.load(business: 101,id: 701)
    await transport.holdDetails()
    func read(_ target: ClientWorkTarget, _ reply: ReadResponse) async {
        let index = pending; pending += 1
        let running = Task { await work.open(target) }
        await transport.wait(index); await transport.resolve(index,reply); await running.value
    }
    for target in [ClientWorkTarget.task(1401),.conversation(931),.appointment(5101)] {
        await read(target,ReadResponse(status: 403,data: Data()))
        try expect(work.failure == .denied && work.detail == nil && model.detail?.client.id == 701, "Parent/window implied target permissions or cached body")
    }
    for value in [NSNull(),702] as [Any] {
        await read(.task(1401),try response("task-101-1401") { object in var row = object["task"] as! [String:Any]; row["client_id"] = value; object["task"] = row })
        try expect(work.failure == .invalidPayload && work.detail == nil, "Unknown/rebound Task Client was accepted")
    }
    await read(.conversation(931),try response("inbox-101-931") { $0["details"] = ["client":["id":702]] })
    try expect(work.failure == .invalidPayload && work.detail == nil, "Thread rebound Client was accepted")
    await read(.appointment(5101),try response("appointment-101-5101") { $0["details"] = ["client":["id":702]] })
    try expect(work.failure == .invalidPayload && work.detail == nil, "Appointment conflicting Client pair was accepted")
    await read(.task(1401),try response("task-101-1401") { $0["business"] = 202 })
    try expect(work.failure == .invalidPayload, "Foreign Business Task accepted")
    await read(.task(1401),try response("task-101-1402"))
    try expect(work.failure == .invalidPayload, "Wrong Task identity accepted")
    await read(.appointment(5101),try response("appointment-101-5101") { object in var row = object["appointment"] as! [String:Any]; row["start_at"] = NSNull(); row["end_at"] = NSNull(); object["appointment"] = row })
    try expect(work.detail != nil && work.failure == nil, "Unknown time erased independent historical Appointment identity")
    let oldIndex = pending; pending += 1
    let old = Task { await work.open(.task(1401)) }; await transport.wait(oldIndex)
    await read(.task(1401),try response("task-101-1401") { object in var row = object["task"] as! [String:Any]; row["title"] = NSNull(); object["task"] = row })
    await transport.resolve(oldIndex,try response("task-101-1401")); await old.value
    try expect(work.detail?.title == nil && work.tasks?.first?.title == nil, "Old response restored newly withheld title")
    let closingIndex = pending; pending += 1
    let closing = Task { await work.open(.conversation(931)) }; await transport.wait(closingIndex); work.back()
    await read(.conversation(931),try response("inbox-101-931"))
    await transport.resolve(closingIndex,ReadResponse(status: 503,data: Data())); await closing.value
    try expect(work.detail != nil && work.failure == nil, "Back/reopen accepted late old error")
    let cancelledIndex = pending; pending += 1
    let cancelled = Task { await work.open(.task(1401)) }; await transport.wait(cancelledIndex); await transport.cancel(cancelledIndex); await cancelled.value
    try expect(work.selected == nil && !work.loading && model.detail != nil, "Cancelled child stranded route or erased parent")
    let stale = work.selection!, lateIndex = pending; pending += 1
    let late = Task { await work.open(.task(1401),expected: stale) }; await transport.wait(lateIndex)
    let refreshIndex = pending; pending += 1
    let refresh = Task { await model.load(business:101,id:701) }; await transport.wait(refreshIndex)
    try expect(work.selection == nil && work.detail == nil, "Parent load retained old child context")
    await transport.resolve(refreshIndex,try response("client-101-701")); await refresh.value
    await transport.resolve(lateIndex,try response("task-101-1401")); await late.value
    try expect(work.detail == nil && work.selected == nil, "Parent refresh accepted old child response")
    let before = await transport.recorded().count
    await work.open(.task(1401),expected: stale)
    let afterStale = await transport.recorded().count
    try expect(!work.back(expected: stale) && afterStale == before, "Stale UI token started/closed new route")
    work.clear()
    await work.open(.task(1401))
    let afterClear = await transport.recorded().count
    try expect(work.parent == nil && work.tasks == nil && work.conversations == nil && work.detail == nil && afterClear == before, "Closed parent retained dependent state or started read")
    return count
}
