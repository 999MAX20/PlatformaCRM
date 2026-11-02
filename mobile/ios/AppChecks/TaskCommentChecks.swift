import Foundation
import CRMCore

actor ControlledCommentSource: TaskCommentDraftSource {
    private var next=0
    private var pending: [Int:CheckedContinuation<Bool,Never>]=[:]
    private var waiters: [Int:CheckedContinuation<Void,Never>]=[:]
    func matchesFixture(_ detail: TaskDetails) async -> Bool {
        let id=next;next += 1;return await withCheckedContinuation {pending[id]=$0;waiters.removeValue(forKey:id)?.resume()}
    }
    func wait(_ id: Int) async {if pending[id]==nil {await withCheckedContinuation {waiters[id]=$0}}}
    func resolve(_ id: Int,_ value: Bool) {pending.removeValue(forKey:id)!.resume(returning:value)}
}

@MainActor func checkTaskComment(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let source=FixtureTaskCommentDraftSource(directory:directory),transport=SearchTransport(directory),repo=APIReadRepository(transport:transport)
    let model=TaskListViewModel(repository:repo,commentSource:source)
    await model.load(business:101,epoch:10);model.query="Alpha";model.status="open";await model.open(id:1101)
    let detail=model.detail!,rows=model.items,reads=await transport.recorded(),comment=model.comment!,read=comment.session.read!
    try expect(comment.session.available && comment.session.text.isEmpty,"Comment editor copied existing read text")
    comment.open(read);let selection=comment.session.selection!
    comment.update("  Manual new comment\nnext line  ",selection);comment.prepare(selection)
    try expect(comment.session.review?.text=="Manual new comment\nnext line" && comment.session.phase == .review,"Comment did not reach unsent review")
    try expect(await transport.recorded()==reads && model.items==rows && model.detail==detail,"Comment review issued a request or mutated rows/history/status")
    comment.back(selection);comment.close(selection);model.back()
    try expect(comment.session.text.isEmpty && comment.session.read==nil && model.query=="Alpha" && model.status=="open","Task Back exposed input or lost list context")
    await model.open(id:1101);try expect(comment.session.text=="  Manual new comment\nnext line  ","Fresh verified reopen failed to restore same task comment")
    await model.open(id:1103);try expect(comment.session.text.isEmpty,"Another task inherited comment")
    await model.open(id:1101);try expect(comment.session.text.hasPrefix("  Manual new"),"Per-task private input was lost")
    let opaque=TaskListViewModel(repository:repo);await opaque.load(business:101,epoch:10);await opaque.open(id:1101)
    try expect(opaque.comment==nil,"Default repository acquired comment permission from readability")
    let unscoped=TaskListViewModel(repository:repo,commentSource:source);await unscoped.load(business:101);await unscoped.open(id:1101)
    try expect(unscoped.comment?.session.read==nil && unscoped.comment?.session.available==false,"Missing epoch enabled comment")
    let controlled=ControlledTasks(),owner=TaskListViewModel(repository:controlled,commentSource:source)
    let page=try JSONDecoder().decode(TaskPage.self,from:Data(contentsOf:directory.appendingPathComponent("tasks-101.json")))
    let loading=Task {await owner.load(business:101,epoch:20)};await controlled.waitPage(0);await controlled.resolvePage(0,.success(page));await loading.value
    let start=Task {await owner.open(id:1101)};await controlled.waitDetail(0);await controlled.resolveDetail(0,.success(detail));await start.value
    let local=owner.comment!;local.open(local.session.read!);let old=local.session.selection!;local.update("Keep after error",old)
    for (n,problem) in [ReadFailure.denied,.unavailable].enumerated() {
        let failure=Task {await owner.open(id:1101)};await controlled.waitDetail(1+n*2)
        try expect(local.session.text.isEmpty && !local.session.available && local.session.selection==nil,"Pending detail retained old editor")
        await controlled.resolveDetail(1+n*2,.failure(problem));await failure.value
        try expect(owner.detailFailure==problem && owner.detail==nil && !local.session.available,"403/503 retained editable task")
        let recovery=Task {await owner.open(id:1101)};await controlled.waitDetail(2+n*2);await controlled.resolveDetail(2+n*2,.success(detail));await recovery.value
        try expect(local.session.text=="Keep after error" && local.session.available,"Read failure discarded own manual comment")
    }
    let origins=ControlledCommentSource(),races=TaskListViewModel(repository:repo,commentSource:origins)
    await races.load(business:101,epoch:30)
    let first=Task {await races.open(id:1101)};await origins.wait(0)
    let second=Task {await races.open(id:1103)};await origins.wait(1)
    await origins.resolve(1,true);await second.value;await origins.resolve(0,true);await first.value
    try expect(races.detail?.task.id==1103 && races.comment?.session.read?.context.task==1103,"Late fixture verification restored old Task")
    let previousEpoch=Task {await races.open(id:1101)};await origins.wait(2);await races.load(business:101,epoch:31)
    let currentEpoch=Task {await races.open(id:1101)};await origins.wait(3);await origins.resolve(2,true);await previousEpoch.value
    try expect(races.detailLoading && races.detail==nil && races.comment?.session.available==false,"Late same-ID epoch verification exposed old source")
    await origins.resolve(3,true);await currentEpoch.value
    let leaving=Task {await races.open(id:1101)};await origins.wait(4);races.back();await origins.resolve(4,true);await leaving.value
    try expect(races.detail==nil && races.selectedID==nil && races.comment?.session.text=="" && races.comment?.session.available==false,"Parent Back was repopulated after provider await")
    let oldBusiness=Task {await races.open(id:1101)};await origins.wait(5);await races.load(business:202,epoch:32)
    let newBusiness=Task {await races.open(id:1201)};await origins.wait(6);await origins.resolve(6,true);await newBusiness.value;await origins.resolve(5,true);await oldBusiness.value
    try expect(races.business==202 && races.detail?.task.id==1201 && races.comment?.session.read?.context.business==202,"Old Business verification entered current comment")
    let mismatched=Task {await races.open(id:1201)};await origins.wait(7);await origins.resolve(7,false);await mismatched.value
    try expect(races.detail?.task.id==1201 && races.comment?.session.available==false && races.comment?.session.text=="","Unverified detail enabled or prefilled comment")
    races.clear();try expect(races.comment?.session.read==nil && races.comment?.session.text=="","Clear retained public comment state")
    let offTab=TaskListViewModel(repository:repo,commentSource:source)
    await offTab.load(business:101,epoch:40);await offTab.open(id:1101)
    let offComment=offTab.comment!;offComment.open(offComment.session.read!);offComment.update("Private old Business",offComment.session.selection!)
    let beforeReconcile=await transport.recorded()
    offTab.reconcileCommentOwner(business:202,epoch:41)
    try expect(offComment.session.read==nil && offComment.session.text.isEmpty && offTab.detail==nil && offTab.selectedID==nil,"Off-tab Business change retained draft or target")
    try expect(await transport.recorded()==beforeReconcile,"Off-tab owner invalidation issued a read")
    await offTab.load(business:101,epoch:42);await offTab.open(id:1101)
    try expect(offComment.session.text.isEmpty,"Returning after off-tab Business roundtrip restored old owner text")
    await races.load(business:101,epoch:50)
    let offTabPending=Task {await races.open(id:1101)};await origins.wait(8)
    races.reconcileCommentOwner(business:202,epoch:51);await origins.resolve(8,true);await offTabPending.value
    try expect(races.detail==nil && races.comment?.session.available==false,"Off-tab owner change failed to revoke pending fixture verification")
    count += try await checkTaskReadTextSourceControls(directory:directory)
    count += try await checkMobileUserDisplaySourceControls(directory:directory)
    return count
}

private struct TypedTaskReferenceSource:TaskCommentDraftSource {
    let reference:TaskDetails
    func matchesFixture(_ detail:TaskDetails) async -> Bool {FixtureTaskCommentDraftSource.verified(detail,reference:reference)}
}
@MainActor private func checkTaskReadTextSourceControls(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let fixture=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-read-text-identity-cases.json"))) as! [String:Any]
    let cases=(fixture["cases"] as! [[String:Any]]).filter {$0["kind"] as! String == "bounded"}
    for (index,row) in cases.enumerated() {
        let beforeData=Data((row["before_json"] as! String).utf8),afterData=Data((row["after_json"] as! String).utf8),reference=try TaskDetails.decodeSource(beforeData),after=try TaskDetails.decodeSource(afterData),changed=row["changed"] as! Bool,field=row["field"] as! String
        let transport=SearchTransport(directory),owner=TaskListViewModel(repository:APIReadRepository(transport:transport),commentSource:TypedTaskReferenceSource(reference:reference)),path="/api/mobile/v1/tasks/1101/",epoch=4300+index
        await owner.load(business:101,epoch:epoch);await transport.override(path,ReadResponse(status:200,data:beforeData));await owner.open(id:1101)
        let comment=owner.comment!;try expect(comment.session.available && owner.detail==reference && owner.detailFailure==nil,"Exact Task fixture reference failed actual parent read")
        owner.openComment(comment.session.read!);let input=comment.inputControl!;comment.update("Operator own unsent text",input:input);owner.back()
        await transport.override(path,ReadResponse(status:200,data:afterData));await owner.open(id:1101)
        try expect(owner.detail==after && owner.detailFailure==nil && comment.session.available == !changed,"Changed Task free text bypassed source eligibility or broke readonly detail")
        let actual:String?;switch field {case "task.title":actual=owner.detail?.task.title;case "details.description":actual=owner.detail?.details.description;default:actual=owner.detail?.comments.first?.text}
        try expect(SourceTextIdentity.same(actual,row["after"] as? String),"Actual readonly detail normalized provided Task free text")
        comment.update("stale overwritten text",input:input);owner.openComment(comment.session.read!)
        try expect(changed ? comment.session.selection==nil && comment.inputControl==nil : comment.session.text=="Operator own unsent text","Stale source/control exposed edit or overwrote private draft")
        owner.back();await transport.override(path,ReadResponse(status:200,data:beforeData));await owner.open(id:1101);owner.openComment(comment.session.read!)
        try expect(comment.session.available && comment.session.text=="Operator own unsent text" && comment.inputControl != input,"Exact reference reread lost draft or revived old input")
        let reads=await transport.recorded();comment.prepare(expected:comment.control)
        try expect(!comment.canSubmit && comment.retainedAttemptCount==0 && comment.session.phase == .review,"Fixture read/source equality inferred synthetic UPDATE authority")
        try expect(await transport.recorded()==reads && reads.count==4 && reads.suffix(3).allSatisfy {$0.path==path && $0.query==["business":"101"]},"Typed identity/source admission invented request or changed scoped existing GET")
    }
    return count
}

@MainActor private func checkMobileUserDisplaySourceControls(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("mobile-user-display-text-cases.json"))) as! [String:Any]
    for (index,row) in (catalog["cases"] as! [[String:Any]]).enumerated() {
        let beforeData=Data((row["before_json"] as! String).utf8),afterData=Data((row["after_json"] as! String).utf8),reference=try TaskDetails.decodeSource(beforeData),after=try TaskDetails.decodeSource(afterData),changed=row["changed"] as! Bool,context=row["context"] as! String,path="/api/mobile/v1/tasks/1101/"
        let transport=SearchTransport(directory),owner=TaskListViewModel(repository:APIReadRepository(transport:transport),commentSource:TypedTaskReferenceSource(reference:reference))
        await owner.load(business:101,epoch:4700+index);await transport.override(path,ReadResponse(status:200,data:beforeData));await owner.open(id:1101);let model=owner.comment!
        try expect(model.session.available && owner.detail==reference,"Exact typed user source failed initial readonly Task reference")
        owner.openComment(model.session.read!);let input=model.inputControl!;model.update("Own unsent text",input:input);owner.back();await transport.override(path,ReadResponse(status:200,data:afterData));await owner.open(id:1101)
        try expect(owner.detail==after && owner.detailFailure==nil && model.session.available == !changed,"User label change bypassed source reference or denied readonly detail")
        let user:MobileUserRead;switch context {case "created_by":user=owner.detail!.details.created_by;case "assignee":user=owner.detail!.details.assignee;default:user=owner.detail!.comments[0].authorRead}
        if case .person(let person)=user {
            let expected=try JSONDecoder().decode(MobileUserItem.self,from:Data((row["after_user_json"] as! String).utf8))
            try expect(person==expected && SourceTextIdentity.same(person.email,expected.email) && SourceTextIdentity.same(person.full_name,expected.full_name) && SourceTextIdentity.same(person.displayName,row["after_display"] as? String),"Actual readonly name/email/fallback normalized provided user text")
        } else {throw ViewModelCheckFailure(message:"Valid user fixture became membership/unknown assertion")}
        model.update("Stale overwrite",input:input);owner.openComment(model.session.read!)
        try expect(changed ? model.session.selection==nil && model.inputControl==nil : model.session.text=="Own unsent text","Old user-source input affected current editor")
        if !changed {model.prepare(expected:model.control)}
        try expect(!model.canSubmit && model.retainedAttemptCount==0,"Provided user id/name/email or source read inferred UPDATE authority")
        let reads=await transport.recorded();try expect(reads.count==3 && reads.suffix(2).allSatisfy {$0.path==path && $0.query==["business":"101"]},"Display identity introduced route/query or command request")
    }
    return count
}
