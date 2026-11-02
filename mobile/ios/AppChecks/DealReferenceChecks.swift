import Foundation
import CRMCore

private actor HeldDealReferenceRepository:DealReadRepository {
    private var pending:[Int:CheckedContinuation<DealReadSource,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    private var count=0
    func deal(business:Int,id:Int) async throws -> DealReadSource {let i=count;count += 1;return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ s:DealReadSource) {pending.removeValue(forKey:i)!.resume(returning:s)}
    func fail(_ i:Int,_ e:ReadFailure) {pending.removeValue(forKey:i)!.resume(throwing:e)}
}
@MainActor func checkDealReference(directory:URL) async throws -> Int {
    var count=0
    func expect(_ v:Bool,_ m:String) throws {guard v else {throw ViewModelCheckFailure(message:m)};count += 1}
    let api=APIDealReadRepository(transport:FixtureDealReadTransport(directory:directory)),a=InboxConversationFilesContext(business:101,conversation:901,epoch:1,revision:1),b=InboxConversationFilesContext(business:202,conversation:951,epoch:2,revision:1),m=DealReferenceViewModel(repository:api)
    m.bind(a);m.show();try expect(m.session.rawInput.isEmpty && m.session.source==nil && !m.session.canRead,"Deal host auto fetched/default target")
    let input=m.session.input;m.update("5",input:input);m.update("57",input:input);m.update("005701",input:input);let old=m.control;await m.read(expected:old);try expect(m.session.source?.id==5701 && m.session.choice==nil,"Deal read failed or automatically selected")
    m.use(expected:old);try expect(m.session.choice==nil,"Deal stale read control selected reference");m.use(expected:m.control);let choice=m.session.choice!;try expect(choice.valid && choice.rawInput=="005701" && choice.source.client==1701,"Deal explicit qualified reference lost supplied input")
    let stale=m.control;m.clearChoice(expected:stale);m.use(expected:stale);try expect(m.session.choice==nil && m.session.source != nil,"Deal local clear or stale Use")
    m.update("5702",input:m.session.input);try expect(m.session.source==nil && m.session.choice==nil,"Deal field edit retained obsolete reference");await m.read(expected:m.control);m.use(expected:m.control);try expect(m.session.choice?.source.lead==nil && m.session.choice?.source.client==1702,"Deal nullable Lead defaulted/aliased")
    m.controlsBlocked={true};let frozen=m.session.rawInput,control=m.control;m.update("5701",input:m.session.input);m.clear(expected:control);m.clearChoice(expected:control);await m.read(expected:control);try expect(m.control==control && m.session.rawInput==frozen && m.session.choice != nil,"External frozen-reference gate bypassed");m.controlsBlocked={false}
    m.update("5704",input:m.session.input);await m.read(expected:m.control);m.use(expected:m.control);try expect(m.session.failure == .denied && m.session.source==nil && m.session.choice==nil && m.session.rawInput=="5704","Denied Deal exposed previous data or lost input")
    m.update("6701",input:m.session.input);await m.read(expected:m.control);try expect(m.session.failure == .invalidPayload && m.session.source==nil,"Foreign Deal source exposed despite selected Business")
    m.hide();m.show();try expect(m.session.rawInput=="6701" && m.session.source==nil,"Deal hide/reopen lost input or restored stale data");m.bind(b);m.show();try expect(m.session.rawInput.isEmpty,"Deal Business switch inherited raw input")
    let held=HeldDealReferenceRepository(),late=DealReferenceViewModel(repository:held),first=try await api.deal(business:101,id:5701),second=try await api.deal(business:101,id:5702);late.bind(a);late.show();late.update("5701",input:late.session.input);let j=Task {await late.read(expected:late.control)};await held.wait(0);late.update("5702",input:late.session.input);let edited=late.control;await held.resolve(0,first);await j.value;try expect(late.control==edited && late.session.rawInput=="5702" && late.session.source==nil,"Late Deal body changed newly typed number")
    let cancelled=Task {await late.read(expected:late.control)};await held.wait(1);cancelled.cancel();await held.resolve(1,second);await cancelled.value;try expect(!late.session.loading && late.session.source==nil && late.session.rawInput=="5702","Ignored GET cancellation exposed a Deal")
    let bj=Task {await late.read(expected:late.control)};await held.wait(2);late.bind(b);late.show();late.update("6701",input:late.session.input);let bControl=late.control;await held.fail(2,.unavailable);await bj.value;try expect(late.control==bControl && late.session.failure==nil && late.session.rawInput=="6701","Late failure displaced new Business input")
    let aj=Task {await late.read(expected:late.control)};await held.wait(3);late.bind(a);late.show();let aba=late.control;await held.resolve(3,try await api.deal(business:202,id:6701));await aj.value;try expect(late.control==aba && late.session.source==nil && late.session.choice==nil && late.session.rawInput.isEmpty,"Deal ABA revived old response/reference")
    let files=InboxConversationFilesViewModel(repository:APIInboxConversationFilesRepository(transport:FixtureInboxConversationFilesTransport(directory:directory)),deals:api);files.bind(a);try expect(files.open(expected:files.control) && files.dealReference?.session.presented==true,"Deal reader missing Inbox panel");let p=files.dealReference!;p.update("005701",input:p.session.input);await p.read(expected:p.control);p.use(expected:p.control);await files.load(expected:files.control);try expect(p.session.rawInput=="005701" && p.session.source==nil && p.session.choice==nil && p.session.presented,"Metadata read lost raw Deal input or kept qualification")
    if let row=files.items.first {files.select(row,expected:files.control);try expect(!p.session.presented,"Deal remained interactive behind file detail");files.back(expected:files.control);try expect(p.session.presented && p.session.rawInput=="005701","File Back lost raw Deal input")}
    files.bind(b);try expect(p.session.context==b && p.session.rawInput.isEmpty && !p.session.presented,"Parent Business change leaked Deal input");let absent=InboxConversationFilesViewModel(repository:APIInboxConversationFilesRepository(transport:FixtureInboxConversationFilesTransport(directory:directory)));try expect(absent.dealReference==nil,"Default composition invented Deal reader")
    return count
}
