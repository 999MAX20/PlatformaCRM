import Foundation
import CRMCore

actor ControlledTaskClientEditPort:SyntheticTaskClientEditPort {
    nonisolated let grants:[SyntheticTaskClientEditGrant]
    private var sent:[TaskClientEditAttempt]=[],pending:[Int:CheckedContinuation<SyntheticTaskClientEditOutcome,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    init(update:Bool=true) {grants=[SyntheticTaskClientEditGrant(business:101,task:1101,actor:9001,update:update),SyntheticTaskClientEditGrant(business:202,task:1201,actor:9002,update:update)]}
    func execute(_ attempt:TaskClientEditAttempt) async throws -> SyntheticTaskClientEditOutcome {let i=sent.count;sent.append(attempt);return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func lose(_ i:Int) {pending.removeValue(forKey:i)!.resume(throwing:ReadFailure.unavailable)}
    func resolve(_ i:Int,_ outcome:SyntheticTaskClientEditOutcome) {pending.removeValue(forKey:i)!.resume(returning:outcome)}
    func calls()->[TaskClientEditAttempt] {sent}
}
actor ControlledTaskClientEditReads:ClientSearchRepository {
    private var lists:[CheckedContinuation<ClientList,any Error>?]=[],profiles:[CheckedContinuation<ClientProfile,any Error>?]=[]
    private var listWait:[Int:CheckedContinuation<Void,Never>]=[:],profileWait:[Int:CheckedContinuation<Void,Never>]=[:]
    private var sent:[String]=[]
    func searchClients(business:Int,search:String) async throws -> ClientList {let i=lists.count;sent.append("list:\(business):\(search)");return try await withCheckedThrowingContinuation {lists.append($0);listWait.removeValue(forKey:i)?.resume()}}
    func clientProfile(business:Int,id:Int) async throws -> ClientProfile {let i=profiles.count;sent.append("profile:\(business):\(id)");return try await withCheckedThrowingContinuation {profiles.append($0);profileWait.removeValue(forKey:i)?.resume()}}
    func waitList(_ i:Int) async {if lists.count<=i {await withCheckedContinuation {listWait[i]=$0}}}
    func waitProfile(_ i:Int) async {if profiles.count<=i {await withCheckedContinuation {profileWait[i]=$0}}}
    func resolveList(_ i:Int,_ value:ClientList) {lists[i]!.resume(returning:value);lists[i]=nil}
    func resolveProfile(_ i:Int,_ value:ClientProfile) {profiles[i]!.resume(returning:value);profiles[i]=nil}
    func calls()->[String] {sent}
}
@MainActor func checkTaskClientEdit(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),detail=try await repo.taskDetails(business:101,id:1101),context=TaskCommentContext(business:101,task:1101,epoch:1),read=TaskCommentRead(context:context,revision:1),source=TaskClientEditSource(read:read,task:detail.task,original:detail.clientRead),port=ControlledTaskClientEditPort(),reads=ControlledTaskClientEditReads(),model=TaskClientEditViewModel(port:port,clients:reads)
    let page=try await repo.searchClients(business:101,search:""),profile=try await repo.clientProfile(business:101,id:1754)
    model.bind(source);let initial=await reads.calls();try expect(model.canOpen && model.canPresent && model.draft.mode==nil && model.draft.choice==nil && model.draft.query.isEmpty && initial.isEmpty,"Client editor inferred mode/choice/read/permission/query")
    model.open(expected:model.control);model.prepare(expected:model.control);try expect(model.review==nil && model.showsIssue,"Unset Client intent defaulted null")
    model.choose(.set,expected:model.control);let input=model.inputControl!,oldControl=model.control!
    for raw in [" ","  "] {model.updateQuery(raw,input:input);try expect(model.draft.query==raw && model.inputControl==input,"Consecutive raw Client query lost input")}
    let staleChild=model.picker.control!;model.updateQuery("",input:input);await model.readClients(expected:model.control,child:staleChild);try expect(await reads.calls().isEmpty,"Old query ticket read a newer search")
    model.updateQuery("  ",input:input);let first=Task {await model.readClients(expected:model.control,child:model.picker.control)};await reads.waitList(0)
    model.updateQuery("overwrite",input:input);try expect(model.inputControl==nil && model.draft.query=="  ","Pending Client list accepted old input")
    model.back(expected:model.control);let closed=model.control!,saved=model.draft;await reads.resolveList(0,page);await first.value
    try expect(!model.editing && model.control==closed && model.draft==saved && model.picker.session.context==nil,"Closed Client editor adopted late search")
    model.open(expected:model.control);try expect(model.picker.session.query=="  " && !model.picker.session.loaded && model.picker.session.items.isEmpty,"Reopened Client picker defaulted/read/lost raw query")
    let list=Task {await model.readClients(expected:model.control,child:model.picker.control)};await reads.waitList(1);let pending=model.picker.control!;await reads.resolveList(1,page);await list.value
    try expect(model.picker.session.items==page.items && model.picker.session.total==page.summary.total && model.picker.session.partial==(page.summary.total>page.items.count),"Client counts/window were filtered or promoted")
    await model.openClient(1754,expected:model.control,child:pending);try expect(model.picker.session.profileSelection==nil,"Pending search ticket selected ready Client")
    await model.openClient(701,expected:model.control,child:model.picker.control);try expect(model.picker.session.profileSelection==nil,"Unprovided legacy Client became a current row")
    let opening=Task {await model.openClient(1754,expected:model.control,child:model.picker.control)};await reads.waitProfile(0);let pendingProfile=model.picker.control!
    model.useClient(expected:model.control,child:pendingProfile);try expect(model.draft.choice==nil,"Pending profile became selected Client")
    await reads.resolveProfile(0,try await repo.clientProfile(business:202,id:801));await opening.value
    try expect(model.picker.profile.failure == .invalidPayload && model.draft.choice==nil,"Foreign Client profile accepted")
    let retry=Task {await model.retryClient(expected:model.control,child:model.picker.control)};await reads.waitProfile(1);let oldProfile=model.picker.control!;await reads.resolveProfile(1,profile);await retry.value
    model.useClient(expected:model.control,child:oldProfile);try expect(model.draft.choice==nil,"Former pending profile adopted current result")
    model.useClient(expected:model.control,child:model.picker.control);let chosen=model.draft
    try expect(chosen.choice?.id==1754 && chosen.choiceRead==source.read && chosen.query=="  " && model.source==source,"Client selection altered original/unrelated Task fields or lost raw query")
    model.prepare(expected:oldControl);try expect(model.review==nil,"Old parent control prepared current Client")
    model.prepare(expected:model.control);let review=model.review!,reviewControl=model.control!
    let fields=try JSONSerialization.jsonObject(with:review.change!.body()!) as! [String:Any]
    try expect(Set(fields.keys)==["client"] && fields["client"] as? Int==1754 && review.draft==chosen && review.source==source,"Review serialized another field/alias or lost original/query")
    model.back(expected:model.control);model.choose(.clear,expected:model.control);model.prepare(expected:model.control)
    try expect(model.review?.change?.mode == .clear && (try JSONSerialization.jsonObject(with:model.review!.change!.body()!) as! [String:Any])["client"] is NSNull && model.draft.choice==chosen.choice,"Clear lost retained choice or emitted another field")
    model.back(expected:model.control);model.choose(.set,expected:model.control);model.prepare(expected:model.control);try expect(model.review?.draft==chosen,"Set/clear/review Back lost Client raw draft")
    await model.submit(expected:reviewControl);try expect(await port.calls().isEmpty,"Old review submitted current Client intent")
    let sending=Task {await model.submit(expected:model.control)};await port.wait(0);let attempt=await port.calls()[0],body=attempt.preparedBody()!
    model.updateQuery("overwrite",input:input);model.choose(.clear,expected:model.control);model.askClear(expected:model.control);await model.submit(expected:model.control)
    try expect(await port.calls().count==1 && model.blocked && model.draft==chosen && model.clearConfirmation==nil,"Pending Client UPDATE edited/replayed/reset input")
    await port.lose(0);await sending.value;try expect(model.submission?.phase == .unknown && model.submission?.attempt.preparedBody()==body && model.submission?.attempt.review==attempt.review,"Unknown Client outcome lost exact input/source/body/attempt")
    let reread=TaskCommentRead(context:context,revision:2);model.bind(TaskClientEditSource(read:reread,task:detail.task,original:.client(1754)))
    try expect(model.blocked && model.submission?.phase == .unknown && !model.canOpen && model.submission?.attempt.preparedBody()==body,"Matching Client reread became outcome proof")
    model.bind(TaskClientEditSource(read:TaskCommentRead(context:TaskCommentContext(business:101,task:1101,epoch:2),revision:3),task:detail.task,original:.client(1754)))
    try expect(model.blocked && model.submission==nil && model.retainedAttemptCount==1 && !model.canOpen,"Epoch replayed unknown Client attempt")
    let other=try await repo.taskDetails(business:202,id:1201);model.bind(TaskClientEditSource(read:TaskCommentRead(context:TaskCommentContext(business:202,task:1201,epoch:2),revision:4),task:other.task,original:other.clientRead));try expect(model.canOpen && !model.blocked && model.draft.mode==nil,"One unknown Task blocked independent Client edit")
    let fresh=TaskClientEditViewModel(port:ControlledTaskClientEditPort(),clients:repo);fresh.bind(source);fresh.open(expected:fresh.control);fresh.choose(.set,expected:fresh.control);fresh.updateQuery("  retained  ",input:fresh.inputControl);fresh.askClear(expected:fresh.control);let question=fresh.clearConfirmation!;fresh.dismissClear(question);fresh.choose(.clear,expected:fresh.control);fresh.confirmClear(question);try expect(fresh.draft.mode == .clear && fresh.draft.query=="  retained  ","Old reset dialog discarded current Client intent")
    fresh.askClear(expected:fresh.control);fresh.confirmClear(fresh.clearConfirmation!);try expect(fresh.draft==TaskClientEditDraft() && fresh.picker.session.query.isEmpty && fresh.source==source,"Local reset changed original or kept implicit choice/query")
    fresh.bind(TaskClientEditSource(read:read,task:detail.task,original:.unknown));try expect(fresh.canPresent && !fresh.canOpen,"Unknown original became editable null")
    let noGrant=TaskClientEditViewModel(port:ControlledTaskClientEditPort(update:false),clients:repo);noGrant.bind(source);try expect(!noGrant.canPresent && !noGrant.canOpen,"Client GET granted Task UPDATE")
    let confirmed=TaskClientEditViewModel(port:FixtureTaskClientEditPort(directory:directory),clients:repo);confirmed.bind(source);confirmed.open(expected:confirmed.control);confirmed.choose(.clear,expected:confirmed.control);confirmed.prepare(expected:confirmed.control);await confirmed.submit(expected:confirmed.control);let record=confirmed.submission!;try expect(record.phase == .confirmed && record.result?.value==nil && confirmed.source==source,"Separate fake clear changed GET source")
    confirmed.acknowledge(expected:confirmed.control,record:record);try expect(confirmed.consumed && !confirmed.canOpen && confirmed.source==source,"Confirmed Client edit reused consumed read")
    let ownerPort=ControlledTaskClientEditPort(),owner=TaskListViewModel(repository:repo,commentSource:FixtureTaskCommentDraftSource(directory:directory),dateEditSubmission:FixtureTaskDateEditPort(directory:directory),appointmentEditSubmission:FixtureTaskAppointmentEditPort(directory:directory),appointmentEditReads:repo,clientEditSubmission:ownerPort,clientEditReads:repo)
    await owner.load(business:101,epoch:1);await owner.open(id:1101);let action=owner.clientEdit!,parent=owner.control!
    try expect(action.source?.original == .notSet && action.canOpen && owner.clientEditCurrent(parent),"Same-response original/fixture UPDATE context did not bind")
    owner.openClientEdit(action.control,parent:parent);owner.openDateEdit(owner.dateEdit?.control,parent:parent);owner.openAppointmentEdit(owner.appointmentEdit?.control,parent:parent)
    try expect(action.editing && owner.dateEdit?.editing==false && owner.appointmentEdit?.editing==false && !owner.dateEditCurrent(parent) && !owner.appointmentEditCurrent(parent),"Other relation/date editor bypassed Client input lane")
    action.choose(.clear,expected:action.control);action.prepare(expected:action.control);let submit=Task {await action.submit(expected:action.control)};await ownerPort.wait(0);await ownerPort.lose(0);await submit.value
    let before=owner.detail,rows=owner.items,total=owner.total;if let read=owner.comment?.session.read {owner.openComment(read)}
    try expect(owner.taskActionOccupied && owner.comment?.session.selection==nil && owner.detail==before && owner.items==rows && owner.total==total && !owner.appointmentEditCurrent(owner.control),"Unknown Client UPDATE allowed raw comment/optimistic GET/sibling action")
    await owner.load(business:101,epoch:2);await owner.open(id:1101);try expect(owner.taskActionOccupied && action.blocked && action.canPresent && owner.clientEditCurrent(owner.control) && action.submission==nil && action.retainedAttemptCount==1 && !owner.dateEditCurrent(owner.control) && !owner.appointmentEditCurrent(owner.control),"Epoch lost quarantine/retained attempt/peer blockers")
    let plain=TaskListViewModel(repository:repo,commentSource:FixtureTaskCommentDraftSource(directory:directory)),noRead=TaskListViewModel(repository:repo,clientEditSubmission:ownerPort);try expect(plain.clientEdit==nil && noRead.clientEdit==nil,"Default GET consumer inferred Client UPDATE/read port")
    let rawCases=(try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("client-search-raw-unicode-cases.json"))) as! [String:Any])["cases"] as! [[String:Any]]
    for row in rawCases {
        let before=row["before"] as! String,after=row["after"] as! String,changed=row["changed"] as! Bool,submitted=row["after_submitted"] as! String
        let unicodeReads=ControlledTaskClientEditReads(),search=ClientSearchViewModel(repository:unicodeReads),searchContext=ClientSearchContext(business:101,epoch:11)
        search.bind(searchContext);search.open(searchContext);let input=search.inputControl!;search.update(before,input:input)
        let load=Task {await search.submit(expected:search.control)};await unicodeReads.waitList(0);let prior=search.control!
        search.update(after,input:input);try expect(search.session.query.utf8.elementsEqual(after.utf8) && search.inputControl==input,"Generic search dropped consecutive Unicode input")
        try expect((search.control != prior)==changed,"Unicode query change retained old read/window control")
        await unicodeReads.resolveList(0,page);await load.value
        try expect(search.session.loaded == !changed,"Changed Unicode query accepted late old list")
        if changed {
            await search.openClient(1754,expected:prior);try expect(search.session.profileSelection==nil,"Old Unicode query window opened a Client profile")
            let next=Task {await search.submit(expected:search.control)};await unicodeReads.waitList(1);await unicodeReads.resolveList(1,page);await next.value
        }
        let recorded=await unicodeReads.calls();try expect(search.session.submitted!.utf8.elementsEqual(submitted.utf8) && recorded.last!.utf8.elementsEqual(("list:101:"+submitted).utf8),"Generic search normalized request or automatically re-read")
        let partialReads=ControlledTaskClientEditReads(),partial=TaskClientEditViewModel(port:ControlledTaskClientEditPort(),clients:partialReads)
        partial.bind(source);partial.open(expected:partial.control);partial.choose(.set,expected:partial.control);let rawInput=partial.inputControl!;partial.updateQuery(before,input:rawInput);partial.updateQuery(after,input:rawInput)
        try expect(partial.draft.query.utf8.elementsEqual(after.utf8) && partial.picker.session.query.utf8.elementsEqual(after.utf8) && partial.inputControl==rawInput && partial.source==source,"Task Client partial lost exact Unicode query/source/input owner")
        try expect(await partialReads.calls().isEmpty && partial.draft.choice==nil && partial.draft.choiceRead==nil,"Raw Unicode change auto-read/defaulted a Client or inherited a relation")
    }
    return count
}
