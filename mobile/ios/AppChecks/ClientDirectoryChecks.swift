import Foundation
import CRMCore

actor ControlledClients: ClientRepository {
    private var pending: [Int: CheckedContinuation<ClientList, any Error>] = [:]
    private var waiters: [Int: CheckedContinuation<Void, Never>] = [:]
    private var next = 0
    func clients(business: Int) async throws -> ClientList {
        let request = next; next += 1
        return try await withCheckedThrowingContinuation { continuation in
            pending[request] = continuation; waiters.removeValue(forKey: request)?.resume()
        }
    }
    func wait(_ request: Int) async {
        if pending[request] != nil { return }
        await withCheckedContinuation { waiters[request] = $0 }
    }
    func resolve(_ request: Int, _ result: Result<ClientList, ReadFailure>) {
        let continuation = pending.removeValue(forKey: request)!
        switch result {
        case .success(let value): continuation.resume(returning: value)
        case .failure(let error): continuation.resume(throwing: error)
        }
    }
    func requests() -> Int { next }
}

@MainActor func checkClientDirectory(directory: URL) async throws -> Int {
    func page(_ business: Int) throws -> ClientList {
        try JSONDecoder().decode(ClientList.self, from: Data(contentsOf: directory.appendingPathComponent("clients-\(business).json")))
    }
    let a = try page(101), b = try page(202)
    let source = ControlledClients(); let model = ClientDirectoryViewModel(repository: source)
    var count = 0
    func expect(_ condition: Bool, _ message: String) throws {
        guard condition else { throw ViewModelCheckFailure(message: message) }; count += 1
    }
    try expect(!model.showsEmpty, "Unknown client state looked empty")
    let first = Task { await model.load(business: 101) }; await source.wait(0)
    await source.resolve(0, .success(a)); await first.value
    try expect(model.items.map(\.id) == [701, 702], "Client fixture identities changed")
    for query in [" ALPHA ", "000000001", "ALPHA@EXAMPLE.INVALID"] {
        model.query = query
        try expect(model.visible.map(\.id) == [701], "Local client name/phone/email search failed")
    }
    model.open(id: 701); try expect(model.selected?.id == 701, "Contact card did not open")
    model.back(); try expect(model.selected == nil && model.query == "ALPHA@EXAMPLE.INVALID", "Back lost search or retained card")
    model.open(id: 999); try expect(model.selected == nil, "Unknown client identity opened")
    model.query = "Beta"; model.open(id: 702)
    try expect(model.selected?.phone == nil && model.selected?.email == nil, "Unavailable contacts were reconstructed")
    model.back(); model.query = "notAvailable"
    try expect(model.visible.isEmpty && model.showsEmpty, "Placeholder was indexed as client data")
    let localRequests = await source.requests(); try expect(localRequests == 1, "Local search/card/back issued a read")

    model.query = "Alpha"; model.open(id: 701)
    let old = Task { await model.load(business: 101) }; await source.wait(1)
    let other = Task { await model.load(business: 202) }; await source.wait(2)
    try expect(model.items.isEmpty && model.query.isEmpty && model.selected == nil, "Business switch kept prior contact data")
    await source.resolve(2, .success(b)); await other.value
    await source.resolve(1, .success(a)); await old.value
    try expect(model.business == 202 && model.items.map(\.id) == [801], "Late client response entered another Business")

    let failed = Task { await model.load(business: 101) }; await source.wait(3); model.query = "Alpha"
    await source.resolve(3, .failure(.denied)); await failed.value
    try expect(model.failure == .denied && model.query == "Alpha" && !model.showsEmpty, "Denied read lost query or appeared empty")
    let retry = Task { await model.load(business: 101) }; await source.wait(4)
    await source.resolve(4, .success(b)); await retry.value
    try expect(model.failure == .invalidPayload && model.items.isEmpty, "Foreign Business payload was accepted")
    let recovering = Task { await model.load(business: 101) }; await source.wait(5)
    await source.resolve(5, .success(a)); await recovering.value
    try expect(model.failure == nil && model.visible.map(\.id) == [701], "Retry did not recover scoped search")

    let staleError = Task { await model.load(business: 101) }; await source.wait(6)
    let fresh = Task { await model.load(business: 101) }; await source.wait(7)
    let partial = try JSONDecoder().decode(ClientList.self, from: Data("{\"business\":101,\"items\":[],\"summary\":{\"total\":5}}".utf8))
    await source.resolve(7, .success(partial)); await fresh.value
    await source.resolve(6, .failure(.unavailable)); await staleError.value
    try expect(model.failure == nil && model.partial && !model.showsEmpty, "Old failure or partial-zero corrupted current state")
    let leaving = Task { await model.load(business: 101) }; await source.wait(8)
    await model.load(business: nil)
    await source.resolve(8, .success(a)); await leaving.value
    try expect(model.business == nil && model.items.isEmpty && model.selected == nil && !model.showsEmpty, "Cleared scope was repopulated")
    count += try await checkConfiguredClientRead(directory:directory)
    return count
}

private actor ControlledConfiguredClientHTTP: NativeReadHTTPExchange {
    private var pending:[CheckedContinuation<ReadResponse,Never>]=[]
    private var waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    private var descriptors:[URLRequest]=[]
    func execute(_ request:URLRequest) async throws -> ReadResponse {await withCheckedContinuation {let n=pending.count;descriptors.append(request);pending.append($0);waiters.removeValue(forKey:n)?.resume()}}
    func wait(_ n:Int) async {if pending.count<=n {await withCheckedContinuation {waiters[n]=$0}}}
    func resolve(_ n:Int,_ value:ReadResponse) {pending[n].resume(returning:value)}
    func recorded() -> [URLRequest] {descriptors}
}
@MainActor private func checkConfiguredClientRead(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let config=try NativeConnectionConfiguration(publicValues:["CRM_API_ORIGIN":"https://fixture-api.example.invalid","CRM_READ_TIMEOUT_SECONDS":"7"]),http=ControlledConfiguredClientHTTP()
    let model=ClientDirectoryViewModel(repository:APIReadRepository(transport:BackendReadTransport(builder:try config.requestBuilder(),exchange:http)))
    let old=Task {await model.load(business:101,epoch:12)};await http.wait(0)
    let fresh=Task {await model.load(business:202,epoch:13)};await http.wait(1)
    let other=try Data(contentsOf:directory.appendingPathComponent("clients-202.json")),first=try Data(contentsOf:directory.appendingPathComponent("clients-101.json"))
    await http.resolve(1,ReadResponse(status:200,data:other));await fresh.value;await http.resolve(0,ReadResponse(status:200,data:first));await old.value
    try expect(model.business==202 && model.items.map(\.id)==[801] && model.failure==nil,"Configured HTTP late read crossed Business/owner")
    model.draft.open(ClientDraftContext(business:202,epoch:13));let selection=model.draft.session.selection!;model.draft.update(.fullName,"Unsent configured draft",selection)
    let unavailable=Task {await model.load(business:202,epoch:13)};await http.wait(2);await http.resolve(2,ReadResponse(status:503,data:Data()));await unavailable.value
    try expect(model.failure == .unavailable && model.items.isEmpty && model.draft.session.values.fullName=="Unsent configured draft","HTTP failure substituted fixture rows or lost same-owner input")
    let denied=Task {await model.load(business:202,epoch:13)};await http.wait(3);await http.resolve(3,ReadResponse(status:403,data:Data("bad body".utf8)));await denied.value
    try expect(model.failure == .denied && model.items.isEmpty && model.draft.session.values.fullName=="Unsent configured draft","HTTP403 became available data or reset manual input")
    let descriptors=await http.recorded()
    try expect(descriptors.count==4 && descriptors.allSatisfy {$0.httpMethod=="GET" && $0.httpBody==nil && URLComponents(url:$0.url!,resolvingAgainstBaseURL:false)?.path=="/api/mobile/v1/clients/" && $0.url?.host=="fixture-api.example.invalid" && $0.timeoutInterval==7},"Configured parent introduced retries/commands/timeout default")
    try expect(descriptors.map {URLComponents(url:$0.url!,resolvingAgainstBaseURL:false)!.queryItems!.first {$0.name=="business"}!.value!}==["101","202","202","202"],"Configured source query lost exact Business ownership")
    return count
}
