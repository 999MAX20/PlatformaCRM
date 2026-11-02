import Foundation
import CRMCore

@MainActor func checkTaskCancelReason(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let recording=QueryRecordingTransport(directory),repo=APIReadRepository(transport:recording)
    let source=FixtureTaskCommentDraftSource(directory:directory),model=TaskListViewModel(repository:repo,commentSource:source)
    await model.load(business:101,epoch:10);await model.applyFilter(TaskQueryFilter(status:"open",due:.today),expected:model.querySelection);await model.open(id:1101)
    let original=model.detail!,rows=model.items,reason=model.cancelReason!,comment=model.comment!,read=reason.session.read!
    model.openComment(read);let commentSelection=comment.session.selection!;comment.update("Own independent comment",commentSelection)
    model.openCancelReason(read);try expect(comment.session.selection==nil && comment.session.text=="Own independent comment" && reason.session.text.isEmpty,"Opening reason mixed inputs or left two active editors")
    let selection=reason.session.selection!;reason.update("AB",selection);reason.prepare(selection)
    try expect(reason.session.problem == .minimum && reason.session.text=="AB" && reason.session.phase == .editing,"Invalid reason did not retain input")
    let countBefore=await recording.recorded().count
    reason.update("  Manual reason\nsecond line  ",selection);reason.prepare(selection)
    try expect(reason.session.phase == .review && reason.session.review?.text=="Manual reason\nsecond line","Reason failed to reach unsent review")
    try expect(await recording.recorded().count==countBefore,"Reason review issued a repository request")
    try expect(model.detail==original && model.items==rows && model.detail?.task.status=="open","Reason preview cancelled Task or mutated records")
    reason.back(selection);reason.close(selection);model.openComment(read)
    try expect(comment.session.text=="Own independent comment" && reason.session.selection==nil && reason.session.text.hasPrefix("  Manual"),"Switching local editor lost reason/comment isolation")
    model.openCancelReason(read);let reopened=reason.session.selection!;reason.discard(selection)
    try expect(reason.session.selection==reopened && reason.session.text.hasPrefix("  Manual"),"Stale confirmation cleared reopened reason")
    model.back();try expect(reason.session.text.isEmpty && !reason.session.available && model.selectedID==nil,"Task Back exposed private reason")
    await model.open(id:1101);try expect(reason.session.text.hasPrefix("  Manual"),"Verified own return lost reason")
    let oldRead=reason.session.read!,oldTarget=model.detailSelection!
    await model.applyFilter(TaskQueryFilter(status:"done"),expected:model.querySelection);await model.open(id:1103)
    try expect(!reason.session.available && reason.session.text.isEmpty && comment.session.available,"Closed Task policy was widened or comment was wrongly gated")
    let beforeStale=await recording.recorded().count
    model.openCancelReason(oldRead);model.back(expected:oldTarget);await model.retryDetail(expected:oldTarget)
    try expect(await recording.recorded().count==beforeStale,"Old reason/detail control issued a request")
    try expect(model.selectedID==1103 && reason.session.selection==nil,"Old control enabled reason for current closed Task")
    await model.applyFilter(TaskQueryFilter(status:"open",due:.today),expected:model.querySelection);await model.open(id:1101);model.openCancelReason(reason.session.read!);reason.discard(reason.session.selection!)
    try expect(reason.session.text.isEmpty && model.detail?.task.status=="open","Explicit clear mutated source Task")
    let opaque=TaskListViewModel(repository:repo);await opaque.load(business:101,epoch:11);try expect(opaque.cancelReason==nil,"Opaque read acquired cancellation draft eligibility")
    let unscoped=TaskListViewModel(repository:repo,commentSource:source);await unscoped.load(business:101);await unscoped.open(id:1101);try expect(unscoped.cancelReason?.session.read==nil && unscoped.cancelReason?.session.available==false,"Missing epoch enabled reason")
    let control=ControlledTasks(),owner=TaskListViewModel(repository:control,commentSource:source)
    let page=try JSONDecoder().decode(TaskPage.self,from:Data(contentsOf:directory.appendingPathComponent("tasks-101.json")))
    let loading=Task {await owner.load(business:101,epoch:20)};await control.waitPage(0);await control.resolvePage(0,.success(page));await loading.value
    let start=Task {await owner.open(id:1101)};await control.waitDetail(0);await control.resolveDetail(0,.success(original));await start.value
    let keep=owner.cancelReason!;owner.openCancelReason(keep.session.read!);keep.update("Keep after source error",keep.session.selection!)
    for (n,failure) in [ReadFailure.denied,.unavailable].enumerated() {
        let fail=Task {await owner.open(id:1101)};await control.waitDetail(1+n*2)
        try expect(keep.session.text.isEmpty && !keep.session.available,"Pending read retained reason editor")
        await control.resolveDetail(1+n*2,.failure(failure));await fail.value
        try expect(owner.detailFailure==failure && !keep.session.available,"Denied source retained reason eligibility")
        let recover=Task {await owner.open(id:1101)};await control.waitDetail(2+n*2);await control.resolveDetail(2+n*2,.success(original));await recover.value
        try expect(keep.session.text=="Keep after source error","Source recovery erased own reason")
    }
    let pendingSource=ControlledCommentSource(),races=TaskListViewModel(repository:repo,commentSource:pendingSource)
    await races.load(business:101,epoch:30);await races.applyFilter(TaskQueryFilter(due:.today),expected:races.querySelection)
    let oldActive=Task {await races.open(id:1101)};await pendingSource.wait(0)
    let newClosed=Task {await races.open(id:1103)};await pendingSource.wait(1);await pendingSource.resolve(1,true);await newClosed.value;await pendingSource.resolve(0,true);await oldActive.value
    try expect(races.selectedID==1103 && races.cancelReason?.session.available==false,"Late active Task verification enabled reason on closed selection")
    let pending=Task {await races.open(id:1101)};await pendingSource.wait(2);races.reconcileCommentOwner(business:202,epoch:31);await pendingSource.resolve(2,true);await pending.value
    try expect(races.detail==nil && races.cancelReason?.session.read==nil && races.business==nil,"Off-tab owner change failed to revoke reason source/target")
    return count
}
