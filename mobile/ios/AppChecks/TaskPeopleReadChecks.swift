import Foundation
import CRMCore

@MainActor func checkTaskPeopleRead(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let template=try Data(contentsOf:directory.appendingPathComponent("task-101-1101.json"))
    func detail(_ person: Any?,business: Int=101) throws -> TaskDetails {
        var json=try JSONSerialization.jsonObject(with:template) as! [String:Any];var fields=json["details"] as! [String:Any]
        for key in ["assignee","created_by"] {fields.removeValue(forKey:key);if let person {fields[key]=person}};json["details"]=fields;json["business"]=business
        return try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:json))
    }
    let user:[String:Any] = ["id":9001,"email":"fixture@example.invalid","full_name":"Synthetic employee"]
    let known=try detail(user),null=try detail(NSNull()),unknown=try detail(nil),changed=try detail(["id":9002,"email":"other@example.invalid","full_name":"Other employee"])
    let source=ControlledTasks(),model=TaskListViewModel(repository:source)
    let page=try JSONDecoder().decode(TaskPage.self,from:Data(contentsOf:directory.appendingPathComponent("tasks-101.json")))
    let loading=Task {await model.load(business:101,epoch:1)};await source.waitPage(0);await source.resolvePage(0,.success(page));await loading.value
    let first=Task {await model.open(id:1101)};await source.waitDetail(0);try expect(model.detail==nil,"Pending detail exposed previous people")
    await source.resolveDetail(0,.success(known));await first.value
    try expect(model.detail?.details.assignee==known.details.assignee && model.detail?.details.created_by==known.details.created_by,"Fresh scoped people missing")
    let reads=await source.counts()
    if case .person(let person)=model.detail!.details.assignee {try expect(person.displayName=="Synthetic employee","Read source name changed")} else {throw ViewModelCheckFailure(message:"Person missing")}
    try expect(await source.counts()==reads && model.comment==nil && model.cancelReason==nil,"Display person issued lookup or inferred edit/UPDATE capability")
    for (n,payload) in [null,unknown,changed].enumerated() {
        let reload=Task {await model.open(id:1101)};await source.waitDetail(n+1);try expect(model.detail==nil,"Reload retained previous person")
        await source.resolveDetail(n+1,.success(payload));await reload.value
        try expect(model.detail?.details.assignee==payload.details.assignee && model.detail?.details.created_by==payload.details.created_by,"Fresh null/unknown/new user reused old name")
    }
    for (n,error) in [ReadFailure.denied,.unavailable].enumerated() {
        let failed=Task {await model.open(id:1101)};await source.waitDetail(n+4);await source.resolveDetail(n+4,.failure(error));await failed.value
        try expect(model.detail==nil && model.detailFailure==error,"403/503 exposed old user name/email")
    }
    let foreign=Task {await model.open(id:1101)};await source.waitDetail(6);await source.resolveDetail(6,.success(try detail(user,business:202)));await foreign.value
    try expect(model.detail==nil && model.detailFailure == .invalidPayload,"Foreign Business miniobject entered current detail")
    let leaving=Task {await model.open(id:1101)};await source.waitDetail(7);model.back();await source.resolveDetail(7,.success(known));await leaving.value
    try expect(model.detail==nil && model.selectedID==nil,"Back repopulated private people")
    let old=Task {await model.open(id:1101)};await source.waitDetail(8);model.reconcileCommentOwner(business:202,epoch:2);await source.resolveDetail(8,.success(known));await old.value
    try expect(model.detail==nil && model.business==nil,"Late old Business/epoch leaked user miniobject")
    return count
}
