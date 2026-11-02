import Foundation
import CRMCore

private actor RouteUnknownMarker:SyntheticNotificationMarkReadPort {
    let grants=[SyntheticNotificationMarkReadGrant(business:101,notification:2101,actor:9001,update:true)]
    private var count=0
    func execute(_ attempt:NotificationMarkReadAttempt) async throws -> SyntheticNotificationMarkReadOutcome {count += 1;return .unknown}
    func calls()->Int {count}
}

@MainActor func checkNotificationRoute(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let page=try JSONDecoder().decode(NotificationPage.self,from:Data(contentsOf:directory.appendingPathComponent("notifications-101.json")))
    let source=ControlledNotifications(),model=NotificationCenterViewModel(repository:source)
    model.beginRoute(expected:nil);try expect(!model.routeEditorActive,"Route opened without owner")
    let load=Task {await model.load(business:101,epoch:1)};await source.waitPage(0);await source.resolvePage(0,.success(page));await load.value
    model.query="Alpha";model.open(id:2101,expected:model.control);let card=model.control
    model.beginRoute(expected:card);let editor=model.routeControl
    try expect(editor != nil && model.routeInput.isEmpty && model.routeCandidate==nil,"Route editor failed or inferred input authority")
    model.editRoute("/app/calendar/501",expected:editor);model.reviewRoute(expected:editor);let review=model.routeControl
    try expect(model.routeReviewing && model.routeCorroborated && model.routeCandidate?.appointmentID==501,"Independent source did not corroborate")
    model.editRoute("/app/calendar/502",expected:editor);model.backRoute(expected:editor)
    try expect(model.routeReviewing && model.routeInput=="/app/calendar/501","Old editor changed review")
    await model.openTarget(expected:model.control);let requests=await source.counts()
    try expect(requests==[1,0] && !model.targetActive && model.selected?.unread==true,"Route review fetched or changed read state")
    model.backRoute(expected:review);let resumed=model.routeControl
    try expect(!model.routeReviewing && model.routeEditorActive && model.routeInput=="/app/calendar/501","Review Back lost exact input")
    model.backRoute(expected:review);model.editRoute("bad",expected:editor)
    try expect(model.routeInput=="/app/calendar/501" && model.routeEditorActive,"Old visit controls affected resumed editor")
    model.editRoute(" /app/calendar/501",expected:resumed);model.reviewRoute(expected:resumed)
    try expect(model.routeReviewing && model.routeCandidate==nil && !model.routeCorroborated && model.routeInput.hasPrefix(" "),"Unsupported raw normalized or lost")
    model.backRoute(expected:model.routeControl);model.editRoute("/app/calendar/502",expected:model.routeControl);model.reviewRoute(expected:model.routeControl)
    try expect(model.routeCandidate != nil && !model.routeCorroborated,"Different existing ID manufactured source authority")
    model.backRoute(expected:model.routeControl);let exit=model.routeControl;model.backRoute(expected:exit)
    try expect(!model.routeEditorActive && model.routeInput=="/app/calendar/502" && model.selectedID==2101,"Editor Back lost card or raw")
    await model.openTarget(expected:card);let staleCounts=await source.counts();try expect(staleCounts==[1,0],"Old card target callback survived local editor visit")
    model.beginRoute(expected:model.control);try expect(model.routeInput=="/app/calendar/502" && model.routeControl != exit,"Editor reopen reused visit or lost raw")
    let old=model.routeControl;model.close(expected:model.control)
    try expect(model.routeInput.isEmpty && !model.routeEditorActive && model.query=="Alpha","Card close lost filters or retained foreign input")
    model.open(id:2101,expected:model.control);model.beginRoute(expected:model.control);model.editRoute("old",expected:old)
    try expect(model.routeInput.isEmpty,"Old same-ID card editor revived input")
    let epochControl=model.routeControl;model.reconcileOwner(business:101,epoch:2);model.editRoute("stale",expected:epochControl);model.reviewRoute(expected:epochControl)
    try expect(model.business==nil && model.routeInput.isEmpty && model.routeControl==nil,"Owner epoch leaked input")
    let again=Task {await model.load(business:101,epoch:2)};await source.waitPage(1);await source.resolvePage(1,.success(page));await again.value
    model.open(id:2102,expected:model.control);model.beginRoute(expected:model.control);model.editRoute("/app/calendar/501",expected:model.routeControl);model.reviewRoute(expected:model.routeControl)
    try expect(!model.routeCorroborated && model.selected?.appointment_id==501,"Legacy Lead ID remapped to Appointment")
    let staleRead=model.routeControl
    let reread=Task {await model.load(business:101,epoch:2)};await source.waitPage(2)
    model.backRoute(expected:staleRead);await source.resolvePage(2,.failure(.denied));await reread.value
    try expect(!model.routeEditorActive && model.routeInput.isEmpty && model.failure == .denied,"Failed reread retained prior route authority")
    let finalCounts=await source.counts();try expect(finalCounts==[3,0] && model.markRead.retainedAttemptCount==0,"Local route made a request/marker attempt")
    let markerRepo=ControlledNotifications(),port=RouteUnknownMarker(),marked=NotificationCenterViewModel(repository:markerRepo,markReadSubmission:port)
    let markerLoad=Task {await marked.load(business:101,epoch:1)};await markerRepo.waitPage(0);await markerRepo.resolvePage(0,.success(page));await markerLoad.value
    marked.open(id:2101,expected:marked.control);let markerSource=marked.markRead.read!;marked.markRead.prepare(markerSource);let markerReview=marked.markRead.review!
    await marked.markRead.submit(markerReview);try expect(marked.markRead.submission?.phase == .unknown,"Marker test did not quarantine")
    marked.beginRoute(expected:marked.control);marked.editRoute("/app/calendar/501",expected:marked.routeControl);marked.reviewRoute(expected:marked.routeControl)
    try expect(marked.markRead.read==nil && marked.markRead.retainedAttemptCount==1 && marked.routeCorroborated,"Route discarded unknown attempt")
    marked.backRoute(expected:marked.routeControl);marked.backRoute(expected:marked.routeControl)
    try expect(marked.markRead.blocked && !marked.markRead.canPrepare && marked.markRead.retainedAttemptCount==1,"Route match cleared marker quarantine")
    await marked.markRead.submit(markerReview);let calls=await port.calls();try expect(calls==1 && marked.selected?.unread==true,"Route replayed marker or mutated unread")
    return count
}
