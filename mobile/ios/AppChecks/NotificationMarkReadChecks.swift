import Foundation
import CRMCore

private actor ControlledNotificationMarkRead:SyntheticNotificationMarkReadPort {
    let grants=[SyntheticNotificationMarkReadGrant(business:101,notification:2101,actor:9001,update:true)]
    private var pending:[Int:CheckedContinuation<SyntheticNotificationMarkReadOutcome,any Error>]=[:]
    private var waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    private var attempts:[NotificationMarkReadAttempt]=[]
    func execute(_ attempt:NotificationMarkReadAttempt) async throws -> SyntheticNotificationMarkReadOutcome {
        let i=attempts.count;attempts.append(attempt)
        return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}
    }
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ outcome:SyntheticNotificationMarkReadOutcome) {pending.removeValue(forKey:i)!.resume(returning:outcome)}
    func fail(_ i:Int) {pending.removeValue(forKey:i)!.resume(throwing:ReadFailure.unavailable)}
    func calls()->Int {attempts.count}
}

@MainActor func checkNotificationMarkRead(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let data=try Data(contentsOf:directory.appendingPathComponent("notification-mark-read.json")),catalog=try JSONSerialization.jsonObject(with:data) as! [String:Any]
    let cases=catalog["validation_cases"] as! [[String:Any]],reply=try JSONDecoder().decode(NotificationMarkReadReply.self,from:JSONSerialization.data(withJSONObject:cases[0]["reply"]!))
    let readRepository=ControlledNotifications(),port=ControlledNotificationMarkRead(),parent=NotificationCenterViewModel(repository:readRepository,markReadSubmission:port)
    let load=Task {await parent.load(business:101,epoch:1)};await readRepository.waitPage(0)
    let page=try JSONDecoder().decode(NotificationPage.self,from:Data(contentsOf:directory.appendingPathComponent("notifications-101.json")))
    await readRepository.resolvePage(0,.success(page));await load.value
    parent.open(id:2101,expected:parent.control);let model=parent.markRead,source=model.read!,markers=parent.items.map(\.read_at),total=parent.total
    let ordinary=NotificationMarkReadViewModel();ordinary.bind(source);try expect(!ordinary.canPrepare,"Read source granted UPDATE without explicit port")
    model.prepare(source);let stale=model.review!;model.back(stale);model.prepare(source);let review=model.review!
    await model.submit(stale);try expect(await port.calls()==0 && review != stale,"Old review executed or fresh review reused identity")
    let send=Task {await model.submit(review)};await port.wait(0);await model.submit(review);model.back(review)
    try expect(await port.calls()==1 && model.submission?.phase == .pending && model.review==review,"Pending doubleclick/back repeated or discarded input")
    await port.resolve(0,.response(status:200,reply:reply));await send.value
    let readsAfterConfirmation=await readRepository.counts()
    try expect(model.submission?.phase == .confirmed && parent.items.map(\.read_at)==markers && parent.total==total && parent.selected?.unread==true && readsAfterConfirmation==[1,0],"Fake confirmation changed marker/count or issued read")
    model.acknowledge(source,attemptID:999);try expect(model.blocked,"Old acknowledgement removed current attempt")
    model.acknowledge(source,attemptID:1);try expect(model.canPrepare && model.review==nil && model.retainedAttemptCount==1,"Terminal ack did not retain history/fresh review")
    model.prepare(source);let rejected=model.review!,sending=Task {await model.submit(rejected)};await port.wait(1)
    await port.resolve(1,.rejectedWithoutWrite);await sending.value
    try expect(model.submission?.phase == .rejected && !model.canPrepare,"No-write enabled replay without acknowledgement")
    model.acknowledge(source,attemptID:2);model.prepare(source);let unknownReview=model.review!,late=Task {await model.submit(unknownReview)};await port.wait(2)
    parent.close(expected:parent.control);try expect(model.read==nil && model.submission==nil && model.retainedAttemptCount==3,"Back erased attempt or exposed hidden input")
    parent.reconcileOwner(business:101,epoch:2)
    let reload=Task {await parent.load(business:101,epoch:2)};await readRepository.waitPage(1);await readRepository.resolvePage(1,.success(page));await reload.value
    parent.open(id:2101,expected:parent.control);let newer=model.read!
    await port.resolve(2,.response(status:200,reply:reply));await late.value
    try expect(newer.context.epoch==2 && model.blocked && model.submission==nil && !model.canPrepare,"Late old epoch result appeared or reread enabled replay")
    await model.submit(unknownReview);model.acknowledge(source,attemptID:3)
    try expect(await port.calls()==3 && model.blocked && parent.items.map(\.read_at)==markers,"Old callback or matching reread cleared quarantine")
    // Error/cancel after dispatch retain unknown; pre-dispatch cancellation issues no call.
    let failure=NotificationMarkReadViewModel(port:port);failure.bind(source);failure.prepare(source)
    let failureReview=failure.review!,errorTask=Task {await failure.submit(failureReview)};await port.wait(3);await port.fail(3);await errorTask.value
    try expect(failure.submission?.phase == .unknown && failure.retainedAttemptCount==1,"Thrown error lost source/attempt")
    let cancellation=NotificationMarkReadViewModel(port:port);cancellation.bind(source);cancellation.prepare(source)
    let cancelReview=cancellation.review!,cancelTask=Task {await cancellation.submit(cancelReview)};await port.wait(4);cancelTask.cancel();await port.resolve(4,.response(status:200,reply:reply));await cancelTask.value
    try expect(cancellation.submission?.phase == .unknown && !cancellation.canPrepare,"Cancelled confirmation accepted or replayed")
    let never=NotificationMarkReadViewModel(port:port);never.bind(source);never.prepare(source);let neverReview=never.review!
    let cancelledBefore=Task {withUnsafeCurrentTask {$0?.cancel()};await never.submit(neverReview)};await cancelledBefore.value
    try expect(await port.calls()==5 && never.retainedAttemptCount==0 && never.review==neverReview,"Cancelled queued task dispatched")
    return count
}
