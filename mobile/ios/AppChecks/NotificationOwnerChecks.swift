import Foundation
import CRMCore

@MainActor func checkNotificationOwnerControls(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func fixture<T:Decodable>(_ name:String,_ type:T.Type) throws -> T {try JSONDecoder().decode(type,from:Data(contentsOf:directory.appendingPathComponent(name+".json")))}
    let a=try fixture("notifications-101",NotificationPage.self),b=try fixture("notifications-202",NotificationPage.self),appointment=try fixture("appointment-101-501",AppointmentDetail.self)
    let source=ControlledNotifications(),m=NotificationCenterViewModel(repository:source)
    try expect(m.control==nil && !m.matches(nil),"Missing notification owner produced control")
    let load=Task {await m.load(business:101,epoch:1)};await source.waitPage(0)
    await m.retryList(expected:m.control);try expect(await source.counts()==[1,0],"Pending list callback duplicated read")
    await source.resolvePage(0,.success(a));await load.value
    let list=m.control!;m.search("Alpha",expected:list);m.filterCategory("sales",previous:nil,expected:list);m.filterUnread(true,previous:false,expected:list)
    m.filterCategory("finance",previous:nil,expected:list);m.filterUnread(false,previous:false,expected:list)
    try expect(m.query=="Alpha" && m.category=="sales" && m.unreadOnly && m.visible.map(\.id)==[2101],"Current filters failed or old field snapshot overwrote them")
    m.open(id:2102,expected:list);m.open(id:999,expected:list);try expect(m.selectedID==nil,"Filtered-out/unknown notification row opened")
    m.open(id:2101,expected:list);let card=m.control!,readMarkers=m.items.map(\.read_at)
    m.close(expected:list);m.search("leak",expected:list);try expect(m.selectedID==2101 && m.query=="Alpha" && m.selected?.unread==true,"Old list callback closed card/changed filter/read marker")
    let opening=Task {await m.openTarget(expected:card)};await source.waitTarget(0)
    let targetVisit=m.control!;await m.openTarget(expected:targetVisit);m.close(expected:card);m.backTarget(expected:card);await m.retryList(expected:targetVisit)
    try expect(await source.counts()==[1,1] && m.targetLoading && m.selectedID==2101,"Old card callback closed/repeated pending target")
    await source.resolveTarget(0,.success(appointment));await opening.value
    try expect(m.target?.appointment.id==501 && m.items.map(\.read_at)==readMarkers && m.selected?.unread==true,"Target read marked notification read or changed identity")
    m.backTarget(expected:targetVisit);let returned=m.control!
    try expect(!m.targetActive && m.target==nil && m.selectedID==2101,"Current target Back lost notification card")
    let retry=Task {await m.openTarget(expected:returned)};await source.waitTarget(1)
    m.backTarget(expected:targetVisit);m.close(expected:returned);await m.openTarget(expected:card)
    try expect(await source.counts()==[1,2] && m.targetLoading,"Old same-card target/Back reactivated or closed new visit")
    await source.resolveTarget(1,.failure(.denied));await retry.value
    try expect(m.target==nil && m.targetFailure == .denied && m.selectedID==2101,"Denied target reused cached payload or erased parent")
    let late=Task {await m.openTarget(expected:m.control)};await source.waitTarget(2);let old=m.control!,before=await source.counts()
    m.reconcileOwner(business:101,epoch:2)
    try expect(await source.counts()==before && m.business==nil && m.scopeEpoch==nil && m.items.isEmpty && m.control==nil && m.target==nil,"Root same-Business epoch failed local invalidation or issued GET")
    await source.resolveTarget(2,.success(appointment));await late.value
    try expect(m.target==nil && m.business==nil,"Old epoch target reply resurrected private payload")
    let current=Task {await m.load(business:101,epoch:2)};await source.waitPage(1);await source.resolvePage(1,.success(a));await current.value
    let fresh=m.control!;m.search("Private-current",expected:fresh);m.search("old",expected:old);m.filterCategory("finance",previous:nil,expected:old);m.filterUnread(true,previous:false,expected:old);m.open(id:2101,expected:old);await m.retryList(expected:old);await m.openTarget(expected:old)
    try expect(await source.counts()==[2,3] && m.query=="Private-current" && m.category==nil && !m.unreadOnly && m.selectedID==nil,"Old epoch controls affected fresh same-Business list")
    m.search("",expected:fresh);m.open(id:2102,expected:fresh);let legacy=m.control!;await m.openTarget(expected:legacy)
    try expect(await source.counts()==[2,3] && !m.targetActive,"Legacy Lead path became Appointment by numeric identity")
    m.close(expected:legacy);m.open(id:2101,expected:m.control);let reopened=m.control!;m.close(expected:legacy)
    try expect(m.control==reopened && m.selectedID==2101,"Old notification Back closed new selected card")
    m.close(expected:reopened);let beforeReload=m.control!,reload=Task {await m.retryList(expected:beforeReload)};await source.waitPage(2)
    m.reconcileOwner(business:101,epoch:3);await source.resolvePage(2,.success(a));await reload.value
    try expect(m.items.isEmpty && m.business==nil && m.control==nil,"Late list repopulated same Business new epoch")
    let other=Task {await m.load(business:202,epoch:4)};await source.waitPage(3);await source.resolvePage(3,.success(b));await other.value
    m.search("old",expected:beforeReload);await m.retryList(expected:beforeReload);await m.openTarget(expected:reopened);m.close(expected:reopened)
    try expect(await source.counts()==[4,3] && m.business==202 && m.items.map(\.id)==[2201] && m.selectedID==nil && m.query.isEmpty,"Old Business callbacks changed new owner or issued read")
    return count
}
