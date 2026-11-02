import Foundation
import CRMCore

actor ControlledTaskClientReads:ClientSearchRepository {
    private let fixture:APIReadRepository;private var pending:[Int:CheckedContinuation<ClientProfile,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:];private var reads:[(Int,Int)]=[]
    init(_ directory:URL) {fixture=APIReadRepository(transport:FixtureTransport(directory:directory))}
    func searchClients(business:Int,search:String) async throws -> ClientList {try await fixture.searchClients(business:business,search:search)}
    func clientProfile(business:Int,id:Int) async throws -> ClientProfile {let i=reads.count;reads.append((business,id));return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ profile:ClientProfile) {pending.removeValue(forKey:i)!.resume(returning:profile)}
    func fail(_ i:Int,_ error:ReadFailure) {pending.removeValue(forKey:i)!.resume(throwing:error)}
    func count()->Int {reads.count}
}
@MainActor func checkTaskCreateClient(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let source=APIReadRepository(transport:FixtureTransport(directory:directory)),port=ControlledTaskCreatePort(),reads=ControlledTaskClientReads(directory),context=TaskDraftContext(business:101,epoch:1),model=TaskDraftViewModel(port:port,clients:reads)
    func enter(_ model:TaskDraftViewModel) {model.bind(context);model.open(context);let s=model.session.selection!;model.update(.title,"  Client task\n",s);model.update(.description,"  Raw Client notes\n",s);model.chooseDue(.setDate,input:model.inputControl);model.update(.dueAt,"2026-11-02T09:30:00+05:00",input:model.inputControl);model.chooseReminder(.setDate,input:model.inputControl);model.update(.reminderAt,"2026-11-01T14:00:00Z",input:model.inputControl)}
    enter(model);let original=model.session.values,oldInput=model.inputControl!,oldControl=model.control!;model.openClientPicker(input:oldInput);let owner=model.clientPickerOwner!,search=model.clients!
    try expect(model.inputControl==nil && model.matchesClientPicker(owner) && search.session.items.isEmpty && !search.session.loading && model.session.values.client==nil,"Picker inferred a Client/read/permission or left parent input active")
    model.update(.title,"overwrite",input:oldInput);model.prepare(expected:oldControl);model.chooseDue(.omit,input:oldInput);try expect(model.session.values==original && model.session.phase == .editing,"Old editor callback changed raw input while Client picker owned it")
    await search.submit(expected:search.control);let list=search.control!,id=search.session.items.first!.id
    model.confirmClient(owner,search:list);try expect(model.session.values.client==nil,"List row became chosen Client without independent profile")
    let loading=Task {await search.openClient(id,expected:list)};await reads.wait(0);let pending=search.control!;model.confirmClient(owner,search:pending);model.closeClientPicker(owner);let afterClose=model.control!
    let profile=try await source.clientProfile(business:101,id:id);await reads.resolve(0,profile);await loading.value;model.confirmClient(owner,search:pending)
    try expect(model.session.values==original && model.clientPickerOwner==nil && model.control==afterClose,"Late profile/old choose revived closed picker or mutated draft")
    model.openClientPicker(input:model.inputControl);let active=model.clientPickerOwner!;await search.submit(expected:search.control);let freshList=search.control!;let reading=Task {await search.openClient(id,expected:freshList)};await reads.wait(1);await reads.resolve(1,profile);await reading.value;let ready=search.control!
    model.confirmClient(owner,search:ready);try expect(model.session.values.client==nil,"Old Task picker owner adopted current independent profile")
    model.confirmClient(active,search:freshList);try expect(model.session.values.client==nil,"Old list ticket adopted later profile read")
    model.confirmClient(active,search:ready);let chosen=model.session.values.client!,current=model.control!
    try expect(chosen.id==id && chosen.business==101 && model.clientPickerOwner==nil && model.session.values.title==original.title && model.session.values.description==original.description && model.session.values.dueDate==original.dueDate && model.session.values.reminderDate==original.reminderDate,"Client selection lost raw fields or retained lookup/private profile state")
    model.prepare(expected:current);let review=model.session.review!,sending=Task {await model.submit(review,expected:model.control)};await port.wait(0);let attempt=(await port.recorded())[0],body=try JSONSerialization.jsonObject(with:attempt.preparedBody()!) as! [String:Any]
    model.openClientPicker(input:oldInput);model.clearClient(input:oldInput);await model.submit(review)
    try expect(await port.recorded().count==1 && body["client"] as? Int==id && body["client_id"]==nil && model.session.values.client==chosen,"Pending create changed/repeated Client or prepared GET alias")
    let v=review.preview,receipt=WorkTask(id:88001,title:v.title,status:"open",priority:v.priority,due_at:v.dueAt,business:101,updated_at:"2026-10-30T12:00:00Z",description:v.description,created_by:9001,created_at:"2026-10-30T12:00:00Z")
    await port.resolve(0,.response(status:201,task:receipt,reminderAt:v.reminderAt,clientRead:.client(id+1)));await sending.value
    try expect(model.submission?.phase == .unknown && model.submission?.attempt.review==review && model.submission?.attempt.preparedBody()==attempt.preparedBody() && model.session.values.client==chosen,"Mismatched Client201 became success or lost unknown input/attempt")
    model.close(expected:model.returnControl);model.open(context);model.clearClient(input:model.inputControl);model.openClientPicker(input:model.inputControl);await model.submit(review)
    try expect(await port.recorded().count==1 && model.submissionBlocked && model.clientPickerOwner==nil && model.session.values.client==chosen,"Unknown Client replayed through close/reopen/local clear")
    model.bind(TaskDraftContext(business:101,epoch:2));model.open(TaskDraftContext(business:101,epoch:2));try expect(model.submissionBlocked && model.retainedAttemptCount==1 && model.submission==nil,"New epoch bypassed Business unknown guard or exposed old actor receipt")
    // Foreign independently returned profile never becomes a same-Business choice.
    let fresh=TaskDraftViewModel(port:ControlledTaskCreatePort(),clients:reads);enter(fresh);fresh.openClientPicker(input:fresh.inputControl);let foreignOwner=fresh.clientPickerOwner!,finder=fresh.clients!;await finder.submit(expected:finder.control);let request=Task {await finder.openClient(id,expected:finder.control)};await reads.wait(2);await reads.resolve(2,try await source.clientProfile(business:202,id:801));await request.value;fresh.confirmClient(foreignOwner,search:finder.control)
    try expect(fresh.session.values.client==nil && finder.profile.failure == .invalidPayload,"Foreign profile became selected Client")
    let oldOwner=fresh.clientPickerOwner!,late=Task {await finder.retryProfile(expected:finder.control)};await reads.wait(3);fresh.bind(TaskDraftContext(business:202,epoch:3));await reads.resolve(3,profile);await late.value;fresh.confirmClient(oldOwner,search:finder.control)
    try expect(fresh.clientPickerOwner==nil && fresh.session.values.client==nil && fresh.session.context?.business==202,"Business change accepted late Client read or old picker callback")
    let noGrant=TaskDraftViewModel(clients:source);enter(noGrant);noGrant.openClientPicker(input:noGrant.inputControl);let ng=noGrant.clientPickerOwner!,lookup=noGrant.clients!;await lookup.submit(expected:lookup.control);await lookup.openClient(id,expected:lookup.control);noGrant.confirmClient(ng,search:lookup.control);noGrant.prepare(expected:noGrant.control)
    try expect(noGrant.session.review?.preview.clientID==id && !noGrant.canSubmit && noGrant.submission==nil,"Client GET created synthetic CREATE authority")
    let withoutRead=TaskDraftViewModel(port:ControlledTaskCreatePort());enter(withoutRead);withoutRead.openClientPicker(input:withoutRead.inputControl);try expect(!withoutRead.clientPickerAvailable && withoutRead.clientPickerOwner==nil,"Default Task composer inferred a Client read port")
    return count
}
