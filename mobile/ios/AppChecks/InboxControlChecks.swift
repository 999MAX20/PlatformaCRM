import Foundation
import CRMCore

@MainActor func checkInboxControls(directory:URL) async throws -> Int {
    var count=0
    func expect(_ v:Bool,_ message:String) throws {guard v else {throw ViewModelCheckFailure(message:message)};count += 1}
    func fixture<T:Decodable>(_ name:String,_ type:T.Type) throws -> T {try JSONDecoder().decode(type,from:Data(contentsOf:directory.appendingPathComponent(name+".json")))}
    let a=try fixture("inbox-101",InboxList.self),b=try fixture("inbox-202",InboxList.self),thread=try fixture("inbox-101-901",InboxThread.self)
    let source=ControlledInbox(),m=InboxViewModel(repository:source)
    try expect(m.control==nil && !m.matches(nil),"Missing Inbox owner produced captured control")
    let load=Task {await m.load(business:101,epoch:1)};await source.waitPage(0);await source.resolvePage(0,.success(a));await load.value
    let list=m.control!;m.search("Alpha",expected:list);m.filterUnread(true,previous:false,expected:list)
    try expect(m.visible.map(\.id)==[901] && m.query=="Alpha" && m.unreadOnly,"Current list controls lost filter semantics")
    m.filterUnread(false,previous:false,expected:list);try expect(m.unreadOnly,"Old unread-toggle snapshot overwrote newer filter")
    await m.open(id:902,expected:list);await m.open(id:999,expected:list);try expect(await source.counts()==[1,0],"Filtered-out/unknown Inbox row issued a read")
    let opening=Task {await m.open(id:901,expected:list)};await source.waitThread(0)
    let pending=m.control!;m.search("old binding",expected:list);m.filterUnread(false,previous:true,expected:list);await m.retryList(expected:list);await m.open(id:901,expected:list)
    try expect(await source.counts()==[1,1] && m.query=="Alpha" && m.unreadOnly && m.control==pending,"Old list callback changed pending thread or duplicated request")
    await source.resolveThread(0,.success(thread));await opening.value
    let selected=m.control!,target=m.threadSelection!,context=m.reply.session.context!
    m.openReply(context,expected:selected);let draft=m.reply.session.selection!,draftControl=m.control!;m.reply.update("Retained private reply",draft)
    m.openReply(context,expected:selected);m.back(expected:selected,thread:target);await m.retryThread(expected:target,control:selected)
    try expect(await source.counts()==[1,1] && m.reply.session.selection==draft && m.reply.session.text=="Retained private reply","Old thread entry/Back/retry closed or reset newer draft")
    m.openReply(context,expected:draftControl);try expect(m.reply.session.selection==draft,"Duplicate entry reset current reply generation")
    m.reply.close(draft);m.openReply(context,expected:draftControl);let reopened=m.reply.session.selection!
    try expect(reopened != draft && m.reply.session.text=="Retained private reply","Current reply reopen lost own raw text")
    m.back(expected:draftControl,thread:target);try expect(m.selectedID==901 && m.reply.session.selection==reopened,"Old parent Back closed reopened reply")
    m.back(expected:m.control,thread:m.threadSelection);try expect(m.selectedID==nil && m.query=="Alpha" && m.unreadOnly,"Current thread Back lost list filters")
    await m.open(id:901,expected:list);try expect(await source.counts()==[1,1],"Old row reactivated after returning to same list")
    let beforeRetry=m.control!,retry=Task {await m.retryList(expected:beforeRetry)};await source.waitPage(1)
    await m.retryList(expected:m.control);m.search("old",expected:beforeRetry)
    try expect(await source.counts()==[2,1] && m.query=="Alpha","Pending current/old list retry duplicated read or changed query")
    await source.resolvePage(1,.success(a));await retry.value;await m.retryList(expected:beforeRetry)
    try expect(await source.counts()==[2,1],"Previous list generation retry issued GET")
    let oldEpoch=m.control!,next=Task {await m.load(business:101,epoch:2)};await source.waitPage(2);await source.resolvePage(2,.success(a));await next.value
    let own=m.control!;m.search("Current",expected:own);m.search("leak",expected:oldEpoch);m.filterUnread(true,previous:false,expected:oldEpoch);await m.open(id:901,expected:oldEpoch);await m.retryList(expected:oldEpoch)
    try expect(await source.counts()==[3,1] && m.query=="Current" && !m.unreadOnly && m.reply.session.text.isEmpty,"Same Business new epoch accepted old filter/row/retry/raw")
    let foreign=Task {await m.load(business:202,epoch:3)};await source.waitPage(3);await source.resolvePage(3,.success(b));await foreign.value
    m.search("leak",expected:own);await m.retryList(expected:own);try expect(await source.counts()==[4,1] && m.items.map(\.id)==[951] && m.query.isEmpty,"Foreign owner received old filter/retry")
    m.clear();await m.retryList(expected:m.control);await m.open(id:951,expected:own);try expect(await source.counts()==[4,1] && m.control==nil,"Cleared Inbox resurrected from captured controls")
    return count
}

@MainActor func checkInboxInspectorPresentation(directory:URL) async throws -> Int {
    var count=0
    func expect(_ v:Bool,_ message:String) throws {guard v else {throw ViewModelCheckFailure(message:message)};count += 1}
    let transport=SearchTransport(directory),m=InboxViewModel(repository:APIReadRepository(transport:transport)),links=m.clientLinks!
    await m.load(business:101,epoch:10);await m.open(id:901,expected:m.control)
    let thread=m.thread!,entry=m.control!,idle=links.presentation!,before=await transport.recorded()
    await m.openClient(idle,expected:entry);let first=links.presentation!,parent=m.control!
    try expect(links.profile.detail?.client.id==701 && first != idle && first.request==idle.request,"Current inspector entry/generation failed")
    try expect(await transport.recorded().count==before.count+2 && m.thread?.messages.map(\.id)==thread.messages.map(\.id),"Inspector changed message history or read sequence")
    let reads=await transport.recorded();await links.open(presentation:idle);try expect(await transport.recorded()==reads && !links.back(presentation:idle),"Old inspector entry/Back changed active same-parent child")
    try expect(links.back(presentation:first) && links.profile.detail==nil,"Current inspector Back failed")
    let closed=links.presentation!;await m.openClient(closed,expected:parent);let second=links.presentation!
    try expect(second.request==first.request && second != first && links.profile.detail != nil,"Same-parent inspector reopen did not rotate presentation")
    let currentReads=await transport.recorded();await links.open(presentation:first);await m.openClient(closed,expected:parent)
    try expect(await transport.recorded()==currentReads && !links.back(presentation:first) && links.presentation==second,"Old same-parent retry/Back/entry closed or reloaded reopened inspector")
    let owner=m.control!,context=m.reply.session.context!;m.openReply(context,expected:owner)
    try expect(m.reply.session.selection==nil && links.presentation==second,"Stale reply entry displaced active inspector")
    _=links.back(presentation:second);m.openReply(context,expected:owner);let draft=m.reply.session.selection!
    m.reply.update("Private",draft);await m.openClient(links.presentation,expected:owner)
    try expect(m.reply.session.selection==draft && m.reply.session.text=="Private" && links.selectedID==nil,"Old inspector action closed or exposed current private form")
    m.reconcileHandoffOwner(business:101,epoch:11);let atClear=await transport.recorded();await links.open(presentation:second);await m.openClient(second,expected:owner)
    try expect(await transport.recorded()==atClear && links.presentation==nil && m.thread==nil,"Off-tab new epoch accepted old inspector presentation")
    return count
}
