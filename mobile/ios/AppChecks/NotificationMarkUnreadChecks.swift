import Foundation
import CRMCore

private actor ControlledUnreadMarker:SyntheticNotificationMarkUnreadPort {
    let grants=[SyntheticNotificationMarkUnreadGrant(business:101,notification:2102,actor:9001,update:true)]
    private var pending:CheckedContinuation<SyntheticNotificationMarkUnreadOutcome,Never>?
    private var waiter:CheckedContinuation<Void,Never>?
    private var count=0
    func execute(_ attempt:NotificationMarkUnreadAttempt) async throws -> SyntheticNotificationMarkUnreadOutcome {count += 1;return await withCheckedContinuation {pending=$0;waiter?.resume();waiter=nil}}
    func wait() async {if pending==nil {await withCheckedContinuation {waiter=$0}}}
    func resolve(_ value:SyntheticNotificationMarkUnreadOutcome) {pending!.resume(returning:value);pending=nil}
    func calls()->Int {count}
}
private actor UnreadPeerReadMarker:SyntheticNotificationMarkReadPort {
    let grants=[SyntheticNotificationMarkReadGrant(business:101,notification:2102,actor:9001,update:true)]
    private var count=0
    func execute(_ attempt:NotificationMarkReadAttempt) async throws -> SyntheticNotificationMarkReadOutcome {count += 1;return .unknown}
    func calls()->Int {count}
}
@MainActor func checkNotificationMarkUnread(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let source=ControlledNotifications(),port=ControlledUnreadMarker(),readPort=UnreadPeerReadMarker(),parent=NotificationCenterViewModel(repository:source,markReadSubmission:readPort,markUnreadSubmission:port)
    let page=try JSONDecoder().decode(NotificationPage.self,from:Data(contentsOf:directory.appendingPathComponent("notifications-101.json")))
    let load=Task {await parent.load(business:101,epoch:1)};await source.waitPage(0);await source.resolvePage(0,.success(page));await load.value
    parent.query="legacy";parent.open(id:2102,expected:parent.control);let m=parent.markUnread,s=m.read!,original=parent.items,total=parent.total
    let defaultModel=NotificationMarkUnreadViewModel();defaultModel.bind(s);try expect(!defaultModel.canPrepare,"Read alone granted unread command")
    m.prepare(s);let old=m.review!;m.back(old);m.prepare(s);let current=m.review!;await m.submit(old)
    try expect(await port.calls()==0 && old != current,"Stale unread review executed")
    let peerSource=parent.markRead.read!;parent.markRead.prepare(peerSource);let peerReview=parent.markRead.review!
    let submit=Task {await m.submit(current)};await port.wait();await m.submit(current);m.back(current);await parent.markRead.submit(peerReview)
    try expect(await port.calls()==1 && m.submission?.phase == .pending && m.review==current,"Pending unread lost input or repeated")
    try expect(await readPort.calls()==0 && parent.markRead.blocked && parent.markRead.review==nil,"Unread failed to invalidate prepared/read peer")
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("notification-mark-unread.json"))) as! [String:Any]
    let reply=try JSONDecoder().decode(NotificationMarkUnreadReply.self,from:JSONSerialization.data(withJSONObject:(catalog["validation_cases"] as! [[String:Any]])[0]["reply"]!))
    await port.resolve(.response(status:200,reply:reply));await submit.value
    try expect(m.submission?.phase == .confirmed && parent.items==original && parent.total==total && parent.selected?.read_at==s.notification.read_at,"Fake unread changed marker/list/count")
    m.acknowledge(s,attemptID:99);try expect(m.blocked,"Wrong unread ack consumed attempt")
    m.acknowledge(s,attemptID:1);try expect(m.canPrepare && m.review==nil && m.retainedAttemptCount==1 && parent.markRead.canPrepare,"Unread ack failed fresh review or lost ledger")
    await parent.markRead.submit(peerReview);try expect(await readPort.calls()==0,"Old peer review revived after unread ack")
    m.prepare(s);let rejected=m.review!,rejectTask=Task {await m.submit(rejected)};await port.wait();await port.resolve(.rejectedWithoutWrite);await rejectTask.value
    try expect(m.submission?.phase == .rejected && !m.canPrepare,"No-write permitted automatic repeat")
    m.acknowledge(s,attemptID:2);m.prepare(s);let unknown=m.review!,late=Task {await m.submit(unknown)};await port.wait()
    parent.close(expected:parent.control);try expect(m.read==nil && m.retainedAttemptCount==3,"Card Back erased unread attempt")
    parent.reconcileOwner(business:101,epoch:2);let reload=Task {await parent.load(business:101,epoch:2)};await source.waitPage(1);await source.resolvePage(1,.success(page));await reload.value
    parent.open(id:2102,expected:parent.control);let fresh=m.read!
    await port.resolve(.unknown);await late.value
    try expect(m.blocked && m.submission==nil && fresh.context.epoch==2 && !m.canPrepare && parent.markRead.blocked,"Unread reread/epoch lost quarantine or blocked only own action")
    m.acknowledge(fresh,attemptID:3);await m.submit(unknown);try expect(await port.calls()==3 && m.blocked,"Unread unknown acknowledged or repeated")
    parent.beginRoute(expected:parent.control);parent.editRoute("/app/calendar/501",expected:parent.routeControl);parent.reviewRoute(expected:parent.routeControl)
    try expect(m.read==nil && m.retainedAttemptCount==3,"Route hid/lost unread ledger")
    parent.backRoute(expected:parent.routeControl);parent.backRoute(expected:parent.routeControl)
    try expect(m.blocked && parent.markRead.blocked && parent.query.isEmpty,"Route return cleared marker quarantine")
    let counts=await source.counts();try expect(counts==[2,0] && parent.items==original,"Unread issued reads or mutated source")
    // Reverse direction: old read unknown must block a distinct unread review.
    let reverseRepo=ControlledNotifications(),reverseRead=UnreadPeerReadMarker(),reverseUnread=ControlledUnreadMarker(),reverse=NotificationCenterViewModel(repository:reverseRepo,markReadSubmission:reverseRead,markUnreadSubmission:reverseUnread)
    let rl=Task {await reverse.load(business:101,epoch:1)};await reverseRepo.waitPage(0);await reverseRepo.resolvePage(0,.success(page));await rl.value;reverse.open(id:2102,expected:reverse.control)
    let us=reverse.markUnread.read!;reverse.markUnread.prepare(us);let ur=reverse.markUnread.review!,rs=reverse.markRead.read!;reverse.markRead.prepare(rs);await reverse.markRead.submit(reverse.markRead.review!);await reverse.markUnread.submit(ur)
    try expect(await reverseUnread.calls()==0 && reverse.markUnread.blocked && reverse.markUnread.review==nil && !reverse.markUnread.canPrepare,"Read unknown did not guard unread symmetrically")
    return count
}
