import Foundation
import CRMCore

actor ControlledAppointmentReferences:AppointmentReferenceRepository {
    private var calls:[(AppointmentReferenceKind,Int,Int)]=[]
    private var pending:[Int:CheckedContinuation<AppointmentReferenceDetail,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    func reference(_ kind:AppointmentReferenceKind,business:Int,id:Int) async throws -> AppointmentReferenceDetail {let i=calls.count;calls.append((kind,business,id));return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ value:AppointmentReferenceDetail) {pending.removeValue(forKey:i)!.resume(returning:value)}
    func fail(_ i:Int,_ value:ReadFailure) {pending.removeValue(forKey:i)!.resume(throwing:value)}
    func count()->Int {calls.count}
}
actor AppointmentReferenceTransport:ReadTransport {
    private let fixture:FixtureTransport,variant:Data?
    private var calls:[ReadRequest]=[]
    init(_ directory:URL,variant:Data?=nil) {fixture=FixtureTransport(directory:directory);self.variant=variant}
    func get(_ q:ReadRequest) async throws -> ReadResponse {calls.append(q);if q.path=="/api/mobile/v1/appointments/601/",q.query["business"]=="202",let variant {return ReadResponse(status:200,data:variant)};return try await fixture.get(q)}
    func recorded()->[ReadRequest] {calls}
}
@MainActor func checkAppointmentReferenceDetails(directory:URL) async throws -> Int {
    var count=0
    func expect(_ v:Bool,_ message:String) throws {guard v else {throw ViewModelCheckFailure(message:message)};count += 1}
    func bytes(_ detail:AppointmentDetail?)->Data? {let encoder=JSONEncoder();encoder.outputFormatting=[.sortedKeys];return detail.flatMap {try? encoder.encode($0)}}
    let fixed=APIReadRepository(transport:FixtureTransport(directory:directory)),port=ControlledAppointmentReferences(),links=AppointmentRelationsViewModel(repository:fixed,references:port),m=AgendaViewModel(repository:fixed,initialDate:Appointment.instant("2026-10-28T07:00:00Z")!,relations:links)
    await m.start();await m.loadDetail(id:501);let parent=m.session.detailSelection!,scope=m.session.selection,body=bytes(m.session.detail),entry=links.presentation!
    let plain=AppointmentRelationsViewModel(repository:fixed);plain.bind(m.session.detail!,request:parent);await plain.openReference(.service,presentation:plain.presentation);try expect(!plain.referenceAvailable(.service) && plain.selected==nil,"Missing independent read port became a GET/default")
    let source=APIAppointmentReferenceRepository(transport:FixtureTransport(directory:directory)),service=try await source.reference(.service,business:101,id:8001),resource=try await source.reference(.resource,business:101,id:9001)
    let first=Task {await links.openReference(.service,presentation:entry)};await port.wait(0);let pending=links.presentation!
    await links.openReference(.resource,presentation:entry);await links.openClient(presentation:pending);await links.retry(presentation:pending);links.back(presentation:entry)
    try expect(await port.count()==1 && links.loading && links.selected == .service(8001),"Pending reference repeated/switched or old parent Back displaced it")
    await port.fail(0,.denied);await first.value;try expect(links.failure == .denied && links.reference==nil,"Denied reference became empty/active/stale data")
    let retry=Task {await links.retry(presentation:links.presentation)};await port.wait(1);let fresh=links.presentation!;links.back(presentation:pending);await links.retry(presentation:pending);await port.resolve(1,service);await retry.value
    try expect(await port.count()==2 && links.presentation==fresh && links.reference==service && m.session.selection==scope && bytes(m.session.detail)==body,"Reference retry lost ownership or changed parent/selection")
    links.back(presentation:fresh);let leaving=Task {await links.openReference(.service,presentation:links.presentation)};await port.wait(2);let old=links.presentation!;links.back(presentation:old)
    let next=Task {await links.openReference(.resource,presentation:links.presentation)};await port.wait(3);let current=links.presentation!;links.back(presentation:old);await links.retry(presentation:old);await port.resolve(3,resource);await next.value;await port.fail(2,.unavailable);await leaving.value
    try expect(await port.count()==4 && links.presentation==current && links.reference==resource && links.failure==nil && links.request==parent,"Late Service result/old Back changed current Resource")
    links.back(presentation:current);let late=Task {await links.openReference(.service,presentation:links.presentation)};await port.wait(4);let oldParent=links.presentation!;await m.retryDetail(expected:m.control);await port.resolve(4,service);await late.value
    await links.openReference(.service,presentation:oldParent);links.back(presentation:oldParent);await links.retry(presentation:oldParent)
    try expect(await port.count()==5 && links.request != parent && links.selected==nil && links.reference==nil,"Parent refresh accepted old reference data/control")
    let transport=AppointmentReferenceTransport(directory),repo=APIReadRepository(transport:transport),actual=AppointmentRelationsViewModel(repository:repo,references:APIAppointmentReferenceRepository(transport:transport)),owner=AgendaViewModel(repository:repo,initialDate:Appointment.instant("2026-10-28T07:00:00Z")!,relations:actual)
    await owner.start();await owner.loadDetail(id:501);let oldBody=bytes(owner.session.detail),list=owner.session.items,day=owner.session.selection;let before=await transport.recorded().count
    await actual.openReference(.service,presentation:actual.presentation);let shown=actual.reference!;let reads=await transport.recorded();try expect(shown.id==8001 && reads.count==before+1 && reads.last==ReadRequest(path:"/api/services/8001/") && bytes(owner.session.detail)==oldBody && owner.session.items==list && owner.session.selection==day,"Reference GET invented query or changed Appointment/list/day")
    actual.back(presentation:actual.presentation);await owner.load(business:202);await owner.loadDetail(id:601);await actual.openReference(.service,presentation:actual.presentation)
    try expect(actual.reference==nil && actual.failure == .invalidPayload,"Unchanged legacy202 shared id falsely became selected Business")
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-reference-read-cases.json"))) as! [String:Any],variant=Data((catalog["parent_202_variant_json"] as! String).utf8),vt=AppointmentReferenceTransport(directory,variant:variant),vr=APIReadRepository(transport:vt),vlinks=AppointmentRelationsViewModel(repository:vr,references:APIAppointmentReferenceRepository(transport:vt)),vm=AgendaViewModel(repository:vr,initialDate:Appointment.instant("2026-10-28T07:00:00Z")!,relations:vlinks)
    await vm.start();await vm.load(business:202);await vm.loadDetail(id:601);await vlinks.openReference(.service,presentation:vlinks.presentation)
    try expect(vlinks.reference?.business==202 && vlinks.reference?.id==8002 && vlinks.reference?.isActive==false && vlinks.reference?.activityCopyKey=="referenceInactive","Fresh explicit202 variant/inactive object was defaulted or treated as unreadable")
    return count
}
