import Foundation
import CRMCore

@MainActor func checkClientDirectoryControls(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func page(_ b:Int) throws -> ClientList {try JSONDecoder().decode(ClientList.self,from:Data(contentsOf:directory.appendingPathComponent("clients-\(b).json")))}
    let a=try page(101),b=try page(202),source=ControlledClients(),m=ClientDirectoryViewModel(repository:source)
    var request=0
    func load(_ business:Int,_ epoch:Int) async {let n=request;request += 1;let job=Task {await m.load(business:business,epoch:epoch)};await source.wait(n);await source.resolve(n,.success(business==101 ? a:b));await job.value}
    try expect(m.control==nil && !m.matches(nil),"Missing owner supplied Directory control")
    await load(101,1);let original=m.control!
    m.search("Alpha",expected:original);try expect(m.visible.map(\.id)==[701],"Current captured Directory query did not filter loaded page")
    try expect(!m.open(id:702,expected:original) && !m.open(id:999,expected:original),"Filtered-out or unknown stale row opened")
    try expect(m.open(id:701,expected:original),"Current row did not open")
    let firstCard=m.control!;try expect(!m.back(expected:original) && m.selectedID==701,"Old list Back closed selected card")
    m.search("overwrite",expected:original);try expect(m.query=="Alpha","Old list binding changed current card query")
    let old=a.items[0],updated=ClientContact(id:old.id,title:"Fresh",phone:nil,email:nil)
    m.refreshContact(business:202,contact:updated,expected:firstCard);try expect(m.items[0]==old,"Foreign Business contact callback accepted")
    m.refreshContact(business:101,contact:updated,expected:firstCard);try expect(m.items[0]==updated && m.control==firstCard && m.total==a.summary.total,"Valid contact callback changed selection/count or was rejected")
    try expect(m.back(expected:firstCard) && m.query=="Alpha","Current Back lost local query")
    let returned=m.control!;try expect(returned != original && !m.open(id:701,expected:original),"Old row became valid again after Back")
    m.search("",expected:returned);try expect(m.open(id:702,expected:returned),"New selected row unavailable")
    let secondCard=m.control!;m.refreshContact(business:101,contact:old,expected:firstCard)
    try expect(m.items[0]==updated && !m.back(expected:firstCard) && m.control==secondCard,"Old profile callback/Back affected different current target")
    _=m.back(expected:secondCard);let beforeReload=m.control!
    let reload=Task {await m.retry(expected:beforeReload)};await source.wait(request);request += 1
    let pending=m.control!;await m.retry(expected:pending);m.search("old",expected:beforeReload)
    try expect(await source.requests()==request && m.query.isEmpty && !m.openDraft(expected:pending),"Pending Directory retry duplicated read or old query/create changed state")
    await source.resolve(request-1,.success(a));await reload.value
    try expect(!m.matches(beforeReload) && m.control==pending,"Directory load generation not captured")
    await m.retry(expected:beforeReload);try expect(await source.requests()==request,"Old load retry issued a read")
    let oldEpoch=m.control!;await load(101,2);m.search("Beta",expected:m.control);let newEpoch=m.control!
    m.search("private-old",expected:oldEpoch);await m.retry(expected:oldEpoch)
    try expect(!m.back(expected:oldEpoch) && !m.open(id:701,expected:oldEpoch) && !m.openDraft(expected:oldEpoch) && m.query=="Beta" && m.control==newEpoch,"Same Business new epoch accepted old controls")
    await load(202,3);let current=m.control!;m.search("Current",expected:current);let reads=await source.requests()
    m.search("leak",expected:oldEpoch);await m.retry(expected:oldEpoch);m.refreshContact(business:101,contact:updated,expected:oldEpoch)
    try expect(await source.requests()==reads && m.business==202 && m.items==b.items && m.query=="Current" && !m.back(expected:oldEpoch),"Cross-Business stale callbacks changed data or sent GET")
    m.reconcileOwner(business:202,epoch:4);await m.retry(expected:current);try expect(await source.requests()==reads && m.control==nil,"Cleared Directory resurrected from old retry")

    let transport=SearchTransport(directory),owner=ClientDirectoryViewModel(repository:APIReadRepository(transport:transport))
    await owner.load(business:101,epoch:10);let entry=owner.control!,beforeEntry=await transport.recorded()
    try expect(owner.openDraft(expected:entry),"Guarded create entry did not open existing local draft")
    let draft=owner.draft.session.selection!;owner.draft.update(.fullName,"Retained private",draft);let ownDraft=owner.control!
    try expect(!owner.openSearch(expected:entry) && !owner.back(expected:entry) && !owner.openDraft(expected:entry) && owner.draft.session.selection==draft && owner.draft.session.values.fullName=="Retained private","Old entry callback closed/reopened current private draft")
    try expect(owner.openSearch(expected:ownDraft) && owner.draft.session.selection==nil,"Current search entry did not close only own draft")
    let search=owner.serverSearch!.session.selection!,searchControl=owner.control!
    try expect(!owner.back(expected:ownDraft) && owner.serverSearch!.session.selection==search,"Old Back closed current search")
    try expect(await transport.recorded()==beforeEntry && owner.back(expected:searchControl),"Local form/search entry unexpectedly requested data")

    let profiles=ControlledProfiles(),profile=ClientProfileViewModel(repository:profiles)
    let start=Task {await profile.load(business:101,id:701,epoch:1)};await profiles.wait(0)
    let p1=profile.readSelection!;await profile.retry(expected:p1,epoch:1)
    await profiles.resolve(0,.failure(.unavailable));await start.value
    var callbacks=0
    let retry=Task {await profile.retry(expected:p1,epoch:1,onContact:{_,_ in callbacks += 1})};await profiles.wait(1)
    let p2=profile.readSelection!;await profile.retry(expected:p1,epoch:1)
    let detail=try JSONDecoder().decode(ClientProfile.self,from:Data(contentsOf:directory.appendingPathComponent("client-101-701.json")))
    await profiles.resolve(1,.success(detail));await retry.value
    try expect(profile.detail != nil && callbacks==1 && p1 != p2,"Current profile retry/result failed")
    await profile.retry(expected:p1,epoch:1);await profile.retry(expected:p2,epoch:2)
    try expect(profile.readSelection==p2 && profile.detail != nil,"Old read generation/foreign epoch retried current profile")
    profile.clear();await profile.retry(expected:p2,epoch:1)
    try expect(profile.readSelection==nil && profile.detail==nil && callbacks==1,"Stale profile retry resurrected cleared state")
    return count
}
