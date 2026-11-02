import Foundation
import CRMCore

@MainActor func checkTaskListControls(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func fixture<T:Decodable>(_ name:String,_ type:T.Type) throws -> T {try JSONDecoder().decode(type,from:Data(contentsOf:directory.appendingPathComponent(name+".json")))}
    let a=try fixture("tasks-101",TaskPage.self),b=try fixture("tasks-202",TaskPage.self),detail=try fixture("task-101-1101",TaskDetails.self)
    let source=ControlledTasks(),m=TaskListViewModel(repository:source,commentSource:FixtureTaskCommentDraftSource(directory:directory))
    try expect(m.control==nil && !m.matches(nil),"Missing Task owner yielded control")
    let load=Task {await m.load(business:101,epoch:1)};await source.waitPage(0);let pending=m.control!
    m.search("pending",expected:pending);m.filterStatus("done",previous:nil,expected:pending);await m.retryList(expected:pending)
    try expect(await source.counts()==[1,0] && m.query.isEmpty && m.status==nil,"Pending callbacks repeated list or changed filters")
    await source.resolvePage(0,.success(a));await load.value;let list=m.control!
    m.search("Alpha",expected:list);m.filterStatus("open",previous:nil,expected:list);m.filterStatus("done",previous:nil,expected:list)
    try expect(m.query=="Alpha" && m.status=="open" && m.visible.map(\.id)==[1101],"Current filters failed or previous status snapshot overwrote input")
    await m.open(id:1102,expected:list);await m.open(id:999,expected:list)
    try expect(await source.counts()==[1,0] && m.selectedID==nil,"Filtered/absent row opened")
    let open=Task {await m.open(id:1101,expected:list)};await source.waitDetail(0);let card=m.control!,selection=m.detailSelection!
    m.search("old",expected:list);m.filterStatus(nil,previous:"open",expected:list);await m.retryList(expected:list);await m.open(id:1101,expected:list)
    try expect(await source.counts()==[1,1] && m.control==card && m.query=="Alpha" && m.status=="open","Old list callback altered pending card or repeated request")
    await source.resolveDetail(0,.success(detail));await open.value
    let comment=m.comment!;m.openComment(comment.session.read!);let editor=comment.session.selection!;comment.update("Keep private local comment",editor)
    m.back(expected:selection);let returned=m.control!;await m.open(id:1101,expected:list)
    try expect(await source.counts()==[1,1] && m.selectedID==nil && returned != list,"Old row callback reopened returned list")
    let reopen=Task {await m.open(id:1101,expected:returned)};await source.waitDetail(1);let newer=m.detailSelection!
    m.back(expected:selection);await m.retryDetail(expected:selection)
    try expect(await source.counts()==[1,2] && m.detailSelection==newer && m.detailLoading,"Old detail Back/retry affected reopened card")
    await source.resolveDetail(1,.success(detail));await reopen.value
    try expect(comment.session.text=="Keep private local comment" && m.query=="Alpha" && m.status=="open","Read controls erased independent local draft/filter state")
    m.back(expected:newer);let beforeRetry=m.control!;let retry=Task {await m.retryList(expected:beforeRetry)};await source.waitPage(1)
    let readsBeforeOwner=await source.counts();m.reconcileCommentOwner(business:101,epoch:2)
    try expect(await source.counts()==readsBeforeOwner && m.control==nil && m.items.isEmpty,"Same-Business epoch root issued GET or retained private list")
    await source.resolvePage(1,.success(a));await retry.value
    try expect(m.business==nil && m.items.isEmpty,"Late old epoch list resurrected data")
    let reload=Task {await m.load(business:101,epoch:2)};await source.waitPage(2);await source.resolvePage(2,.success(a));await reload.value
    let fresh=m.control!;m.search("Current",expected:fresh);m.search("old",expected:beforeRetry);m.filterStatus("done",previous:nil,expected:list);await m.retryList(expected:beforeRetry);await m.open(id:1101,expected:returned)
    try expect(await source.counts()==[3,2] && m.query=="Current" && m.status==nil && m.selectedID==nil,"Old same-Business epoch callbacks entered new list")
    let other=Task {await m.load(business:202,epoch:3)};await source.waitPage(3);await source.resolvePage(3,.success(b));await other.value
    m.search("leak",expected:fresh);await m.open(id:1201,expected:fresh);await m.retryList(expected:fresh)
    try expect(await source.counts()==[4,2] && m.business==202 && m.query.isEmpty && m.items.map(\.id)==[1201],"Old Business control changed current list/request")
    // Query-backed lists keep their exact source filter; local status guard cannot substitute one.
    let recorder=QueryRecordingTransport(directory),query=TaskListViewModel(repository:APIReadRepository(transport:recorder))
    await query.load(business:101,epoch:10);let control=query.control!,sourceSelection=query.querySelection!
    query.filterStatus("done",previous:nil,expected:control)
    try expect(query.status==nil && query.appliedFilter==TaskQueryFilter(),"Local status guard replaced source query")
    await query.applyFilter(TaskQueryFilter(status:"open",due:.today),expected:sourceSelection)
    await query.open(id:1101,expected:control);await query.retryList(expected:control)
    let requests=await recorder.recorded()
    try expect(requests.count==2 && query.items.map(\.id)==[3165,1101] && query.appliedFilter==TaskQueryFilter(status:"open",due:.today) && query.selectedID==nil,"Old list control ignored source-query generation")
    return count
}
