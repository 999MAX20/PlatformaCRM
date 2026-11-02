import Foundation
import CRMCore

@MainActor func checkInboxMessageStates(directory:URL) async throws -> Int {
    struct Catalog:Decodable {struct Row:Decodable {let name:String;let response:InboxThread};let cases:[Row]}
    let catalog=try JSONDecoder().decode(Catalog.self,from:Data(contentsOf:directory.appendingPathComponent("message-source-states.json")))
    func thread(_ name:String)->InboxThread {catalog.cases.first {$0.name==name}!.response}
    let page=try JSONDecoder().decode(InboxList.self,from:Data(contentsOf:directory.appendingPathComponent("inbox-101.json"))),source=ControlledInbox(),m=InboxViewModel(repository:source)
    var count=0
    func expect(_ v:Bool,_ message:String) throws {guard v else {throw ViewModelCheckFailure(message:message)};count += 1}
    let load=Task {await m.load(business:101,epoch:1)};await source.waitPage(0);await source.resolvePage(0,.success(page));await load.value
    m.query="Alpha";m.unreadOnly=true
    let open=Task {await m.open(id:901)};await source.waitThread(0);await source.resolveThread(0,.success(thread("sent")));await open.value
    try expect(m.thread?.messages[0].sourceState == .sent && m.thread?.messages[1].sourceState == .sent,"Fresh thread source statuses not visible independently")
    let first=m.threadSelection,refresh=Task {await m.retryThread(expected:first)};await source.waitThread(1)
    try expect(m.thread==nil && m.threadLoading,"Pending reread displayed previous sent state")
    await source.resolveThread(1,.success(thread("missing")));await refresh.value
    try expect(m.thread?.messages[0].sourceState == .unknown,"Missing fresh source status restored cached sent value")
    let failed=Task {await m.retryThread(expected:m.threadSelection)};await source.waitThread(2);await source.resolveThread(2,.success(thread("failed")));await failed.value
    try expect(m.thread?.messages[0].sourceState == .failed && m.query=="Alpha" && m.unreadOnly,"Source failed status was hidden/retried or lost local list filter")
    let denied=Task {await m.retryThread(expected:m.threadSelection)};await source.waitThread(3);await source.resolveThread(3,.failure(.denied));await denied.value
    try expect(m.thread==nil && m.threadFailure == .denied,"Denied thread retained previous status")
    let leaving=Task {await m.retryThread(expected:m.threadSelection)};await source.waitThread(4);m.back();await source.resolveThread(4,.success(thread("sent")));await leaving.value
    try expect(m.thread==nil && m.selectedID==nil,"Late status resurrected closed thread")
    let reopen=Task {await m.open(id:901)};await source.waitThread(5);m.reconcileHandoffOwner(business:101,epoch:2);await source.resolveThread(5,.success(thread("failed")));await reopen.value
    try expect(m.thread==nil && m.business==nil && m.reply.session.context==nil,"Same Business new epoch exposed old message state/form")
    try expect(await source.counts()==[1,6],"Reading source status triggered an extra request or resend")
    return count
}
