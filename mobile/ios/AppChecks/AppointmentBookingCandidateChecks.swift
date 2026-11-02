import Foundation
import CRMCore

@MainActor func checkAppointmentBookingCandidate(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),refs=APIAppointmentReferenceRepository(transport:FixtureTransport(directory:directory)),slots=APIAppointmentSlotRepository(transport:FixtureAppointmentSlotTransport(directory:directory)),fixture=FixtureAppointmentBookingPort(directory:directory),date=Appointment.instant("2026-10-28T07:00:00Z")!
    let links=AppointmentRelationsViewModel(repository:repo,references:refs,slots:slots),m=AgendaViewModel(repository:repo,initialDate:date,relations:links,lifecyclePort:FixtureAppointmentTerminalPort(directory:directory),bookingPort:fixture,bookingClients:repo,bookingReferences:refs)
    await m.start();await m.loadDetail(id:501);let b=m.booking!,s=links.slotReads,original=m.session.detail!,list=m.session.items,scope=m.session.selection
    await links.openReference(.service,presentation:links.presentation);s.open(s.presentation);let input=s.inputControl!,oldAction=s.presentation!
    s.setDayInput("2026-11-0",input:input);s.setDayInput("2026-11-02",input:input);s.choose(.linked,expected:oldAction)
    try expect(s.day=="2026-11-02" && s.inputControl==input && s.resourceMode==nil,"Slot date continuous input was lost or old action accepted after typing")
    s.choose(.unspecified,expected:s.presentation);await s.submit(s.presentation);s.selectCandidate(0,expected:s.presentation);let review=s.review!,bridge=m.bookingCandidateControl(parent:m.control,related:links.presentation,slot:s.presentation,review:review)!
    try expect(review.context.resource==nil && bridge.time.rawStart==review.candidate.startAt && b.resource==nil,"Unspecified read created a Resource/default time choice")
    let peer=m.lifecycle!;peer.prepare(.confirm,expected:peer.control);peer.back(expected:peer.control);m.useBookingCandidate(bridge)
    try expect(!b.presented && b.rawStart.isEmpty,"Old candidate callback survived peer A-B-A")
    let current=m.bookingCandidateControl(parent:m.control,related:links.presentation,slot:s.presentation,review:review)!,oldSlot=s.presentation!
    m.useBookingCandidate(current)
    try expect(b.presented && b.rawStart=="2026-11-02T04:15:00Z" && b.client==nil && b.service==nil && b.resource==nil && !b.canReview && b.retainedAttemptCount==0 && links.selected==nil && s.context==nil,"Transfer copied choices/default resource/grant/end_at or did not close only related read")
    s.setDayInput("stale",input:input);s.backToCandidates(oldSlot);m.useBookingCandidate(current)
    try expect(s.day.isEmpty && b.rawStart==current.time.rawStart && b.retainedAttemptCount==0,"Old slot/input/bridge callback changed new booking window")
    try expect(m.session.detail?.appointment.start_at==original.appointment.start_at && m.session.detail?.appointment.id==original.appointment.id && m.session.items==list && m.session.selection==scope,"Candidate transfer mutated original Appointment/list/day/scope")
    await b.load(.client,expected:b.control);await b.load(.service,expected:b.control)
    try expect(b.resource==nil && !b.canReview,"Candidate/Service read inferred create resource=null")
    b.chooseClear(expected:b.control);b.prepareReview(expected:b.control);let raw=b.review!.input.start.raw;await b.submit(expected:b.control)
    try expect(b.submission?.phase == .unknown && b.submission?.attempt.review.input.start.raw==raw && b.retainedAttemptCount==1,"Fixed fixture fabricated success for new candidate or lost original raw input")
    let retained=b.submission!.attempt,body=try JSONSerialization.jsonObject(with:retained.body) as! [String:Any]
    try expect(Set(body.keys)==["business","client","service","start_at","resource"] && body["resource"] is NSNull && body["start_at"] as? String==raw,"Candidate copied end_at/context/grant/version/extra fields into body")
    await m.retryDetail(expected:m.control);await links.openReference(.service,presentation:links.presentation);s.open(s.presentation);s.setDayInput("2026-11-02",input:s.inputControl);s.choose(.unspecified,expected:s.presentation);await s.submit(s.presentation);s.selectCandidate(0,expected:s.presentation)
    try expect(b.blocked && m.bookingCandidateControl(parent:m.control,related:links.presentation,slot:s.presentation,review:s.review!)==nil,"Matching parent/slot reread released unknown create")
    m.useBookingCandidate(current);await m.load(business:202);await m.load(business:101);await m.loadDetail(id:501)
    try expect(b.blocked && !b.canOpen && b.retainedAttemptCount==1,"Business return released/repeated candidate-origin unknown")
    let nextLinks=AppointmentRelationsViewModel(repository:repo,references:refs,slots:slots),n=AgendaViewModel(repository:repo,initialDate:date,relations:nextLinks,bookingPort:fixture,bookingClients:repo,bookingReferences:refs)
    await n.start();await n.loadDetail(id:501);let target=n.booking!,read=nextLinks.slotReads
    @MainActor func select(_ index:Int=0,mode:AppointmentSlotResourceMode = .linked) async {
        if nextLinks.selected != nil {nextLinks.back(presentation:nextLinks.presentation)}
        await nextLinks.openReference(.service,presentation:nextLinks.presentation);read.open(read.presentation);read.setDayInput("2026-11-02",input:read.inputControl);read.choose(mode,expected:read.presentation);await read.submit(read.presentation);read.selectCandidate(index,expected:read.presentation)
    }
    @MainActor func control()->AppointmentBookingCandidateControl? {guard let review=read.review else {return nil};return n.bookingCandidateControl(parent:n.control,related:nextLinks.presentation,slot:read.presentation,review:review)}
    await select();let beforeBack=control()!;read.backToCandidates(read.presentation);read.selectCandidate(0,expected:read.presentation);n.useBookingCandidate(beforeBack)
    try expect(!target.presented && target.rawStart.isEmpty,"Candidate Back/reselect restored old transfer controls")
    let beforeRefresh=control()!,same=read.context!;await read.refresh(read.presentation);read.selectCandidate(0,expected:read.presentation);n.useBookingCandidate(beforeRefresh)
    try expect(read.context==same && !target.presented,"Byte-matching reread revived stale transfer")
    let beforeRelated=control()!;await select();n.useBookingCandidate(beforeRelated)
    try expect(!target.presented,"Related Service A-B-A restored old bridge")
    let beforeParent=control()!;await n.retryDetail(expected:n.control);await select();n.useBookingCandidate(beforeParent)
    try expect(!target.presented,"Parent reread admitted old bridge")
    let beforeBusiness=control()!;await n.load(business:202);await n.load(business:101);await n.loadDetail(id:501);await select();n.useBookingCandidate(beforeBusiness)
    try expect(!target.presented && target.retainedAttemptCount==0,"Business round trip restored old candidate action")
    let fresh=control()!;try expect(fresh.review.context.resource?.id==9001,"Linked read context lost provided Resource")
    n.useBookingCandidate(fresh)
    try expect(target.presented && target.resource==nil && target.client==nil && target.service==nil && !target.canReview,"Linked candidate automatically selected Resource/Client/Service or grant")
    // Preserve already explicit same-source choices while replacing only time via a new action.
    await target.load(.client,expected:target.control);await target.load(.service,expected:target.control);target.chooseClear(expected:target.control);let chosenClient=target.client,chosenService=target.service
    n.backBooking(entry:n.bookingEntryControl,child:target.control);await select(1,mode:.unspecified);let preserved=control()!;n.useBookingCandidate(preserved)
    try expect(target.rawStart==preserved.time.rawStart && target.client==chosenClient && target.service==chosenService && target.resource == .clear && target.canReview,"Explicit time transfer overwrote retained same-source choices")
    let noLinks=AppointmentRelationsViewModel(repository:repo,references:refs,slots:slots),noGrant=AgendaViewModel(repository:repo,initialDate:date,relations:noLinks)
    await noGrant.start();await noGrant.loadDetail(id:501);await noLinks.openReference(.service,presentation:noLinks.presentation);let noRead=noLinks.slotReads;noRead.open(noRead.presentation);noRead.setDayInput("2026-11-02",input:noRead.inputControl);noRead.choose(.unspecified,expected:noRead.presentation);await noRead.submit(noRead.presentation);noRead.selectCandidate(0,expected:noRead.presentation)
    try expect(noGrant.bookingCandidateControl(parent:noGrant.control,related:noLinks.presentation,slot:noRead.presentation,review:noRead.review!)==nil && noGrant.booking==nil,"GET-only candidate created CREATE admission")
    return count
}
