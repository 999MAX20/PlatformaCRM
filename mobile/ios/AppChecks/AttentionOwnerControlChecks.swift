import Foundation
import CRMCore

@MainActor func checkAttentionOwnerControls(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),source=ControlledAttention(),m=AttentionQueueViewModel(repository:source)
    let a=try await repo.actions(business:101),b=try await repo.actions(business:202),task=try await repo.taskDetails(business:101,id:1111),appointment=try await repo.appointment(business:101,id:511)
    try expect(m.control==nil && !m.matches(nil),"Missing attention owner created control")
    let load=Task {await m.load(business:101,epoch:1)};await source.wait(pages:1,details:0);let pending=m.control!
    await m.retryList(expected:pending);m.search("old",expected:pending);try expect(await source.counts()==[1,0] && m.query.isEmpty,"Pending list callbacks changed query/repeated request")
    await source.page(0,.success(a));await load.value;let list=m.control!,taskID=a.items[1].id,appointmentID=a.items[4].id
    m.search("follow-up",expected:list);await m.open(appointmentID,expected:list);await m.open(a.items[0].id,expected:list)
    try expect(await source.counts()==[1,0] && m.selectedID==nil,"Filtered/composite-colliding unsupported row opened")
    let open=Task {await m.open(taskID,expected:list)};await source.wait(pages:1,details:1);let card=m.control!
    await m.open(taskID,expected:list);await m.retryList(expected:list);m.search("old",expected:list);m.back(expected:list);await m.retryDetail(expected:card)
    try expect(await source.counts()==[1,1] && m.selectedID==taskID && m.query=="follow-up","Old list/pending target callback changed card or repeated GET")
    await source.detail(0,.failure(.denied));await open.value
    try expect(m.detail==nil && m.detailFailure == .denied,"Queue read inferred destination access")
    let retry=Task {await m.retryDetail(expected:m.control)};await source.wait(pages:1,details:2);let visit=m.control!
    m.back(expected:card);await m.retryDetail(expected:card)
    try expect(await source.counts()==[1,2] && m.control==visit,"Old retry/Back changed current same-ID visit")
    await source.detail(1,.success(.task(task)));await retry.value;m.back(expected:visit);let returned=m.control!
    await m.open(taskID,expected:list);try expect(await source.counts()==[1,2] && m.selectedID==nil,"Old row reopened returned list")
    m.search("",expected:returned);await m.open(a.items[3].id,expected:returned)
    try expect(await source.counts()==[1,2],"Legacy Lead gained Appointment target by numeric ID")
    let target=Task {await m.open(appointmentID,expected:returned)};await source.wait(pages:1,details:3);let old=m.control!
    m.reconcileOwner(business:101,epoch:2)
    try expect(await source.counts()==[1,3] && m.control==nil && m.items.isEmpty && m.detail==nil,"Same-Business root invalidation issued GET or retained target")
    await source.detail(2,.success(.appointment(appointment)));await target.value
    try expect(m.business==nil && m.detail==nil,"Late old epoch target restored private detail")
    let fresh=Task {await m.load(business:101,epoch:2)};await source.wait(pages:2,details:3);await source.page(1,.success(a));await fresh.value;let current=m.control!
    m.search("Current",expected:current);m.search("leak",expected:list);await m.retryList(expected:list);await m.open(taskID,expected:old);m.back(expected:old)
    try expect(await source.counts()==[2,3] && m.query=="Current" && m.selectedID==nil,"Old epoch callbacks entered fresh list")
    let next=Task {await m.load(business:202,epoch:3)};await source.wait(pages:3,details:3);await source.page(2,.success(b));await next.value
    m.search("old",expected:current);await m.open(b.items[0].id,expected:current);await m.retryList(expected:current)
    try expect(await source.counts()==[3,3] && m.business==202 && m.query.isEmpty && m.items.map(\.id)==b.items.map(\.id),"Old Business callback changed new scope or request")
    return count
}
