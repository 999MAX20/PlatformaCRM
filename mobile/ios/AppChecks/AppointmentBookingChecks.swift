import Foundation
import CRMCore

private actor BookingReadTrace:ReadTransport {
    let fixture:FixtureTransport;private var calls:[ReadRequest]=[]
    init(_ directory:URL) {fixture=FixtureTransport(directory:directory)}
    func get(_ request:ReadRequest) async throws -> ReadResponse {calls.append(request);return try await fixture.get(request)}
    func requests()->[ReadRequest] {calls}
}
private actor HeldBookingPort:SyntheticAppointmentBookingPort {
    nonisolated let grants:[SyntheticAppointmentBookingGrant];private var pending:[CheckedContinuation<SyntheticAppointmentBookingOutcome,Never>]=[];private var attempts:[AppointmentBookingAttempt]=[]
    init(_ grants:[SyntheticAppointmentBookingGrant]) {self.grants=grants}
    func execute(_ a:AppointmentBookingAttempt) async throws -> SyntheticAppointmentBookingOutcome {attempts.append(a);return await withCheckedContinuation {pending.append($0)}}
    func wait(_ n:Int) async {while pending.count<n {await Task.yield()}}
    func resolve(_ n:Int,_ value:SyntheticAppointmentBookingOutcome) {pending[n].resume(returning:value)}
    func calls()->[AppointmentBookingAttempt] {attempts}
}
private actor HeldBookingReferences:AppointmentReferenceRepository {
    private var pending:[CheckedContinuation<AppointmentReferenceDetail,any Error>]=[]
    func reference(_ kind:AppointmentReferenceKind,business:Int,id:Int) async throws -> AppointmentReferenceDetail {try await withCheckedThrowingContinuation {pending.append($0)}}
    func wait(_ n:Int) async {while pending.count<n {await Task.yield()}}
    func resolve(_ n:Int,_ value:Result<AppointmentReferenceDetail,any Error>) {pending[n].resume(with:value)}
}
private actor HeldBookingClients:ClientProfileRepository {
    private var pending:[CheckedContinuation<ClientProfile,any Error>]=[]
    func clientProfile(business:Int,id:Int) async throws -> ClientProfile {try await withCheckedThrowingContinuation {pending.append($0)}}
    func wait(_ n:Int) async {while pending.count<n {await Task.yield()}}
    func resolve(_ n:Int,_ value:ClientProfile) {pending[n].resume(returning:value)}
}
@MainActor func checkAppointmentBooking(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let trace=BookingReadTrace(directory),repo=APIReadRepository(transport:trace),refs=APIAppointmentReferenceRepository(transport:trace),fixture=FixtureAppointmentBookingPort(directory:directory),date=Appointment.instant("2026-10-28T07:00:00Z")!
    let m=AgendaViewModel(repository:repo,initialDate:date,lifecyclePort:FixtureAppointmentTerminalPort(directory:directory),bookingPort:fixture,bookingClients:repo,bookingReferences:refs)
    await m.start();await m.loadDetail(id:501);let model=m.booking!,entry=m.bookingEntryControl!,initial=model.control!,parent=m.control,original=m.session.detail!,list=m.session.items
    try expect(model.rawStart.isEmpty && model.client==nil && model.service==nil && model.resource==nil && model.canOpen && !model.canReview,"Booking copied original date/client/service/resource choices or derived CREATE from GET")
    m.openBooking(entry:entry,child:initial);let input=model.inputControl!,before=model.control!
    try expect(model.presented && m.lifecycleEntryControl==nil,"Booking form did not isolate lifecycle entry")
    model.setStart("2026-10-29T05:00:00",expected:input);model.setStart("2026-10-29T05:00:00Z",expected:input);model.chooseClear(expected:before)
    try expect(model.rawStart=="2026-10-29T05:00:00Z" && model.timeValid && model.resource==nil && !model.canReview,"Continuous input rejected keystrokes, stale resource button applied or reads skipped")
    await model.load(.client,expected:model.control);await model.load(.service,expected:model.control);await model.load(.resource,expected:model.control)
    let calls=await trace.requests()
    try expect(model.client?.id==7001 && model.service?.id==8001 && model.resource?.id==9001 && calls.contains { $0.path=="/api/mobile/v1/clients/7001/" && $0.query==["business":"101"] } && calls.contains {$0.path=="/api/services/8001/" && $0.query.isEmpty} && calls.contains {$0.path=="/api/resources/9001/" && $0.query.isEmpty},"Booking choices skipped exact existing scoped Client/Service/Resource GET")
    model.chooseClear(expected:model.control);model.prepareReview(expected:model.control);let review=model.review!
    model.setStart("stale",expected:input);m.backBooking(entry:m.bookingEntryControl,child:model.control)
    try expect(model.review==nil && model.presented && model.rawStart==review.input.start.raw && model.client==review.input.client && model.service==review.input.service && model.resource==review.input.resource,"Review Back lost read choices/raw time or allowed stale field callback")
    m.backBooking(entry:m.bookingEntryControl,child:model.control);m.openBooking(entry:entry,child:model.control)
    try expect(!model.presented && model.rawStart==review.input.start.raw,"Old parent entry reopened closed booking or Back lost same-window input")
    m.openBooking(entry:m.bookingEntryControl,child:model.control);model.setStart("stale",expected:input);model.prepareReview(expected:model.control);m.closeDetail(expected:parent)
    try expect(m.session.detailSelection?.id==501 && model.review?.input==review.input,"Old parent Back closed new booking window")
    await model.submit(expected:model.control)
    try expect(model.submission?.phase == .acceptedFixture && model.submission?.receipt?.appointment.id==1501 && model.retainedAttemptCount==1,"Explicit local booking201 fixture failed")
    try expect(m.session.detail?.appointment.id==original.appointment.id && m.session.detail?.appointment.start_at==original.appointment.start_at && m.session.items.map(\.id)==list.map(\.id) && m.session.items.map(\.status)==list.map(\.status),"Fake booking changed GET/list/calendar or inserted returned id")
    m.acknowledgeBooking(entry:m.bookingEntryControl,child:model.control,record:model.submission!)
    try expect(model.used && !model.canOpen && m.bookingEntryControl==nil && m.lifecycleEntryControl != nil,"Accepted local create was silently repeatable or peer entry did not restore")
    await m.loadDetail(id:502);m.openBooking(entry:m.bookingEntryControl,child:model.control);model.setStart("2026-10-29T05:00:00Z",expected:model.inputControl);await model.load(.client,expected:model.control);await model.load(.service,expected:model.control);model.chooseClear(expected:model.control);model.prepareReview(expected:model.control);await model.submit(expected:model.control)
    try expect(model.submission?.phase == .rejectedFixture,"Explicit known no-write create rejection misclassified")
    m.acknowledgeBooking(entry:m.bookingEntryControl,child:model.control,record:model.submission!)
    try expect(model.editing && model.rawStart=="2026-10-29T05:00:00Z" && model.client?.id==7002 && model.service?.id==8001 && model.resource == .clear && model.canReview,"Known no-write rejection discarded input/choices or invented retry")
    let held=HeldBookingPort(fixture.grants),n=AgendaViewModel(repository:repo,initialDate:date,bookingPort:held,bookingClients:repo,bookingReferences:refs)
    await n.start();await n.loadDetail(id:501);let child=n.booking!;n.openBooking(entry:n.bookingEntryControl,child:child.control);child.setStart("2026-10-29T05:00:00Z",expected:child.inputControl);await child.load(.client,expected:child.control);await child.load(.service,expected:child.control);child.chooseClear(expected:child.control);child.prepareReview(expected:child.control)
    let old=child.control!,pending=Task {await child.submit(expected:old)};await held.wait(1);await child.submit(expected:old);child.prepareReview(expected:child.control);n.backBooking(entry:n.bookingEntryControl,child:child.control)
    try expect(child.blocked && child.retainedAttemptCount==1,"Pending booking admitted repeated submit/Back")
    await n.loadDetail(id:502);await held.resolve(0,.unknown);await pending.value
    try expect(n.session.detail?.appointment.id==502 && child.submission==nil && child.canOpen,"Late501 unknown poisoned502 or exposed another input")
    await n.load(business:202);await n.loadDetail(id:601);n.openBooking(entry:n.bookingEntryControl,child:child.control);child.setStart("2026-10-29T05:00:00Z",expected:child.inputControl);await child.load(.service,expected:child.control)
    try expect(child.failure == .invalidPayload && child.service==nil && !child.canReview && child.rawStart=="2026-10-29T05:00:00Z","Cross-Business linked Service admitted or read error lost input/fell back")
    await n.load(business:101);await n.loadDetail(id:501);await child.submit(expected:old)
    let heldCount=await held.calls().count
    try expect(child.blocked && child.submission==nil && !child.canOpen && child.retainedAttemptCount==1 && heldCount==1,"Matching reread/Business return resolved/repeated unknown create")
    let attempt=await held.calls()[0],body=try JSONSerialization.jsonObject(with:attempt.body) as! [String:Any]
    try expect(attempt.review.input.start.raw=="2026-10-29T05:00:00Z" && Set(body.keys)==["business","client","service","start_at","resource"] && body["resource"] is NSNull,"Unknown did not retain original exact input/body/attempt")
    let heldRefs=HeldBookingReferences(),late=AgendaViewModel(repository:repo,initialDate:date,bookingPort:fixture,bookingClients:repo,bookingReferences:heldRefs)
    await late.start();await late.loadDetail(id:501);let l=late.booking!;late.openBooking(entry:late.bookingEntryControl,child:l.control);l.setStart("2026-10-29T05:00:00Z",expected:l.inputControl)
    let read=Task {await l.load(.service,expected:l.control)};await heldRefs.wait(1);late.backBooking(entry:late.bookingEntryControl,child:l.control);late.openBooking(entry:late.bookingEntryControl,child:l.control)
    await heldRefs.resolve(0,.success(try await refs.reference(.service,business:101,id:8001)));await read.value
    try expect(l.service==nil && l.loading==nil && l.rawStart=="2026-10-29T05:00:00Z","Late GET selected Service in reopened form or lost raw input")
    let denied=Task {await l.load(.service,expected:l.control)};await heldRefs.wait(2);await heldRefs.resolve(1,.failure(ReadFailure.denied));await denied.value
    try expect(l.failure == .denied && l.service==nil && !l.canReview && l.rawStart=="2026-10-29T05:00:00Z","Failed Service read became choice/default or destroyed input")
    let heldClients=HeldBookingClients(),clientLate=AgendaViewModel(repository:repo,initialDate:date,bookingPort:fixture,bookingClients:heldClients,bookingReferences:refs)
    await clientLate.start();await clientLate.loadDetail(id:501);let c=clientLate.booking!;clientLate.openBooking(entry:clientLate.bookingEntryControl,child:c.control);let oldRead=Task {await c.load(.client,expected:c.control)};await heldClients.wait(1);await clientLate.loadDetail(id:502);await heldClients.resolve(0,try await repo.clientProfile(business:101,id:7001));await oldRead.value
    try expect(c.source?.clientID==7002 && c.client==nil && !c.presented,"Late Client GET crossed selected entry ownership")
    let cancelledPort=HeldBookingPort(fixture.grants),cancelled=AgendaViewModel(repository:repo,initialDate:date,bookingPort:cancelledPort,bookingClients:repo,bookingReferences:refs)
    await cancelled.start();await cancelled.loadDetail(id:501);let cancel=cancelled.booking!;cancelled.openBooking(entry:cancelled.bookingEntryControl,child:cancel.control);cancel.setStart("2026-10-29T05:00:00Z",expected:cancel.inputControl);await cancel.load(.client,expected:cancel.control);await cancel.load(.service,expected:cancel.control);cancel.chooseClear(expected:cancel.control);cancel.prepareReview(expected:cancel.control)
    let task=Task {await cancel.submit(expected:cancel.control)};await cancelledPort.wait(1);let sent=await cancelledPort.calls();task.cancel();await cancelledPort.resolve(0,try await fixture.execute(sent[0]));await task.value
    try expect(cancel.submission?.phase == .unknown && cancel.submission?.attempt==sent[0],"Cancellation accepted late create201 or discarded input/attempt")
    let noGrant=AgendaViewModel(repository:repo,initialDate:date);await noGrant.start();await noGrant.loadDetail(id:501);try expect(noGrant.booking==nil && noGrant.bookingEntryControl==nil,"GET-only/default Agenda created fake CREATE context")
    return count
}
