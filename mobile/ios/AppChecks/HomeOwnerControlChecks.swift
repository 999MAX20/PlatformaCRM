import Foundation
import CRMCore

@MainActor func checkHomeOwnerControls(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory))
    let a=try await repo.home(business:101),b=try await repo.home(business:202),t=try await repo.today(business:101,day:"2026-10-28"),u=try await repo.today(business:202,day:"2026-10-28")
    let source=ControlledHomeToday(),m=HomeTodayViewModel(repository:source)
    try expect(m.owner==nil && m.homeControl==nil && !m.matches(nil),"Missing Home owner created controls")
    let initial=Task {await m.start(business:101,day:"2026-10-28",epoch:1)};await source.wait(home:1,today:1)
    await m.reloadHome(expected:m.homeControl);await m.reloadToday(expected:m.todayControl)
    try expect(await source.counts()==[1,1],"Pending Home/Today duplicated request")
    await source.resolveHome(0,.success(a));await source.resolveToday(0,.failure(.denied));await initial.value
    try expect(m.home != nil && m.today==nil && m.todayFailure == .denied,"Independent denial erased Home or fabricated Today")
    let oldHome=m.homeControl!,oldToday=m.todayControl!
    let today=Task {await m.reloadToday(expected:oldToday)};await source.wait(home:1,today:2)
    let home=Task {await m.reloadHome(expected:oldHome)};await source.wait(home:2,today:2)
    await m.reloadHome(expected:m.homeControl);await m.reloadToday(expected:m.todayControl)
    try expect(await source.counts()==[2,2],"Independent section retry blocked other section or duplicated pending request")
    await source.resolveToday(1,.success(t));await today.value;await source.resolveHome(1,.success(a));await home.value
    await m.reloadHome(expected:oldHome);await m.reloadToday(expected:oldToday);await m.reloadHome(expected:m.todayControl)
    try expect(await source.counts()==[2,2] && m.home != nil && m.today != nil,"Old/wrong-section control repeated read")
    let presentation=m.homeControl!,before=m.navigationControl!;m.open(.tasks,expected:before);let taskVisit=m.navigationControl!
    try expect(m.takeNavigation(expected:before)==nil && m.takeNavigation(expected:taskVisit) == .tasks && m.takeNavigation(expected:taskVisit)==nil,"Stale navigation consumed new event or event replayed")
    m.open(.inbox,expected:before);m.back(expected:before)
    try expect(m.destination == .tasks,"Old Home callback closed/rerouted current child")
    m.back(expected:taskVisit);m.open(.clients,expected:m.navigationControl);let clientVisit=m.navigationControl!
    m.back(expected:taskVisit);try expect(m.destination == .clients && m.takeNavigation(expected:clientVisit) == .clients,"Old Back closed new child or fresh event lost")
    m.back(expected:clientVisit);await m.reloadHome(expected:presentation)
    try expect(await source.counts()==[2,2] && m.home != nil && m.today != nil,"Old pre-child section callback changed retained projections")
    let prior=m.homeControl!,priorNavigation=m.navigationControl!,late=Task {await m.reloadHome(expected:prior)};await source.wait(home:3,today:2)
    m.reconcileOwner(business:101,epoch:2)
    try expect(await source.counts()==[3,2] && m.owner==nil && m.home==nil && m.today==nil && m.destination==nil,"Same-Business root invalidation issued GET or kept private state")
    let fresh=Task {await m.start(business:101,day:"2026-10-28",epoch:2)};await source.wait(home:4,today:3)
    var redacted=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("home-101.json"))) as! [String:Any];redacted["sections"]=[:]
    let hidden=try JSONDecoder().decode(HomeSummary.self,from:JSONSerialization.data(withJSONObject:redacted))
    await source.resolveHome(3,.success(hidden));await source.resolveToday(2,.success(t));await fresh.value;await source.resolveHome(2,.success(a));await late.value
    await m.reloadHome(expected:prior);await m.reloadToday(expected:oldToday);m.open(.tasks,expected:priorNavigation);m.back(expected:clientVisit)
    try expect(await source.counts()==[4,3] && m.owner?.epoch==2 && m.home?.sections.tasks==nil && m.destination==nil,"Old epoch result/control restored withheld data or route")
    let dayOwner=m.owner!,dayControl=m.todayControl!,changedDay=Task {await m.start(business:101,day:"2026-10-29",epoch:2)};await source.wait(home:5,today:4)
    await source.resolveHome(4,.success(a));await source.resolveToday(3,.success(t));await changedDay.value;await m.reloadToday(expected:dayControl)
    try expect(m.owner != dayOwner && m.today==nil && m.todayFailure == .invalidPayload,"Day change retained old owner or accepted wrong date payload")
    let other=Task {await m.start(business:202,day:"2026-10-28",epoch:3)};await source.wait(home:6,today:5);await source.resolveHome(5,.success(b));await source.resolveToday(4,.success(u));await other.value
    m.open(.inbox,expected:m.navigationControl);m.back(expected:priorNavigation);await m.reloadHome(expected:prior)
    try expect(await source.counts()==[6,5] && m.destination == .inbox && m.home?.business==202 && m.today?.business==202,"Old Business callback affected new retained navigation/summaries")
    return count
}
