import Foundation
import CRMCore

@MainActor func checkTaskScheduleRead(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let template=try Data(contentsOf:directory.appendingPathComponent("task-101-1101.json"))
    func detail(_ fields: [String:Any]) throws -> TaskDetails {
        var json=try JSONSerialization.jsonObject(with:template) as! [String:Any];var values=json["details"] as! [String:Any];values.removeValue(forKey:"reminder_at");values.removeValue(forKey:"snoozed_until");fields.forEach {values[$0.key]=$0.value};json["details"]=values
        return try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:json))
    }
    let known=try detail(["reminder_at":"2026-10-29T23:30:00Z","snoozed_until":"2026-10-30T02:15:00Z"]),null=try detail(["reminder_at":NSNull(),"snoozed_until":NSNull()]),unknown=try detail([:])
    let source=ControlledTasks(),model=TaskListViewModel(repository:source)
    let page=try JSONDecoder().decode(TaskPage.self,from:Data(contentsOf:directory.appendingPathComponent("tasks-101.json")))
    let loading=Task {await model.load(business:101,epoch:1)};await source.waitPage(0);await source.resolvePage(0,.success(page));await loading.value
    let first=Task {await model.open(id:1101)};await source.waitDetail(0);try expect(model.detail==nil && model.detailLoading,"Pending Task displayed cached schedule")
    await source.resolveDetail(0,.success(known));await first.value
    try expect(model.detail?.details.reminder_at == .instant("2026-10-29T23:30:00Z"),"Fresh scoped schedule was dropped")
    let before=await source.counts()
    let ru=AppointmentDate.format(startAt:"2026-10-29T23:30:00Z",timezone:"Asia/Almaty",language:"ru")
    let same=AppointmentDate.format(startAt:"2026-10-30T04:30:00+05:00",timezone:"Asia/Almaty",language:"ru")
    try expect(ru != nil && ru==same,"Business timezone formatter changed equivalent offset instant")
    try expect(AppointmentDate.format(startAt:"2026-10-29T23:30:00Z",timezone:nil,language:"ru")==nil && AppointmentDate.format(startAt:"2026-10-29T23:30:00Z",timezone:"Unknown/Zone",language:"ru")==nil,"Missing/invalid Business timezone fell back to device")
    try expect(await source.counts()==before,"Schedule presentation issued an extra read")
    for (n,payload) in [null,unknown].enumerated() {
        let reload=Task {await model.open(id:1101)};await source.waitDetail(n+1)
        try expect(model.detail==nil,"Reload retained old known schedule")
        await source.resolveDetail(n+1,.success(payload));await reload.value
        try expect(model.detail?.details.reminder_at==payload.details.reminder_at && model.detail?.details.snoozed_until==payload.details.snoozed_until,"Fresh null/unknown reused prior known date")
    }
    for (n,error) in [ReadFailure.denied,.unavailable].enumerated() {
        let failed=Task {await model.open(id:1101)};await source.waitDetail(n+3);await source.resolveDetail(n+3,.failure(error));await failed.value
        try expect(model.detail==nil && model.detailFailure==error,"403/503 retained visible schedule")
    }
    let leaving=Task {await model.open(id:1101)};await source.waitDetail(5);model.back();await source.resolveDetail(5,.success(known));await leaving.value
    try expect(model.detail==nil && model.selectedID==nil,"Back repopulated stale schedule")
    let old=Task {await model.open(id:1101)};await source.waitDetail(6);model.reconcileCommentOwner(business:202,epoch:2);await source.resolveDetail(6,.success(known));await old.value
    try expect(model.detail==nil && model.business==nil,"Old Business/epoch schedule bypassed root invalidation")
    return count
}
