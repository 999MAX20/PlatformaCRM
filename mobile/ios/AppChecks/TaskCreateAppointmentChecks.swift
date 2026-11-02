import Foundation
import CRMCore

actor ControlledTaskAppointmentReads:AgendaRepository {
    private let fixture:APIReadRepository
    private var lists:[CheckedContinuation<AppointmentList,any Error>?]=[],details:[CheckedContinuation<AppointmentDetail,any Error>?]=[]
    private var listWait:[Int:CheckedContinuation<Void,Never>]=[:],detailWait:[Int:CheckedContinuation<Void,Never>]=[:]
    private var requests:[String]=[]
    init(_ directory:URL) {fixture=APIReadRepository(transport:FixtureTransport(directory:directory))}
    func bootstrap() async throws -> Bootstrap {throw ReadFailure.denied}
    func appointments(business:Int,day:String) async throws -> AppointmentList {let i=lists.count;requests.append("list:\(business):\(day)");return try await withCheckedThrowingContinuation {lists.append($0);listWait.removeValue(forKey:i)?.resume()}}
    func appointment(business:Int,id:Int) async throws -> AppointmentDetail {let i=details.count;requests.append("detail:\(business):\(id)");return try await withCheckedThrowingContinuation {details.append($0);detailWait.removeValue(forKey:i)?.resume()}}
    func waitList(_ i:Int) async {if lists.count<=i {await withCheckedContinuation {listWait[i]=$0}}}
    func waitDetail(_ i:Int) async {if details.count<=i {await withCheckedContinuation {detailWait[i]=$0}}}
    func resolveList(_ i:Int,_ page:AppointmentList) {lists[i]!.resume(returning:page);lists[i]=nil}
    func resolveDetail(_ i:Int,_ detail:AppointmentDetail) {details[i]!.resume(returning:detail);details[i]=nil}
    func failDetail(_ i:Int) {details[i]!.resume(throwing:ReadFailure.unavailable);details[i]=nil}
    func calls()->[String] {requests}
}
@MainActor func checkTaskCreateAppointment(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-create-appointment-cases.json"))) as! [String:Any],repo=APIReadRepository(transport:FixtureTransport(directory:directory)),context=TaskDraftContext(business:101,epoch:1),reads=ControlledTaskAppointmentReads(directory),port=ControlledTaskCreatePort(),model=TaskDraftViewModel(port:port,clients:repo,appointments:reads)
    func enter(_ m:TaskDraftViewModel) {m.bind(context);m.open(context);let q=m.session.selection!;m.update(.title,"  Visit task\n",q);m.update(.description,"  Keep notes\n",q);m.chooseDue(.setDate,input:m.inputControl);m.update(.dueAt,"2026-11-02T09:30:00+05:00",input:m.inputControl);m.chooseReminder(.setDate,input:m.inputControl);m.update(.reminderAt,"2026-11-01T14:00:00Z",input:m.inputControl)}
    enter(model)
    // Choose a Client via its own current independent profile before opening Appointment reads.
    model.openClientPicker(input:model.inputControl);let co=model.clientPickerOwner!,clients=model.clients!;await clients.submit(expected:clients.control);await clients.openClient(701,expected:clients.control);try expect(clients.session.profileSelection==nil,"Unprovided legacy Client701 became current search choice");await clients.openClient(1754,expected:clients.control);model.confirmClient(co,search:clients.control)
    try expect(model.session.values.client?.id==1754,"Independent Client not selected before Appointment")
    let original=model.session.values,input=model.inputControl!,oldEditor=model.control!;model.openAppointmentPicker(input:input);let owner=model.appointmentPickerOwner!,read=model.appointments!
    try expect(await reads.calls().isEmpty && read.day.isEmpty && !read.canRead && model.inputControl==nil && model.session.values==original,"Picker inferred date/row/read/default or overwrote input")
    model.update(.title,"overwrite",input:input);model.prepare(expected:oldEditor);model.openClientPicker(input:input);try expect(model.session.values==original && model.clientPickerOwner==nil && model.session.phase == .editing,"Old raw control or second picker bypassed exclusive owner")
    await read.read(expected:read.control);try expect(await reads.calls().isEmpty,"Empty day issued GET")
    read.updateDay("2026-10-30",expected:read.control);let listLoading=Task {await read.read(expected:read.control)};await reads.waitList(0);let pending=read.control!;await read.read(expected:pending);await read.open(501,expected:pending)
    model.closeAppointmentPicker(owner);let closed=model.control;let pageRow=(catalog["page_cases"] as! [[String:Any]])[0],page=try JSONDecoder().decode(AppointmentList.self,from:Data((pageRow["page_json"] as! String).utf8));await reads.resolveList(0,page);await listLoading.value
    model.confirmAppointment(owner,read:pending);try expect(model.control==closed && model.session.values==original && read.context==nil,"Closed picker late list/confirm changed editor")
    model.openAppointmentPicker(input:model.inputControl);let next=model.appointmentPickerOwner!;try expect(read.day.isEmpty,"Reopened picker reused implicit day")
    var li=1
    for row in catalog["page_cases"] as! [[String:Any]] {
        read.updateDay("2026-10-30",expected:read.control);let start=read.control!,loading=Task {await read.read(expected:start)};await reads.waitList(li);let pending=read.control!;let value=try JSONDecoder().decode(AppointmentList.self,from:Data((row["page_json"] as! String).utf8));await reads.resolveList(li,value);li += 1;await loading.value
        try expect(read.loaded==row["valid"] as! Bool && read.control != pending,"Scoped list metadata accepted invalid source or retained pending callback: \(row["name"]!)")
        if read.loaded {try expect(read.items.count==value.items.count && read.total==value.summary.total && read.partial==(value.summary.total>value.items.count),"Count/partial was filtered/promoted")}
    }
    let list=Task {await read.read(expected:read.control)};await reads.waitList(li);await reads.resolveList(li,page);li += 1;await list.value
    let window=read.control!;await read.open(999999,expected:window);try expect(read.selectedID==nil,"Arbitrary ID selected outside current list")
    let opening=Task {await read.open(501,expected:window)};await reads.waitDetail(0);let pendingDetail=read.control!;model.confirmAppointment(next,read:pendingDetail);try expect(model.session.values==original,"Pending detail became Appointment")
    read.backDetail(expected:pendingDetail);let afterBack=read.control!;let detailRow=(catalog["choice_cases"] as! [[String:Any]]).first {$0["name"] as? String=="different client is independent"}!,detail=try JSONDecoder().decode(AppointmentDetail.self,from:Data((detailRow["detail_json"] as! String).utf8));await reads.resolveDetail(0,detail);await opening.value
    try expect(read.control==afterBack && read.detail == nil && model.session.values==original,"Back allowed late independent detail")
    let other=Task {await read.open(501,expected:read.control)};await reads.waitDetail(1);await reads.resolveDetail(1,try await repo.appointment(business:202,id:601));await other.value;try expect(read.failure == .invalidPayload && read.choice(expected:read.control)==nil,"Foreign detail allowed selected Appointment")
    let retry=Task {await read.retryDetail(expected:read.control)};await reads.waitDetail(2);let stale=read.control!;await reads.resolveDetail(2,detail);await retry.value
    model.confirmAppointment(next,read:stale);try expect(model.session.values.appointment==nil,"Pending callback chose completed detail")
    model.confirmAppointment(next,read:read.control);let selected=model.session.values
    try expect(selected.appointment?.id==501 && selected.client==original.client && selected.title==original.title && selected.description==original.description && selected.dueDate==original.dueDate && selected.reminderDate==original.reminderDate && model.appointmentPickerOwner==nil,"Valid independent Appointment did not preserve all Client/raw fields")
    let selectedInput=model.inputControl!;model.clearAppointment(input:selectedInput);try expect(model.session.values.appointment==nil && model.session.values.client==original.client,"Unsent remove inferred Client/null-clear")
    // Re-read explicitly, then unknown fake attempt retains both choices and exact body.
    model.openAppointmentPicker(input:model.inputControl);let last=model.appointmentPickerOwner!;read.updateDay("2026-10-30",expected:read.control);let load=Task {await read.read(expected:read.control)};await reads.waitList(li);await reads.resolveList(li,page);await load.value
    let open=Task {await read.open(501,expected:read.control)};await reads.waitDetail(3);await reads.resolveDetail(3,detail);await open.value;model.confirmAppointment(last,read:read.control);model.prepare(expected:model.control);let review=model.session.review!,send=Task {await model.submit(review,expected:model.control)};await port.wait(0)
    let attempt=await port.recorded()[0],body=attempt.preparedBody();await port.loseReply(0);await send.value
    model.clearAppointment(input:selectedInput);model.openAppointmentPicker(input:selectedInput);model.discard(review.selection);model.back(review.selection);model.open(context)
    let sentCount=await port.recorded().count
    try expect(model.submission?.phase == .unknown && model.submission?.attempt.preparedBody()==body && model.session.values==review.values && model.submissionBlocked && !model.canSubmit && sentCount==1,"Unknown discarded relation/raw attempt or permitted replay")
    model.bind(TaskDraftContext(business:101,epoch:2));model.open(TaskDraftContext(business:101,epoch:2));try expect(model.submissionBlocked && model.submission==nil && model.retainedAttemptCount==1,"Epoch rekey bypassed same-Business unknown")
    let noPort=TaskDraftViewModel(appointments:repo);enter(noPort);noPort.prepare(expected:noPort.control);try expect(!noPort.canSubmit,"GET granted CREATE")
    let noRead=TaskDraftViewModel(port:port);enter(noRead);noRead.openAppointmentPicker(input:noRead.inputControl);try expect(!noRead.appointmentPickerAvailable && noRead.appointmentPickerOwner==nil,"Default constructor invented Appointment read")
    // Cancelled repository may still return: explicit cancellation keeps unavailable, no selection.
    let cancelRead=TaskAppointmentPickerViewModel(repository:reads);cancelRead.begin(context);cancelRead.updateDay("2026-10-30",expected:cancelRead.control);let cancelled=Task {await cancelRead.read(expected:cancelRead.control)};await reads.waitList(li+1);cancelled.cancel();await reads.resolveList(li+1,page);await cancelled.value;try expect(!cancelRead.loaded && cancelRead.failure == .unavailable,"Cancelled source became selectable")
    // Consecutive raw callbacks share an input visit; read/choice tickets remain strict.
    let typingReads=ControlledTaskAppointmentReads(directory),typing=TaskAppointmentPickerViewModel(repository:typingReads)
    typing.begin(context);let typingInput=typing.inputControl!,beforeTypingRead=typing.control!
    for raw in ["2","20","2026-10-30"] {typing.updateDay(raw,input:typingInput);try expect(typing.day==raw && typing.inputControl==typingInput,"Consecutive raw date event was dropped before rerender")}
    await typing.read(expected:beforeTypingRead);try expect(await typingReads.calls().isEmpty,"Raw input token relaxed stale read ticket")
    let typedLoad=Task {await typing.read(expected:typing.control)};await typingReads.waitList(0)
    typing.updateDay("overwrite",input:typingInput);try expect(typing.inputControl==nil && typing.day=="2026-10-30","Loading accepted old raw date callback")
    await typingReads.resolveList(0,page);await typedLoad.value;let afterLoadInput=typing.inputControl!
    typing.updateDay("overwrite",input:typingInput);try expect(typing.inputControl==afterLoadInput && typing.day=="2026-10-30" && afterLoadInput != typingInput,"Completed read revived old input visit")
    let typedOpen=Task {await typing.open(501,expected:typing.control)};await typingReads.waitDetail(0)
    try expect(typing.inputControl==nil,"Detail selection exposed raw day input")
    typing.backDetail(expected:typing.control);let afterDetailInput=typing.inputControl!
    typing.updateDay("overwrite",input:afterLoadInput);try expect(afterDetailInput != afterLoadInput && typing.day=="2026-10-30","Detail Back revived prior raw input visit")
    await typingReads.resolveDetail(0,detail);await typedOpen.value;try expect(typing.detail==nil && typing.inputControl==afterDetailInput,"Late detail altered raw input region")
    typing.begin(TaskDraftContext(business:101,epoch:2));typing.updateDay("overwrite",input:afterDetailInput);try expect(typing.day.isEmpty && typing.inputControl != afterDetailInput,"Old raw callback crossed picker epoch")
    return count
}
