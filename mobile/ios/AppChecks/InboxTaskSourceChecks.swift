import Foundation
import CRMCore

private actor HeldInboxTaskSource:InboxTaskSourceRepository {
    private var pending:CheckedContinuation<InboxTaskSource,any Error>?
    private var waiter:CheckedContinuation<Void,Never>?
    func source(_ c:InboxConversationFilesContext) async throws -> InboxTaskSource {try await withCheckedThrowingContinuation {pending=$0;waiter?.resume();waiter=nil}}
    func wait() async {if pending==nil {await withCheckedContinuation {waiter=$0}}}
    func resolve(_ value:InboxTaskSource) {pending!.resume(returning:value);pending=nil}
    func fail() {pending!.resume(throwing:ReadFailure.unavailable);pending=nil}
}
@MainActor func checkInboxTaskSource(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let read=APIReadRepository(transport:FixtureTransport(directory:directory)),repo=APIInboxTaskSourceRepository(transport:FixtureInboxTaskSourceTransport(directory:directory)),files=APIInboxConversationFilesRepository(transport:FixtureInboxConversationFilesTransport(directory:directory)),root=InboxViewModel(repository:read,files:files,taskSourceRead:repo)
    await root.load(business:101,epoch:800);await root.open(id:901);let original=inboxReadSnapshot(root.thread,root.items),panel=root.fileMetadata!.taskSource!;root.openFiles(expected:root.filesEntryControl);try expect(panel.session.source==nil && panel.session.choice==nil,"Opening source panel made auto GET/reference")
    await panel.read(expected:panel.control);let stale=panel.control;panel.use(expected:panel.control);let choice=panel.session.choice!;try expect(choice.source.client==701 && choice.source.lead==81 && inboxReadSnapshot(root.thread,root.items)==original,"Read/reference patched Inbox or lost source")
    panel.controlsBlocked={true};panel.clearChoice(expected:panel.control);await panel.read(expected:panel.control);try expect(panel.session.choice==choice,"External command freeze hook ignored");panel.controlsBlocked={false};panel.clearChoice(expected:stale);try expect(panel.session.choice==choice,"Stale clear callback changed choice");panel.clearChoice(expected:panel.control);try expect(panel.session.source != nil && panel.session.choice==nil,"Clear mutated observed relations")
    panel.use(expected:panel.control);root.closeFiles(expected:root.filesPresentationControl);root.openFiles(expected:root.filesEntryControl);try expect(panel.session.source==nil && panel.session.choice==nil,"Hide/reopen revived source qualification")
    root.closeFiles(expected:root.filesPresentationControl);await root.load(business:202,epoch:801);await root.open(id:951);root.openFiles(expected:root.filesEntryControl);await panel.read(expected:panel.control);panel.use(expected:panel.control);try expect(panel.session.choice?.context.business==202 && panel.session.source?.client==1701 && panel.session.source?.lead==nil,"Business switch exposed previous source")
    let a=InboxConversationFilesContext(business:101,conversation:901,epoch:802,revision:1),b=InboxConversationFilesContext(business:202,conversation:951,epoch:803,revision:1)
    for mode in 0...2 {let held=HeldInboxTaskSource(),model=InboxTaskSourceViewModel(repository:held);model.bind(a);model.show();let task=Task {await model.read(expected:model.control)};await held.wait();if mode==0 {task.cancel()} else {model.hide();model.bind(b);model.show()};let current=model.control;if mode==2 {await held.fail()} else {await held.resolve(try await repo.source(a))};await task.value;try expect(model.control==current || mode==0,"Late read/failure changed new owner control");try expect(model.session.source==nil && model.session.choice==nil && model.session.failure==nil,"Cancelled/late source or error exposed");model.bind(a);model.show();try expect(model.session.choice==nil,"ABA revived qualification")}
    let null=InboxTaskSourceViewModel(repository:repo);null.bind(InboxConversationFilesContext(business:101,conversation:902,epoch:804,revision:1));null.show();await null.read(expected:null.control);null.use(expected:null.control);try expect(null.session.choice != nil && null.session.source?.client==nil && null.session.source?.lead==nil,"Explicit null relations treated as missing")
    let denied=InboxTaskSourceViewModel(repository:repo);denied.bind(InboxConversationFilesContext(business:101,conversation:903,epoch:805,revision:1));denied.show();await denied.read(expected:denied.control);denied.use(expected:denied.control);try expect(denied.session.failure == .denied && denied.session.choice==nil,"Denied GET exposed source/ref")
    try expect(InboxConversationFilesViewModel(repository:files).taskSource==nil,"Default composition invented source reader")
    return count
}
