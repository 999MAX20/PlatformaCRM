import Foundation
import CRMCore

@MainActor func checkTaskCommentAuthor(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let template=try Data(contentsOf:directory.appendingPathComponent("task-101-1101.json"))
    func detail(_ author: Any?) throws -> TaskDetails {
        var json=try JSONSerialization.jsonObject(with:template) as! [String:Any];var comments=json["comments"] as! [[String:Any]];comments[0].removeValue(forKey:"author");if let author {comments[0]["author"]=author};json["comments"]=comments
        return try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:json))
    }
    let known=try detail(["id":9001,"email":"fixture@example.invalid","full_name":"Synthetic employee"]),other=try detail(["id":9002,"email":"other@example.invalid","full_name":"Other employee"])
    let source=ControlledTasks(),model=TaskListViewModel(repository:source)
    let page=try JSONDecoder().decode(TaskPage.self,from:Data(contentsOf:directory.appendingPathComponent("tasks-101.json")))
    let loading=Task {await model.load(business:101,epoch:1)};await source.waitPage(0);await source.resolvePage(0,.success(page));await loading.value
    for (n,payload) in [known,try detail(nil),other,try detail(NSNull())].enumerated() {
        let reading=Task {await model.open(id:1101)};await source.waitDetail(n);try expect(model.detail==nil,"Pending comment author reused cached name")
        await source.resolveDetail(n,.success(payload));await reading.value
        try expect(model.detail?.comments==payload.comments && model.comment==nil && model.cancelReason==nil,"Fresh comment author discarded/reused or inferred UPDATE capability")
    }
    let reads=await source.counts();_=model.detail?.comments.map(\.authorRead);try expect(await source.counts()==reads,"Comment author display issued user lookup")
    let denied=Task {await model.open(id:1101)};await source.waitDetail(4);await source.resolveDetail(4,.failure(.denied));await denied.value
    try expect(model.detail==nil && model.detailFailure == .denied,"Denied read exposed previous comment author")
    let leaving=Task {await model.open(id:1101)};await source.waitDetail(5);model.back();await source.resolveDetail(5,.success(known));await leaving.value
    try expect(model.detail==nil,"Late comment author repopulated after Back")
    let old=Task {await model.open(id:1101)};await source.waitDetail(6);model.reconcileCommentOwner(business:202,epoch:2);await source.resolveDetail(6,.success(known));await old.value
    try expect(model.detail==nil && model.business==nil,"Old Business/epoch leaked comment author")
    return count
}
