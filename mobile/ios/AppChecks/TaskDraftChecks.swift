import Foundation
import CRMCore

@MainActor func checkTaskDraft(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let transport=SearchTransport(directory),model=TaskListViewModel(repository:APIReadRepository(transport:transport)),a=TaskDraftContext(business:101,epoch:6)
    await model.load(business:101,epoch:6);model.query="review";model.status="done"
    let ids=model.items.map(\.id),reads=await transport.recorded().count
    model.draft.open(a);let old=model.draft.session.selection!;model.draft.update(.description,"Unsent manual note",old);model.draft.prepare(old)
    try expect(model.draft.session.phase == .editing && !model.draft.session.issues.isEmpty && model.draft.session.values.description=="Unsent manual note","Required error lost input")
    model.draft.update(.title,"Synthetic task draft",old);model.draft.update(.priority,"urgent",old);model.draft.prepare(old)
    try expect(model.draft.session.phase == .review,"Task draft failed local review")
    try expect(await transport.recorded().count==reads && model.items.map(\.id)==ids && model.selectedID==nil,"Task preview requested/created a Task")
    model.draft.back(old);model.draft.back(old);model.draft.open(a)
    let current=model.draft.session.selection!;model.draft.discard(old)
    try expect(model.draft.session.selection==current && model.query=="review" && model.status=="done","Back or stale discard changed current list/draft")
    await transport.override("/api/mobile/v1/tasks/",ReadResponse(status:503,data:Data()));await model.load(business:101,epoch:6)
    try expect(model.failure != nil && model.draft.session.selection==current && model.draft.session.values.title=="Synthetic task draft","Recoverable list error cleared input or route")
    await model.load(business:101,epoch:6);await model.open(id:1101)
    try expect(model.draft.session.selection==nil && model.draft.session.values.title=="Synthetic task draft" && model.detail?.task.id==1101,"Task read failed to close form while retaining draft")
    model.back();await model.load(business:202,epoch:7)
    try expect(model.draft.session.values==TaskDraftValues() && model.draft.session.context==TaskDraftContext(business:202,epoch:7),"Business switch retained Task draft")
    model.draft.update(.title,"old event",current);try expect(model.draft.session.values.title.isEmpty,"Old UI callback entered next Business")
    model.clear();try expect(model.draft.session.context==nil,"Clear retained draft context")
    return count
}
