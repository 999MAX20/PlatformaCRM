import Foundation
import CRMCore

@MainActor func checkInboxClientControls(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func data(_ name:String) throws -> Data {try Data(contentsOf:directory.appendingPathComponent(name+".json"))}
    func response(_ name:String) -> ReadResponse {ReadResponse(status:200,data:try! data(name))}
    let a=try JSONDecoder().decode(InboxThread.self,from:data("inbox-101-901")),b=try JSONDecoder().decode(InboxThread.self,from:data("inbox-202-951"))
    let first=InboxReadSelection(business:101,id:901,revision:1),second=InboxReadSelection(business:202,id:951,revision:2)
    // Synchronous callbacks may replace/close a binding. No dependent read may follow.
    for failure in [false,true] {
        let transport=SearchTransport(directory),links=InboxClientViewModel(repository:APIReadRepository(transport:transport));var callbacks=0,newCallbacks=0
        links.bind(a,request:first) {_ in callbacks += 1;links.bind(b,request:second) {_ in newCallbacks += 1}}
        if failure {await transport.override("/api/mobile/v1/inbox/901/",ReadResponse(status:403,data:Data()))}
        await links.open(entry:links.entryControl)
        let reads=await transport.recorded()
        try expect(reads.count==1 && reads[0].path=="/api/mobile/v1/inbox/901/" && callbacks==1 && newCallbacks==0,"Callback rebind started old Client GET or notified replacement owner")
        try expect(links.request==second && links.parent?.clientReferenceID==801 && links.selectedID==nil && links.profile.detail==nil && links.entryControl != nil,"Old completion erased/repopulated replacement binding")
    }
    let closingTransport=SearchTransport(directory),closing=InboxClientViewModel(repository:APIReadRepository(transport:closingTransport))
    closing.bind(a,request:first) {_ in _=closing.close(expected:closing.returnControl)}
    await closing.open(entry:closing.entryControl)
    try expect(await closingTransport.recorded().count==1 && closing.selectedID==nil && closing.profile.detail==nil,"Callback close continued into dependent Client read")
    let transport=SearchTransport(directory),model=InboxViewModel(repository:APIReadRepository(transport:transport)),context=ReplyDraftContext(business:101,conversation:901,epoch:110)
    await model.load(business:101,epoch:110);model.query="response";model.unreadOnly=true;await model.open(id:901)
    let links=model.clientLinks!,reply=model.reply
    model.openReply(context,expected:model.control);reply.update("Private unsent reply",input:reply.inputControl);reply.close(expected:reply.returnControl)
    let before=await transport.recorded().count,messages=model.thread?.messages.map(\.id),unread=model.thread?.conversation.unread_count,entry=links.entryControl!,rootBefore=model.returnControl
    await transport.holdDetails()
    let opening=Task {await model.openClient(entry:entry,expected:model.control)};await transport.wait(0)
    let threadPending=links.control!,earlyReturn=links.returnControl!
    await model.openClient(entry:entry,expected:model.control);await links.retry(expected:threadPending);await model.retryClient(expected:threadPending,parent:model.control)
    model.backToThreadList(expected:rootBefore)
    try expect(await transport.recorded().count==before+1 && links.loading && model.selectedID==901,"Pending duplicate entry/retry or old root Back affected inspector")
    await transport.resolve(0,response("inbox-101-901"));await transport.wait(1);let profilePending=links.control!
    await links.retry(expected:profilePending)
    try expect(profilePending.profile != nil && profilePending.profileLoading && profilePending != threadPending,"Inspector control omitted independent Client read")
    await transport.resolve(1,ReadResponse(status:403,data:Data()));await opening.value;let denied=links.control!,deniedReturn=links.returnControl!
    try expect(links.profile.failure == .denied && links.selectedID==701 && !links.loading,"Independent Client denial erased parent context or claimed profile data")
    try expect(!links.close(expected:earlyReturn),"Old thread/profile-pending Back closed newer result")
    let retry=Task {await model.retryClient(expected:denied,parent:model.control)};await transport.wait(2)
    let retryPending=links.control!;await links.retry(expected:denied);await links.retry(expected:retryPending)
    await transport.resolve(2,response("inbox-101-901"));await transport.wait(3);await transport.resolve(3,response("client-101-701"));await retry.value
    let current=links.control!,currentReturn=links.returnControl!
    try expect(current.profile != denied.profile && links.profile.detail?.client.id==701 && !links.loading,"Retry failed to establish a new independent profile read")
    let afterRetry=await transport.recorded().count;await links.retry(expected:denied)
    try expect(await transport.recorded().count==afterRetry && !links.close(expected:deniedReturn),"Old same-ID Retry/Back acted after fresh profile")
    let work=links.profile.work!,nested=Task {await work.open(.task(1401),presentation:work.presentation)};await transport.wait(4);await transport.resolve(4,response("task-101-1401"));await nested.value
    let nestedReturn=links.returnControl!,rootNested=model.returnControl
    await links.retry(expected:current)
    try expect(!links.close(expected:currentReturn) && !links.close(expected:nestedReturn) && work.selected == .task(1401) && model.selectedID==901,"Inspector Retry/Back closed nested work or parent")
    model.backToThreadList(expected:rootNested);try expect(model.selectedID==901,"Fresh root pop bypassed active inspector")
    try expect(work.back(presentation:work.presentation),"Current work Back failed")
    try expect(!links.close(expected:currentReturn) && links.close(expected:links.returnControl),"Old pre-work return revalidated or fresh inspector close failed")
    try expect(model.thread?.messages.map(\.id)==messages && model.thread?.conversation.unread_count==unread && model.query=="response" && model.unreadOnly && reply.session.text=="Private unsent reply","Inspector/work return changed thread/unread/filter or erased own reply")
    let rootBeforeReply=model.returnControl;model.openReply(context,expected:model.control);model.backToThreadList(expected:rootBeforeReply)
    try expect(model.selectedID==901 && reply.session.text=="Private unsent reply" && reply.control != nil,"Old root Back closed current Reply or lost private buffer")
    reply.close(expected:reply.returnControl);model.backToThreadList(expected:model.returnControl)
    try expect(model.selectedID==nil && links.request==nil,"Current child-free Inbox Back failed")
    // Old delayed revalidation cannot change a later binding even with the same explicit ID.
    let lateTransport=SearchTransport(directory),late=InboxClientViewModel(repository:APIReadRepository(transport:lateTransport));late.bind(a,request:first) {_ in};await lateTransport.holdDetails()
    let leaving=Task {await late.open(entry:late.entryControl)};await lateTransport.wait(0);late.bind(b,request:second) {_ in};let fresh=late.control
    await lateTransport.resolve(0,response("inbox-101-901"));await leaving.value
    let lateReads=await lateTransport.recorded().count
    try expect(late.control==fresh && late.request==second && late.profile.detail==nil && lateReads==1,"Late old thread changed/repopulated new owner")
    var object=try JSONSerialization.jsonObject(with:data("inbox-101-901")) as! [String:Any];var details=object["details"] as! [String:Any];details["client"]=NSNull();object["details"]=details
    let withheld=try JSONDecoder().decode(InboxThread.self,from:JSONSerialization.data(withJSONObject:object)),withheldTransport=SearchTransport(directory),hidden=InboxClientViewModel(repository:APIReadRepository(transport:withheldTransport))
    hidden.bind(a,request:first) {_ in};await withheldTransport.override("/api/mobile/v1/inbox/901/",ReadResponse(status:200,data:try JSONSerialization.data(withJSONObject:object)));await hidden.open(entry:hidden.entryControl)
    try expect(hidden.parent?.clientReferenceID==nil && hidden.entryControl==nil && hidden.profile.detail==nil && hidden.selectedID==nil,"Withheld fresh link loaded cached Client")
    hidden.bind(withheld,request:first) {_ in};await hidden.open(entry:hidden.entryControl)
    try expect(await withheldTransport.recorded().count==1,"Absent link fabricated a second dependent read")
    return count
}
