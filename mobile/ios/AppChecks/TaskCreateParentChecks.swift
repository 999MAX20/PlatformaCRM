import Foundation
import CRMCore

actor ControlledTaskParentReads:TaskReadRepository {
    private var lists:[CheckedContinuation<TaskPage,any Error>?]=[],details:[CheckedContinuation<TaskDetails,any Error>?]=[]
    private var listWait:[Int:CheckedContinuation<Void,Never>]=[:],detailWait:[Int:CheckedContinuation<Void,Never>]=[:]
    private var requests:[String]=[]
    func tasks(business:Int) async throws -> TaskPage {let i=lists.count;requests.append("list:\(business)");return try await withCheckedThrowingContinuation {lists.append($0);listWait.removeValue(forKey:i)?.resume()}}
    func taskDetails(business:Int,id:Int) async throws -> TaskDetails {let i=details.count;requests.append("detail:\(business):\(id)");return try await withCheckedThrowingContinuation {details.append($0);detailWait.removeValue(forKey:i)?.resume()}}
    func waitList(_ i:Int) async {if lists.count<=i {await withCheckedContinuation {listWait[i]=$0}}}
    func waitDetail(_ i:Int) async {if details.count<=i {await withCheckedContinuation {detailWait[i]=$0}}}
    func resolveList(_ i:Int,_ value:TaskPage) {lists[i]!.resume(returning:value);lists[i]=nil}
    func resolveDetail(_ i:Int,_ value:TaskDetails) {details[i]!.resume(returning:value);details[i]=nil}
    func failDetail(_ i:Int,_ failure:ReadFailure) {details[i]!.resume(throwing:failure);details[i]=nil}
    func calls()->[String] {requests}
}
@MainActor func checkTaskCreateParent(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-create-parent-cases.json"))) as! [String:Any],repo=APIReadRepository(transport:FixtureTransport(directory:directory)),context=TaskDraftContext(business:101,epoch:1),reads=ControlledTaskParentReads(),port=ControlledTaskCreatePort(),model=TaskDraftViewModel(port:port,clients:repo,appointments:repo,parents:reads)
    func enter(_ m:TaskDraftViewModel) {m.bind(context);m.open(context);m.update(.title,"  Independent child task\n",input:m.inputControl);m.update(.description,"  Keep exact child notes\n",input:m.inputControl);m.chooseDue(.setDate,input:m.inputControl);m.update(.dueAt,"2026-11-02T09:30:00+05:00",input:m.inputControl);m.chooseReminder(.setDate,input:m.inputControl);m.update(.reminderAt,"2026-11-01T14:00:00Z",input:m.inputControl)}
    enter(model)
    model.openClientPicker(input:model.inputControl);let clientOwner=model.clientPickerOwner!,clients=model.clients!;await clients.submit(expected:clients.control);await clients.openClient(1754,expected:clients.control);model.confirmClient(clientOwner,search:clients.control)
    model.openAppointmentPicker(input:model.inputControl);let appointmentOwner=model.appointmentPickerOwner!,appointments=model.appointments!;appointments.updateDay("2026-10-28",expected:appointments.control);await appointments.read(expected:appointments.control);await appointments.open(501,expected:appointments.control);model.confirmAppointment(appointmentOwner,read:appointments.control)
    try expect(model.session.values.client?.id==1754 && model.session.values.appointment?.id==501,"Preconditions require actual current independent Client and Appointment reads")
    let original=model.session.values,input=model.inputControl!,editor=model.control!;model.openParentPicker(input:input);let oldOwner=model.parentPickerOwner!,read=model.parents!
    try expect(await reads.calls().isEmpty && read.items.isEmpty && !read.loaded && model.inputControl==nil && model.session.values.parentTask==nil,"Parent picker automatically read/selected/inferred fields")
    model.update(.title,"overwrite",input:input);model.prepare(expected:editor);model.openClientPicker(input:input);model.openAppointmentPicker(input:input);try expect(model.session.values==original && model.clientPickerOwner==nil && model.appointmentPickerOwner==nil && model.session.phase == .editing,"Stale raw control or parallel picker bypassed current Parent owner")
    let first=Task {await read.read(expected:read.control)};await reads.waitList(0);let pending=read.control!;await read.read(expected:pending);await read.open(1101,expected:pending);model.closeParentPicker(oldOwner)
    let closed=model.control,page=try await repo.tasks(business:101);await reads.resolveList(0,page);await first.value;model.confirmParent(oldOwner,read:pending);try expect(model.control==closed && model.session.values==original && read.context==nil,"Late closed Parent list/old callback mutated composer")
    model.openParentPicker(input:model.inputControl);let owner=model.parentPickerOwner!;var li=1
    for row in catalog["page_cases"] as! [[String:Any]] {
        let start=read.control!,loading=Task {await read.read(expected:start)};await reads.waitList(li);let pending=read.control!;let value=try JSONDecoder().decode(TaskPage.self,from:Data((row["page_json"] as! String).utf8));await reads.resolveList(li,value);li += 1;await loading.value
        try expect(read.loaded==row["valid"] as! Bool && read.control != pending,"Invalid Parent window or pending-to-ready ownership: \(row["name"]!)")
        if read.loaded {try expect(read.items==value.items && read.total==value.summary.total && read.partial==(value.summary.total>value.items.count),"Parent window was locally filtered/completeness invented")}
    }
    let listing=Task {await read.read(expected:read.control)};await reads.waitList(li);await reads.resolveList(li,page);li += 1;await listing.value
    let current=read.control!;await read.open(999999,expected:current);try expect(read.selectedID==nil,"Unprovided Parent ID selected")
    let opening=Task {await read.open(1101,expected:current)};await reads.waitDetail(0);let waiting=read.control!;model.confirmParent(owner,read:waiting);try expect(model.session.values==original,"Pending Parent detail chosen")
    read.backDetail(expected:waiting);let back=read.control!,detail=try await repo.taskDetails(business:101,id:1101);await reads.resolveDetail(0,detail);await opening.value
    try expect(read.control==back && read.detail==nil && read.loaded && model.session.values==original,"Back accepted late parent detail or lost supplied window")
    let other=Task {await read.open(1101,expected:read.control)};await reads.waitDetail(1);await reads.resolveDetail(1,try await repo.taskDetails(business:202,id:1201));await other.value;try expect(read.failure == .invalidPayload && read.choice(expected:read.control)==nil,"Foreign parent detail became a relation")
    let retry=Task {await read.retryDetail(expected:read.control)};await reads.waitDetail(2);let stale=read.control!;await reads.failDetail(2,.denied);await retry.value;try expect(read.failure == .denied && read.choice(expected:read.control)==nil,"Denied Parent read became eligible")
    let again=Task {await read.retryDetail(expected:read.control)};await reads.waitDetail(3);let pendingAgain=read.control!;await reads.resolveDetail(3,detail);await again.value
    model.confirmParent(owner,read:stale);model.confirmParent(owner,read:pendingAgain);try expect(model.session.values.parentTask==nil,"Former pending/denied controls adopted ready Parent")
    model.confirmParent(owner,read:read.control);let chosen=model.session.values
    try expect(chosen.parentTask?.id==1101 && chosen.client==original.client && chosen.appointment==original.appointment && chosen.title==original.title && chosen.description==original.description && chosen.dueDate==original.dueDate && chosen.reminderDate==original.reminderDate && model.parentPickerOwner==nil,"Parent selected/inferred another field or retained active picker")
    let oldInput=model.inputControl!;model.clearParent(input:oldInput);try expect(model.session.values.parentTask==nil && model.session.values.client==original.client && model.session.values.appointment==original.appointment,"Removing unsent Parent lost independent relations")
    model.openParentPicker(input:model.inputControl);let finalOwner=model.parentPickerOwner!;let load=Task {await read.read(expected:read.control)};await reads.waitList(li);await reads.resolveList(li,page);li += 1;await load.value
    let open=Task {await read.open(1101,expected:read.control)};await reads.waitDetail(4);await reads.resolveDetail(4,detail);await open.value;model.confirmParent(finalOwner,read:read.control);model.prepare(expected:model.control)
    let review=model.session.review!,sending=Task {await model.submit(review,expected:model.control)};await port.wait(0);let attempt=await port.recorded()[0],body=attempt.preparedBody();await port.loseReply(0);await sending.value
    model.clearParent(input:oldInput);model.openParentPicker(input:oldInput);model.discard(review.selection);model.back(review.selection);model.open(context);let calls=await port.recorded().count
    try expect(calls==1 && model.submission?.phase == .unknown && model.submission?.attempt.review==review && model.submission?.attempt.preparedBody()==body && model.session.values==review.values && model.submissionBlocked && !model.canSubmit,"Unknown Parent lost all raw/relations/attempt or replayed")
    model.bind(TaskDraftContext(business:101,epoch:2));model.open(TaskDraftContext(business:101,epoch:2));try expect(model.submissionBlocked && model.submission==nil && model.retainedAttemptCount==1,"Epoch bypassed same-Business unknown parent guard")
    let clean=TaskDraftViewModel(parents:reads);enter(clean);clean.openParentPicker(input:clean.inputControl);let cleanOwner=clean.parentPickerOwner!,child=clean.parents!,request=Task {await child.read(expected:child.control)};await reads.waitList(li);await reads.resolveList(li,page);li += 1;await request.value;let pendingDetail=Task {await child.open(1101,expected:child.control)};await reads.waitDetail(5);let old=child.control;clean.bind(TaskDraftContext(business:202,epoch:2));await reads.resolveDetail(5,detail);await pendingDetail.value;clean.confirmParent(cleanOwner,read:old);try expect(clean.session.context?.business==202 && clean.session.values.parentTask==nil && child.context==nil,"Business switch accepted late Parent")
    let noGrant=TaskDraftViewModel(parents:repo);enter(noGrant);noGrant.openParentPicker(input:noGrant.inputControl);let noGrantOwner=noGrant.parentPickerOwner!,finder=noGrant.parents!;await finder.read(expected:finder.control);await finder.open(1101,expected:finder.control);noGrant.confirmParent(noGrantOwner,read:finder.control);noGrant.prepare(expected:noGrant.control);try expect(noGrant.session.review?.preview.parentTaskID==1101 && !noGrant.canSubmit,"Parent GET granted CREATE")
    let absent=TaskDraftViewModel(port:port);enter(absent);absent.openParentPicker(input:absent.inputControl);try expect(!absent.parentPickerAvailable && absent.parentPickerOwner==nil,"Default constructor invented parent reader")
    let cancel=TaskParentPickerViewModel(repository:reads);cancel.begin(context);let cancelled=Task {await cancel.read(expected:cancel.control)};await reads.waitList(li);cancelled.cancel();await reads.resolveList(li,page);await cancelled.value;try expect(!cancel.loaded && cancel.failure == .unavailable,"Cancelled parent source became selectable")
    return count
}
