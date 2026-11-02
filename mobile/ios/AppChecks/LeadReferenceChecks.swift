import Foundation
import CRMCore

private actor HeldLeadReferenceRepository:LeadReadRepository {
    var lists:[CheckedContinuation<LeadReadPage,any Error>]=[]
    var profiles:[CheckedContinuation<LeadReadDetail,any Error>]=[]
    func leads(business:Int,search:String) async throws -> LeadReadPage {try await withCheckedThrowingContinuation {lists.append($0)}}
    func lead(business:Int,id:Int) async throws -> LeadReadDetail {try await withCheckedThrowingContinuation {profiles.append($0)}}
    func resolveList(_ p:LeadReadPage) {lists.removeFirst().resume(returning:p)}
    func resolveProfile(_ p:LeadReadDetail) {profiles.removeFirst().resume(returning:p)}
    var listCount:Int {lists.count}
    var profileCount:Int {profiles.count}
}
private struct DeniedLeadReferenceRepository:LeadReadRepository {
    let page:LeadReadPage
    func leads(business:Int,search:String) async throws -> LeadReadPage {page}
    func lead(business:Int,id:Int) async throws -> LeadReadDetail {throw ReadFailure.denied}
}
@MainActor func checkLeadReference(directory:URL) async throws -> Int {
    var count=0
    func expect(_ v:Bool,_ text:String) throws {guard v else {throw ViewModelCheckFailure(message:text)};count += 1}
    let repository=APILeadReadRepository(transport:FixtureLeadReadTransport(directory:directory)),a=InboxConversationFilesContext(business:101,conversation:901,epoch:1,revision:1),b=InboxConversationFilesContext(business:202,conversation:951,epoch:2,revision:1)
    let model=LeadReferenceViewModel(repository:repository);model.bind(a);model.show();try expect(model.session.items.isEmpty && !model.session.loaded,"Lead opened with automatic query")
    let input=model.session.input;model.update("e",input:input);model.update("e\u{0301}",input:input);try expect(SourceTextIdentity.same(model.session.query,"e\u{0301}"),"Lead actual host dropped combining keystroke")
    model.clear(expected:model.control);let before=model.control;await model.search(expected:before);try expect(model.session.items.count==50 && model.session.total==54 && model.session.choice==nil,"Lead actual window/qualification")
    await model.open(3701,expected:before);try expect(model.session.selectedID==nil,"Lead actual stale row control opened profile")
    await model.open(3701,expected:model.control);try expect(model.session.detail?.lead.id==3701 && model.session.canUse && model.session.choice==nil,"Lead row was automatically used")
    model.use(expected:model.control);try expect(model.session.choice?.detail.lead.client_id==1701,"Lead explicit qualified Use")
    let chosen=model.control;model.clearChoice(expected:chosen);model.use(expected:chosen);try expect(model.session.choice==nil,"Lead stale clear/use restored reference")
    model.back(expected:model.control);try expect(model.session.items.count==50 && model.session.detail==nil,"Lead Back lost manual window")
    model.update("  после окна50\t",input:model.session.input);await model.search(expected:model.control);try expect(model.session.items.map(\.id)==[3753] && model.session.query=="  после окна50\t","Lead query beyond50 or raw input changed")
    await model.open(3753,expected:model.control);model.use(expected:model.control);let qualified=model.session.choice!;try expect(qualified.rawQuery=="  после окна50\t" && qualified.detail.lead.id==3753,"Lead selected wrong query/profile")
    model.hide();try expect(model.session.choice==nil && model.session.detail==nil && model.session.query=="  после окна50\t","Lead hide lost raw input or kept stale qualification");let hidden=model.control;await model.open(3753,expected:hidden);try expect(model.session.detail==nil,"Hidden Lead accepted work")
    model.show();model.bind(b);model.show();try expect(model.session.query.isEmpty && model.session.choice==nil,"Lead switched Business inherited input/reference")
    // A repository that ignores cancellation still cannot commit after hide/ABA/new read.
    let held=HeldLeadReferenceRepository(),late=LeadReferenceViewModel(repository:held),page=try await repository.leads(business:101,search:""),profile=try await repository.lead(business:101,id:3701)
    late.bind(a);late.show();let work=Task {await late.search(expected:late.control)}
    for _ in 0..<1000 {if await held.listCount==1 {break};await Task.yield()};try expect(await held.listCount==1,"Held Lead list did not start")
    late.bind(b);late.show();late.update("B query",input:late.session.input);let bControl=late.control;await held.resolveList(page);await work.value;try expect(late.control==bControl && late.session.query=="B query" && late.session.items.isEmpty,"Late Lead list changed Business B")
    late.bind(a);late.show();let list=Task {await late.search(expected:late.control)};for _ in 0..<1000 {if await held.listCount==1 {break};await Task.yield()};await held.resolveList(page);await list.value
    let read=Task {await late.open(3701,expected:late.control)};for _ in 0..<1000 {if await held.profileCount==1 {break};await Task.yield()};try expect(await held.profileCount==1,"Held Lead profile did not start");late.back(expected:late.control);let back=late.control;await held.resolveProfile(profile);await read.value;try expect(late.control==back && late.session.detail==nil && late.session.choice==nil,"Late profile escaped Back")
    let cancel=Task {await late.open(3701,expected:late.control)};for _ in 0..<1000 {if await held.profileCount==1 {break};await Task.yield()};cancel.cancel();await held.resolveProfile(profile);await cancel.value;try expect(late.session.detail==nil && late.session.choice==nil && !late.session.loading,"Cancelled ignored profile qualified a Lead")
    let denied=LeadReferenceViewModel(repository:DeniedLeadReferenceRepository(page:page));denied.bind(a);denied.show();await denied.search(expected:denied.control);await denied.open(3701,expected:denied.control);denied.use(expected:denied.control);try expect(denied.session.failure == .denied && denied.session.choice==nil,"Denied Lead detail conferred qualification");denied.back(expected:denied.control);try expect(denied.session.items.count==50 && denied.session.failure==nil,"Denied Lead Back lost window")
    let files=InboxConversationFilesViewModel(repository:APIInboxConversationFilesRepository(transport:FixtureInboxConversationFilesTransport(directory:directory)),leads:repository);files.bind(a);try expect(files.open(expected:files.control) && files.leadReference?.session.presented==true,"Lead panel not attached to Inbox presentation")
    let child=files.leadReference!;child.update("raw local",input:child.session.input);await files.load(expected:files.control);try expect(child.session.query=="raw local" && child.session.presented,"Inbox metadata load dropped scoped Lead query/panel")
    if let first=files.items.first {files.select(first,expected:files.control);try expect(!child.session.presented,"Lead stayed interactive behind file detail");files.back(expected:files.control);try expect(child.session.presented && child.session.query=="raw local","Lead file Back lost scoped input")}
    files.bind(b);try expect(child.session.context==b && !child.session.presented && child.session.query.isEmpty,"Inbox Business switch left stale Lead panel")
    let absent=InboxConversationFilesViewModel(repository:APIInboxConversationFilesRepository(transport:FixtureInboxConversationFilesTransport(directory:directory)));try expect(absent.leadReference==nil,"Default composition invented Lead repository/authority")
    return count
}
