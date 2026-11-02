import Foundation
import CRMCore

actor QueryRecordingTransport: ReadTransport {
    private let fixture: FixtureTransport
    private var captured: [ReadRequest]=[]
    init(_ directory: URL) {fixture=FixtureTransport(directory:directory,taskQueries:true)}
    func get(_ request: ReadRequest) async throws -> ReadResponse {captured.append(request);return try await fixture.get(request)}
    func recorded() -> [ReadRequest] {captured}
}

actor ControlledTaskQueries: TaskQueryRepository {
    private var pending: [Int:CheckedContinuation<TaskPage,any Error>]=[:]
    private var waiters: [Int:CheckedContinuation<Void,Never>]=[:]
    private var calls: [TaskQueryFilter]=[]
    let directory: URL
    init(_ directory: URL) {self.directory=directory}
    func tasks(business: Int) async throws -> TaskPage {try await tasks(business:business,filter:TaskQueryFilter())}
    func tasks(business: Int,filter: TaskQueryFilter) async throws -> TaskPage {
        let id=calls.count;calls.append(filter)
        return try await withCheckedThrowingContinuation {pending[id]=$0;waiters.removeValue(forKey:id)?.resume()}
    }
    func taskDetails(business: Int,id: Int) async throws -> TaskDetails {try await APIReadRepository(transport:FixtureTransport(directory:directory,taskQueries:true)).taskDetails(business:business,id:id)}
    func wait(_ id: Int) async {if pending[id]==nil {await withCheckedContinuation {waiters[id]=$0}}}
    func resolve(_ id: Int,_ result: Result<TaskPage,ReadFailure>) {let c=pending.removeValue(forKey:id)!;switch result {case .success(let value):c.resume(returning:value);case .failure(let error):c.resume(throwing:error)}}
    func recorded() -> [TaskQueryFilter] {calls}
}

@MainActor func checkTaskQuery(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let transport=QueryRecordingTransport(directory),repo=APIReadRepository(transport:transport)
    let model=TaskListViewModel(repository:repo,commentSource:FixtureTaskCommentDraftSource(directory:directory))
    await model.load(business:101,epoch:10)
    let initial=model.querySelection!
    try expect(model.total==73 && model.partial && !model.showsEmpty,"Initial source list lost count/partial evidence")
    await model.applyFilter(TaskQueryFilter(status:"open",due:.today),expected:initial)
    try expect(model.appliedFilter==TaskQueryFilter(status:"open",due:.today) && model.items.map(\.id)==[3165,1101] && model.total==2 && !model.partial,"Source intersection/order was locally replaced")
    let selectedQuery=model.querySelection!
    await model.open(id:1101);let target=model.detailSelection!,before=model.items
    model.comment!.open(model.comment!.session.read!);let commentSelection=model.comment!.session.selection!;model.comment!.update("Keep own comment",commentSelection)
    model.back(expected:target)
    try expect(model.appliedFilter==TaskQueryFilter(status:"open",due:.today) && model.items==before,"Detail Back reset source filter or rows")
    await model.refreshFilter(expected:selectedQuery)
    let requests=await transport.recorded()
    try expect(requests.last==TaskQueryFilter(status:"open",due:.today).request(business:101),"Refresh lost applied source query")
    await model.open(id:1101)
    try expect(model.comment?.session.text=="Keep own comment","Same query refresh erased private own comment")
    let freshTarget=model.detailSelection!,freshQuery=model.querySelection!,readCount=await transport.recorded().count
    model.back(expected:target);await model.retryDetail(expected:target);await model.applyFilter(TaskQueryFilter(due:.overdue),expected:initial);await model.refreshFilter(expected:initial)
    let afterStale=await transport.recorded().count
    try expect(model.detailSelection==freshTarget && model.querySelection==freshQuery && afterStale==readCount,"Stale UI Back/Retry/filter/refresh entered current list")
    model.back(expected:freshTarget);await model.applyFilter(TaskQueryFilter(status:"done",due:.overdue),expected:freshQuery)
    try expect(model.showsEmpty && !model.partial && model.total==0 && model.detail==nil && model.comment?.session.available==false,"Confirmed empty query retained old detail/comment or partial state")
    await model.applyFilter(TaskQueryFilter(),expected:model.querySelection)
    try expect(model.appliedFilter==TaskQueryFilter() && model.total==73 && model.partial,"Reset did not retrieve bounded all-source window")
    let current=model.querySelection!;await model.load(business:202,epoch:11);await model.applyFilter(TaskQueryFilter(due:.overdue),expected:current)
    try expect(model.business==202 && model.appliedFilter==TaskQueryFilter(),"Old Business filter callback changed new owner")
    let control=ControlledTaskQueries(directory),races=TaskListViewModel(repository:control)
    let all=try await repo.tasks(business:101),today=try await repo.tasks(business:101,filter:TaskQueryFilter(due:.today)),overdue=try await repo.tasks(business:101,filter:TaskQueryFilter(due:.overdue)),b=try await repo.tasks(business:202)
    let start=Task {await races.load(business:101,epoch:20)};await control.wait(0);await control.resolve(0,.success(all));await start.value
    let slow=Task {await races.applyFilter(TaskQueryFilter(due:.today),expected:races.querySelection)};await control.wait(1)
    try expect(races.loading && races.items.isEmpty && !races.showsEmpty,"Pending query showed old rows or global empty")
    let quick=Task {await races.applyFilter(TaskQueryFilter(due:.overdue),expected:races.querySelection)};await control.wait(2)
    await control.resolve(2,.success(overdue));await quick.value;await control.resolve(1,.success(today));await slow.value
    try expect(races.appliedFilter.due == .overdue && races.total==66 && races.items==overdue.items,"Older query replaced current rows/count/filter")
    let partialZero=try JSONDecoder().decode(TaskPage.self,from:Data("{\"business\":101,\"items\":[],\"summary\":{\"total\":9}}".utf8))
    let refresh=Task {await races.refreshFilter(expected:races.querySelection)};await control.wait(3);await control.resolve(3,.success(partialZero));await refresh.value
    try expect(races.partial && !races.showsEmpty && races.items.isEmpty,"Partial zero was mislabeled complete empty")
    for (n,error) in [ReadFailure.denied,.unavailable].enumerated() {
        let fail=Task {await races.refreshFilter(expected:races.querySelection)};await control.wait(4+n);await control.resolve(4+n,.failure(error));await fail.value
        try expect(races.failure==error && !races.showsEmpty && races.appliedFilter.due == .overdue,"Error lost query or became empty success")
    }
    let old=Task {await races.refreshFilter(expected:races.querySelection)};await control.wait(6)
    let newOwner=Task {await races.load(business:202,epoch:21)};await control.wait(7);await control.resolve(7,.success(b));await newOwner.value;await control.resolve(6,.success(all));await old.value
    try expect(races.business==202 && races.total==71 && races.appliedFilter==TaskQueryFilter(),"Late old Business query repopulated current list")
    let oldEpoch=Task {await races.refreshFilter(expected:races.querySelection)};await control.wait(8)
    let sameBusiness=Task {await races.load(business:202,epoch:22)};await control.wait(9);await control.resolve(8,.failure(.denied));await oldEpoch.value
    try expect(races.loading && races.failure==nil && races.scopeEpoch==22,"Older same-Business epoch error affected current request")
    await control.resolve(9,.success(b));await sameBusiness.value
    let mismatch=Task {await races.applyFilter(TaskQueryFilter(status:"done"),expected:races.querySelection)};await control.wait(10)
    let wrongStatus=try await repo.tasks(business:202,filter:TaskQueryFilter(status:"open",due:.today))
    await control.resolve(10,.success(wrongStatus));await mismatch.value
    try expect(races.failure == .invalidPayload && races.items.isEmpty && !races.showsEmpty,"Wrong source status was silently locally filtered instead of rejected")
    let oldRoot=races.querySelection!
    let offTabPending=Task {await races.refreshFilter(expected:oldRoot)};await control.wait(11)
    races.reconcileCommentOwner(business:101,epoch:23)
    await races.applyFilter(TaskQueryFilter(),expected:oldRoot);await races.refreshFilter(expected:oldRoot)
    await control.resolve(11,.success(b));await offTabPending.value
    let rootCalls=await control.recorded().count
    try expect(races.business==nil && races.items.isEmpty && races.querySelection==nil && rootCalls==12,"Off-tab owner invalidation left old query controls/list response actionable")
    return count
}
