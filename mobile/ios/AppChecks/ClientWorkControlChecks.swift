import Foundation
import CRMCore

@MainActor func checkClientWorkControls(directory:URL) async throws -> Int {
    var count=0,index=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func response(_ name:String)->ReadResponse {ReadResponse(status:200,data:try! Data(contentsOf:directory.appendingPathComponent(name+".json")))}
    let transport=SearchTransport(directory),model=ClientProfileViewModel(repository:APIReadRepository(transport:transport))
    await model.load(business:101,id:701,epoch:1);let work=model.work!,read=model.readSelection!,notes=model.detail?.details.notes
    try expect(!work.matches(nil),"Missing work control accepted")
    await transport.holdDetails()
    for (target,file) in [(ClientWorkTarget.task(1401),"task-101-1401"),(.conversation(931),"inbox-101-931"),(.appointment(5101),"appointment-101-5101")] {
        let entry=work.presentation!,before=await transport.recorded().count,n=index;index += 1
        let open=Task {await work.open(target,presentation:entry)};await transport.wait(n);let visit=work.presentation!
        await work.open(target,presentation:entry);await work.retry(presentation:visit);let oldBack=work.back(presentation:entry)
        try expect(await transport.recorded().count==before+1 && !oldBack && work.selected==target,"Old parent/pending duplicate changed work child")
        await transport.resolve(n,ReadResponse(status:403,data:Data()));await open.value
        try expect(work.failure == .denied && work.detail==nil && model.readSelection==read,"Supplied source target inferred destination permission or erased parent")
        let retryIndex=index;index += 1;let retry=Task {await work.retry(presentation:work.presentation)};await transport.wait(retryIndex);let fresh=work.presentation!
        let staleBack=work.back(presentation:visit);await work.retry(presentation:visit)
        try expect(await transport.recorded().count==before+2 && !staleBack && work.presentation==fresh,"Old child Back/retry affected new visit")
        await transport.resolve(retryIndex,response(file));await retry.value
        try expect(work.detail != nil && work.failure==nil && model.readSelection==read && model.detail?.details.notes==notes,"Fresh child result lost current parent or relation")
        try expect(work.back(presentation:fresh) && work.detail==nil && model.detail?.client.id==701,"Current work Back did not preserve profile")
        await work.open(target,presentation:entry)
        try expect(await transport.recorded().count==before+2 && work.selected==nil,"Old parent entry reopened child after Back")
    }
    let leaveIndex=index;index += 1;let leaving=Task {await work.open(.task(1401),presentation:work.presentation)};await transport.wait(leaveIndex);let old=work.presentation!;work.back(presentation:old)
    let reopenIndex=index;index += 1;let reopened=Task {await work.open(.task(1401),presentation:work.presentation)};await transport.wait(reopenIndex);let current=work.presentation!
    let rejectedBack=work.back(presentation:old);await work.retry(presentation:old)
    var json=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-101-1401.json"))) as! [String:Any]
    var task=json["task"] as! [String:Any];task["title"]=NSNull();json["task"]=task
    await transport.resolve(reopenIndex,ReadResponse(status:200,data:try JSONSerialization.data(withJSONObject:json)));await reopened.value
    await transport.resolve(leaveIndex,response("task-101-1401"));await leaving.value
    try expect(!rejectedBack && work.presentation==current && work.detail != nil && work.detail?.title==nil && work.failure==nil,"Old same-target visit restored withheld title or closed current child")
    work.back(presentation:current);let lateIndex=index;index += 1;let late=Task {await work.open(.conversation(931),presentation:work.presentation)};await transport.wait(lateIndex);let previous=work.presentation!
    let parentIndex=index;index += 1;let refresh=Task {await model.load(business:101,id:701,epoch:2)};await transport.wait(parentIndex)
    try expect(work.presentation==nil && work.detail==nil,"Parent pending retained dependent private data")
    await transport.resolve(parentIndex,response("client-101-701"));await refresh.value;await transport.resolve(lateIndex,response("inbox-101-931"));await late.value
    let beforeOld=await transport.recorded().count;await work.open(.task(1401),presentation:previous);await work.retry(presentation:previous)
    try expect(await transport.recorded().count==beforeOld && !work.back(presentation:previous) && work.detail==nil && work.selected==nil && model.scopeEpoch==2 && model.readSelection != read,"New parent read accepted old child result/controls")
    return count
}
