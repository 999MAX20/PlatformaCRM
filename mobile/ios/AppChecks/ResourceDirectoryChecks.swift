import Foundation
import CRMCore

actor HeldResourceDirectory:ResourceDirectoryRepository {
    private var calls:[String]=[]
    private var windows:[Int:CheckedContinuation<ResourceDirectoryWindow,any Error>]=[:]
    private var details:[Int:CheckedContinuation<ResourceDirectoryItem,any Error>]=[:]
    private var waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    func resources(business:Int) async throws -> ResourceDirectoryWindow {let i=calls.count;calls.append("list:\(business)");return try await withCheckedThrowingContinuation {windows[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func resource(business:Int,id:Int) async throws -> ResourceDirectoryItem {let i=calls.count;calls.append("detail:\(business)/\(id)");return try await withCheckedThrowingContinuation {details[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if windows[i]==nil && details[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,window:ResourceDirectoryWindow) {windows.removeValue(forKey:i)!.resume(returning:window)}
    func resolve(_ i:Int,item:ResourceDirectoryItem) {details.removeValue(forKey:i)!.resume(returning:item)}
    func fail(_ i:Int) {windows.removeValue(forKey:i)!.resume(throwing:ReadFailure.denied)}
    func recorded()->[String] {calls}
}
@MainActor func checkResourceDirectory(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let fixed=APIReadRepository(transport:FixtureTransport(directory:directory)),reader=APIResourceDirectoryRepository(transport:FixtureResourceDirectoryTransport(directory:directory)),date=Appointment.instant("2026-10-28T07:00:00Z")!
    let a=try await reader.resources(business:101),b=try await reader.resources(business:202),changed=try await reader.resource(business:101,id:9001),zero=try await reader.resource(business:101,id:9003)
    let parent=AgendaViewModel(repository:fixed,initialDate:date,resourceRepository:reader);await parent.start();let owner=parent.resourceOwner!,held=HeldResourceDirectory(),m=ResourceDirectoryViewModel(repository:held);m.bind(owner)
    let entry=m.control!;try expect(m.open(expected:entry),"Resource window did not open explicitly")
    let initiallyRecorded=await held.recorded()
    try expect(m.selected==nil && m.detail==nil && m.choice==nil && m.window==nil && initiallyRecorded.isEmpty,"Open auto-selected/fetched or created a command choice")
    let firstPresentation=m.presentation!,first=Task {await m.reload(expected:m.control)};await held.wait(0)
    try expect(m.presentation==firstPresentation && m.loading,"List loading broke stable navigation ownership")
    try expect(m.close(expected:firstPresentation),"Current navigation Back failed during list read")
    try expect(m.open(expected:m.control),"Fresh window failed to reopen")
    let currentPresentation=m.presentation!,second=Task {await m.reload(expected:m.control)};await held.wait(1)
    await held.resolve(0,window:a);await first.value
    try expect(m.loading && m.window==nil && m.presentation==currentPresentation,"Late first list crossed reopen")
    try expect(!m.close(expected:firstPresentation) && m.presented,"Old navigation Back closed a new window")
    await held.fail(1);await second.value;try expect(!m.loading && m.failure == .denied && m.window==nil && m.choice==nil,"Denied list exposed old content or became empty success")
    try expect(await held.recorded().count==2,"List error automatically retried")
    let retry=Task {await m.reload(expected:m.control)};await held.wait(2);await held.resolve(2,window:a);await retry.value
    try expect(m.window==a && m.selected==nil && m.choice==nil && m.presentation==currentPresentation,"Manual read changed presentation or picked first Resource")
    let rowControl=m.control!,row=a.items[0],third=Task {await m.select(row,expected:rowControl)};await held.wait(3)
    try expect(m.detail==nil && m.choice==nil && m.loading,"List row was used as independent detail")
    m.backToWindow(expected:m.control);await held.resolve(3,item:changed);await third.value
    try expect(m.window==a && m.selected==nil && m.detail==nil && m.failure==nil,"Back lost list or late detail revived old selection")
    await m.select(row,expected:rowControl);try expect(await held.recorded().count==4,"Old row callback survived Back")
    let fresh=Task {await m.select(row,expected:m.control)};await held.wait(4);await held.resolve(4,item:changed);await fresh.value
    try expect(m.selected==row && m.detail==changed && m.detail != m.selected && m.choice==nil,"Changed detail was silently selected or treated as version proof")
    let chooseControl=m.control!;m.choose(expected:chooseControl)
    try expect(m.choice?.item==changed && m.choice?.listed==row && m.choice?.owner==owner && m.choice?.listVisit==rowControl.visit,"Explicit choice lost raw listed/fresh observed context")
    let chosen=m.choice;m.choose(expected:chooseControl);try expect(m.choice==chosen,"Old Choose changed current local choice")
    m.backToWindow(expected:m.control);try expect(m.choice==nil && m.window==a,"Back retained previous choice or discarded read window")
    let beforeReread=m.control!,again=Task {await m.reload(expected:m.control)};await held.wait(5);await held.resolve(5,window:a);await again.value
    await m.select(row,expected:beforeReread);await m.select(changed,expected:m.control)
    try expect(await held.recorded().count==6 && m.selected==nil,"Matching reread revived old callback or ID-only row comparison accepted changed payload")
    let late=Task {await m.select(row,expected:m.control)};await held.wait(6);let previousOwnerControl=m.control
    await parent.load(business:202);m.bind(parent.resourceOwner);await held.resolve(6,item:changed);await late.value
    try expect(m.window==nil && m.detail==nil && m.choice==nil && !m.presented,"Business switch leaked late detail/choice")
    m.choose(expected:previousOwnerControl);try expect(!m.close(expected:currentPresentation),"Old Business presentation accepted")
    m.open(expected:m.control);let next=Task {await m.reload(expected:m.control)};await held.wait(7);await held.resolve(7,window:b);await next.value
    let foreign=Task {await m.select(b.items[0],expected:m.control)};await held.wait(8);await held.resolve(8,item:changed);await foreign.value
    try expect(m.failure == .invalidPayload && m.detail==nil && m.choice==nil,"Cross-Business/id detail port result reached read choice")
    m.close(expected:m.presentation);try expect(m.window==nil && m.selected==nil && m.detail==nil && m.choice==nil,"Close retained private Resource content")
    // Real Agenda composition, independent of Calendar success and unrelated command ports.
    let independent=AgendaViewModel(repository:ServiceIndependentAgendaRepository(base:fixed),initialDate:date,resourceRepository:reader);await independent.start()
    try expect(independent.failure == .denied && independent.resourceEntry != nil,"Calendar failure parked independent source-defined Resource read")
    let rootControl=independent.control,model=independent.resources!,child=model.control
    await independent.openResources(expected:rootControl,child:child)
    try expect(model.window==a && model.presented && independent.booking==nil && independent.lifecycle==nil && independent.failure == .denied,"Read-only Resource entry created grants/booking or patched Calendar error")
    let nav=model.presentation!;await model.select(a.items[1],expected:model.control);model.choose(expected:model.control)
    try expect(model.choice?.item==zero && model.presentation==nav && !zero.isActive && zero.resourceType=="legacy/unknown" && !zero.hasKnownType,"Inactive/unknown type detail was hidden or presentation changed during explicit read choice")
    independent.closeResources(expected:nav);let oldEntry=independent.control,oldChild=model.control
    await independent.load(business:202);await independent.openResources(expected:oldEntry,child:oldChild)
    try expect(!model.presented && model.owner?.scope.business.id==202 && model.choice==nil,"Parent Business change revived old entry/choice")
    await independent.openResources(expected:independent.resourceEntry,child:model.control);let otherNav=model.presentation!;independent.closeResources(expected:nav)
    try expect(model.presented && model.window==b,"Old system Back closed current Business window")
    independent.closeResources(expected:otherNav);await independent.load(business:101);await independent.openResources(expected:independent.resourceEntry,child:model.control);let dateNav=model.presentation!
    independent.closeResources(expected:dateNav);let old=independent.control;await independent.changeDate(date.addingTimeInterval(86400),previous:date,expected:old)
    try expect(model.owner?.scope.day != owner.scope.day && model.window==nil && model.choice==nil && !model.presented,"Day owner transition retained Resource choice despite empty wire query")
    let noPort=AgendaViewModel(repository:fixed,initialDate:date);await noPort.start();try expect(noPort.resources==nil && noPort.resourceEntry==nil,"Default composition fabricated Resource source/grants")
    let shared=AgendaViewModel(repository:fixed,initialDate:date,serviceRepository:APIServiceDirectoryRepository(transport:FixtureServiceDirectoryTransport(directory:directory)),resourceRepository:reader);await shared.start()
    let services=shared.services!,resources=shared.resources!,serviceEntry=shared.serviceEntry!,serviceChild=services.control
    await shared.openResources(expected:shared.resourceEntry,child:resources.control);let firstResourceNav=resources.presentation!
    try expect(resources.presented && !services.presented && shared.serviceEntry==nil,"Resource presentation admitted overlapping Service route")
    await shared.openServices(expected:serviceEntry,child:serviceChild);try expect(!services.presented && resources.presented,"Old Service root callback opened over Resource")
    shared.closeResources(expected:firstResourceNav);let resourceEntry=shared.resourceEntry!,resourceChild=resources.control
    await shared.openServices(expected:shared.serviceEntry,child:services.control);let serviceNav=services.presentation!
    try expect(services.presented && !resources.presented && shared.resourceEntry==nil,"Service presentation admitted overlapping Resource route")
    await shared.openResources(expected:resourceEntry,child:resourceChild);try expect(!resources.presented && services.presented,"Old Resource entry opened over Service")
    shared.closeServices(expected:serviceNav);await shared.openResources(expected:shared.resourceEntry,child:resources.control);shared.closeResources(expected:firstResourceNav)
    try expect(resources.presented && !services.presented,"Old Resource navigation Back survived peer Service round trip")
    await shared.loadDetail(id:501);try expect(resources.owner==nil && services.owner==nil && resources.window==nil && services.window==nil && resources.choice==nil && services.choice==nil,"Appointment transition retained a directory owner/private result")
    shared.closeDetail();try expect(shared.resourceEntry != nil && shared.serviceEntry != nil && resources.window==nil && services.window==nil,"Closing Appointment did not rebind fresh independent directory entries")
    return count
}
