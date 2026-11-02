import Foundation
import CRMCore

actor ControlledAppointmentSlots:AppointmentSlotRepository {
    private var calls:[AppointmentSlotIntent]=[];private var pending:[Int:CheckedContinuation<AppointmentSlotRead,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    func slots(_ intent:AppointmentSlotIntent) async throws -> AppointmentSlotRead {let i=calls.count;calls.append(intent);return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ read:AppointmentSlotRead) {pending.removeValue(forKey:i)!.resume(returning:read)}
    func fail(_ i:Int,_ error:ReadFailure) {pending.removeValue(forKey:i)!.resume(throwing:error)}
    func recorded()->[AppointmentSlotIntent] {calls}
}
@MainActor func checkAppointmentSlotRead(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let encoder=JSONEncoder();encoder.outputFormatting=[.sortedKeys]
    let fixed=APIReadRepository(transport:FixtureTransport(directory:directory)),refs=APIAppointmentReferenceRepository(transport:FixtureTransport(directory:directory)),slots=ControlledAppointmentSlots(),links=AppointmentRelationsViewModel(repository:fixed,references:refs,slots:slots),parent=AgendaViewModel(repository:fixed,initialDate:Appointment.instant("2026-10-28T07:00:00Z")!,relations:links)
    await parent.start();await parent.loadDetail(id:501);let parentControl=parent.control,parentData=try encoder.encode(parent.session.detail),list=parent.session.items,selection=parent.session.selection
    await links.openReference(.service,presentation:links.presentation);let model=links.slotReads,entry=model.presentation!
    model.open(entry);try expect(model.presented && model.day.isEmpty && model.resourceMode==nil && !model.canRead,"Slot form inferred Agenda day/resource or skipped explicit choice")
    model.setDay("2026-11-02",expected:model.presentation);try expect(!model.canRead,"Date alone silently selected unspecified/linked Resource")
    model.choose(.unspecified,expected:model.presentation);let ready=model.presentation!;let first=Task {await model.submit(ready)};await slots.wait(0);let pending=model.presentation!
    model.setDay("2026-11-03",expected:pending);model.choose(.linked,expected:pending);await model.submit(pending);await model.retry(pending);model.close(ready)
    try expect(await slots.recorded().count==1 && model.loading && model.day=="2026-11-02" && model.resourceMode == .unspecified,"Pending read/input or stale close displaced selected intent")
    await slots.fail(0,.denied);await first.value;try expect(model.failure == .denied && model.read==nil && model.day=="2026-11-02","Denied read lost input or became empty candidate proof")
    let old=model.presentation!;let retry=Task {await model.retry(old)};await slots.wait(1);let active=model.presentation!;model.close(old);model.edit(old)
    let intent=(await slots.recorded())[1],bytes=Data("[{\"start_at\":\"2026-11-02T04:00:00Z\",\"end_at\":\"2026-11-02T04:45:00Z\"}]".utf8),answer=AppointmentSlotRead.decode(bytes,intent:intent)!
    await slots.resolve(1,answer);await retry.value;try expect(model.read==answer && model.presentation==active && model.failure==nil,"Manual read retry/stale callback lost current result")
    let currentParentData=try encoder.encode(parent.session.detail);try expect(parent.control==parentControl && parent.session.items==list && parent.session.selection==selection && currentParentData==parentData,"Slot read changed parent, list, day, mode or booking")
    model.edit(model.presentation);try expect(model.day=="2026-11-02" && model.resourceMode == .unspecified && model.read==nil,"Edit replaced exact explicit input")
    let late=Task {await model.submit(model.presentation)};await slots.wait(2);let leaving=model.presentation!;model.close(leaving);model.open(model.presentation);model.setDay("2026-11-03",expected:model.presentation);model.choose(.unspecified,expected:model.presentation)
    let fresh=model.presentation!;await slots.resolve(2,answer);await late.value;model.setDay("2026-11-02",expected:leaving);await model.submit(leaving)
    let callsAfterReopen=await slots.recorded();try expect(model.presentation==fresh && model.day=="2026-11-03" && model.read==nil && !model.loading && callsAfterReopen.count==3,"Late candidate data/old entry changed reopened input")
    let afterRefresh=Task {await model.submit(model.presentation)};await slots.wait(3);let oldOwner=model.presentation;await parent.retryDetail(expected:parent.control);await slots.resolve(3,AppointmentSlotRead.decode(Data("[]".utf8),intent:(await slots.recorded())[3])!);await afterRefresh.value;model.open(oldOwner)
    try expect(!model.available && model.presentation==nil && !model.presented,"Parent refresh revived stale Service slot context")
    // Linked Resource must be read independently before the candidate endpoint.
    await links.openReference(.service,presentation:links.presentation);let owner=links.request!,service=links.reference!,controlledRefs=ControlledAppointmentReferences(),controlledSlots=ControlledAppointmentSlots(),child=AppointmentSlotReadViewModel(repository:controlledSlots,references:controlledRefs)
    child.bind(service:service,owner:owner,linkedID:9001);child.open(child.presentation);child.setDay("2026-11-02",expected:child.presentation);child.choose(.linked,expected:child.presentation)
    let foreign=Task {await child.submit(child.presentation)};await controlledRefs.wait(0);let wrong=try await refs.reference(.resource,business:202,id:9002);await controlledRefs.resolve(0,wrong);await foreign.value
    let callsAfterForeign=await controlledSlots.recorded();try expect(child.failure == .invalidPayload && callsAfterForeign.isEmpty,"Foreign linked Resource reached slot endpoint")
    child.edit(child.presentation);let linked=Task {await child.submit(child.presentation)};await controlledRefs.wait(1);await controlledRefs.resolve(1,try await refs.reference(.resource,business:101,id:9001));await controlledSlots.wait(0)
    let selected=(await controlledSlots.recorded())[0];try expect(selected.resource==9001 && selected.day=="2026-11-02" && selected.request.query["exclude_appointment_id"]==nil,"Validated linked Resource lost explicit intent or inferred rescheduling")
    let previous=child.presentation;child.clear();await controlledSlots.resolve(0,AppointmentSlotRead.decode(Data("[]".utf8),intent:selected)!);await linked.value;await child.retry(previous)
    try expect(child.read==nil && child.presentation==nil && !child.loading,"Late selected-resource result revived cleared owner")
    let absent=AppointmentSlotReadViewModel(repository:nil,references:refs);absent.bind(service:service,owner:owner,linkedID:9001);absent.open(absent.presentation);try expect(!absent.available && !absent.presented,"Default composition invented independent slot port")
    return count
}
