import Foundation
import CRMCore

@MainActor func checkLoadedSearchControls(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let page=try JSONDecoder().decode(TaskPage.self,from:Data(contentsOf:directory.appendingPathComponent("tasks-101.json")))
    func feed(_ epoch:Int,_ generation:Int)->LoadedSearchFeed {LoadedSearchFeed(business:101,epoch:epoch,sources:[LoadedSearchSource(kind:.tasks,token:LoadedSearchToken(kind:.tasks,business:101,epoch:epoch,generation:generation),coverage:.loaded,rows:page.items.map {LoadedSearchRow(id:$0.id,title:$0.title)})])}
    let transport=SearchTransport(directory),m=LoadedSearchViewModel(repository:APIReadRepository(transport:transport))
    try expect(m.control==nil && !m.matches(nil) && m.sourceTab(.tasks,expected:nil)==nil,"Missing loaded-search owner created entry action")
    m.reconcile(feed(1,1));let input=m.inputControl!;m.search("Alpha",input:input);let list=m.control!,hit=m.matches.first!
    let initialRequests=await transport.recorded()
    try expect(m.sourceTab(.clients,expected:list)==2 && initialRequests.isEmpty,"Opening source tab inferred a loaded row or issued GET")
    m.search("Beta",input:input);await m.open(hit,expected:list)
    try expect(await transport.recorded().isEmpty && m.selected==nil,"Filtered-out loaded result opened")
    m.search("Alpha",input:input);let opening=m.control!;await transport.holdDetails()
    let first=Task {await m.open(hit,expected:opening)};await transport.wait(0);let card=m.control!
    await m.open(hit,expected:list);await m.retry(expected:card);m.back(expected:list);m.search("old",expected:list)
    try expect(await transport.recorded().count==1 && m.selected==hit && m.query=="Alpha" && m.sourceTab(.tasks,expected:card)==nil,"Old list/pending retry/entry affected selected result")
    await transport.resolve(0,ReadResponse(status:403,data:Data()));await first.value
    try expect(m.failure == .denied && m.detail==nil && m.matches.isEmpty,"Denied target restored list title/body")
    let retry=Task {await m.retry(expected:m.control)};await transport.wait(1);let retried=m.control!
    m.back(expected:card);await m.retry(expected:card)
    try expect(await transport.recorded().count==2 && m.control==retried,"Old Back/retry changed newer result visit")
    let data=try Data(contentsOf:directory.appendingPathComponent("task-101-1101.json"))
    await transport.resolve(1,ReadResponse(status:200,data:data));await retry.value;m.back(expected:retried)
    try expect(m.query=="Alpha" && m.selected==nil && m.matches.isEmpty && m.detail==nil,"Back lost query or unsuppressed old denied candidate")
    m.reconcile(feed(1,2));let fresh=m.control!,newHit=m.matches.first!;await m.open(hit,expected:list);m.search("old",expected:list)
    try expect(await transport.recorded().count==2 && m.query=="Alpha" && m.sourceTab(.tasks,expected:list)==nil,"Old feed control entered refreshed source")
    let leaving=Task {await m.open(newHit,expected:fresh)};await transport.wait(2);let oldVisit=m.control!;m.back(expected:oldVisit)
    let reopen=Task {await m.open(newHit,expected:m.control)};await transport.wait(3);let newVisit=m.control!
    m.back(expected:oldVisit);await m.retry(expected:oldVisit)
    try expect(await transport.recorded().count==4 && m.control==newVisit,"Old same-hit Back/retry closed or repeated reopened result")
    var redacted=try JSONSerialization.jsonObject(with:data) as! [String:Any];var task=redacted["task"] as! [String:Any];task["title"]=NSNull();redacted["task"]=task
    await transport.resolve(3,ReadResponse(status:200,data:try JSONSerialization.data(withJSONObject:redacted)));await reopen.value
    await transport.resolve(2,ReadResponse(status:200,data:data));await leaving.value
    try expect(m.detail?.title==nil && m.failure==nil && m.matches.isEmpty,"Late old read restored withheld title")
    m.reconcile(feed(2,3));m.search("new",expected:list);m.back(expected:newVisit);await m.retry(expected:retried)
    try expect(await transport.recorded().count==4 && m.feed.epoch==2 && m.query.isEmpty && m.selected==nil && m.sourceTab(.clients,expected:oldVisit)==nil,"Old owner entry/query/Back/retry affected new same-Business epoch")
    let appointment=try JSONDecoder().decode(AppointmentDetail.self,from:Data(contentsOf:directory.appendingPathComponent("appointment-101-501.json")))
    let appointments=LoadedSearchFeed(business:101,epoch:3,sources:[LoadedSearchSource(kind:.appointments,token:LoadedSearchToken(kind:.appointments,business:101,epoch:3,generation:4),coverage:.loaded,rows:[LoadedSearchRow(id:501,title:appointment.appointment.title)])])
    m.reconcile(appointments);m.search("Synthetic",expected:m.control);let appointmentHit=m.matches.first!
    let invalid=Task {await m.open(appointmentHit,expected:m.control)};await transport.wait(4)
    var invalidJSON=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-101-501.json"))) as! [String:Any]
    var invalidRow=invalidJSON["appointment"] as! [String:Any];invalidRow["end_at"]=invalidRow["start_at"];invalidJSON["appointment"]=invalidRow
    await transport.resolve(4,ReadResponse(status:200,data:try JSONSerialization.data(withJSONObject:invalidJSON)));await invalid.value
    try expect(m.failure == .invalidPayload && m.detail==nil && !m.matches.contains(appointmentHit),"Malformed Appointment range bypassed existing independent target validation")
    count += try await checkLoadedSearchExactHeaders(directory:directory)
    count += try await checkLoadedSearchFeedVisits(directory:directory)
    count += try await checkLoadedSearchQueryWindows(directory:directory)
    return count
}

@MainActor private func checkLoadedSearchExactHeaders(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let cases=(try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("loaded-search-exact-header-cases.json"))) as! [String:Any])["cases"] as! [[String:Any]]
    for (index,row) in cases.enumerated() {
        let before=row["before_title"] as! String,after=row["after_title"] as? String,changed=row["changed"] as! Bool,epoch=2100+index
        for kind in LoadedSearchKind.allCases {
            let id:Int,file:String,field:String
            switch kind {case .appointments:id=501;file="appointment-101-501";field="appointment";case .clients:id=701;file="client-101-701";field="client";case .inbox:id=901;file="inbox-101-901";field="conversation";case .tasks:id=1101;file="task-101-1101";field="task"}
            let sourceCoverage:LoadedSearchCoverage=index%2==0 ? .loaded:.partial
            func feed(_ title:String?,_ generation:Int=1,_ epoch:Int)->LoadedSearchFeed {LoadedSearchFeed(business:101,epoch:epoch,sources:[LoadedSearchSource(kind:kind,token:LoadedSearchToken(kind:kind,business:101,epoch:epoch,generation:generation),coverage:sourceCoverage,rows:[LoadedSearchRow(id:id,title:title)])])}
            func response(_ title:String?) throws -> ReadResponse {
                var object=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent(file+".json"))) as! [String:Any],entity=object[field] as! [String:Any]
                entity["title"]=title.map {$0 as Any} ?? NSNull();object[field]=entity
                return ReadResponse(status:200,data:try JSONSerialization.data(withJSONObject:object))
            }
            let transport=SearchTransport(directory),model=LoadedSearchViewModel(repository:APIReadRepository(transport:transport))
            model.reconcile(feed(before,1,epoch));model.search(" SHARED ",input:model.inputControl);let oldList=model.control!,oldHit=model.matches.first!
            model.reconcile(feed(after,1,epoch));try expect((model.control != oldList)==changed,"Raw provided header change retained old UI feed control")
            if changed {await model.open(oldHit,expected:oldList);model.search("old input",expected:oldList)}
            let noReads=await transport.recorded();try expect(noReads.isEmpty && model.selected==nil && model.query==" SHARED ","Header reconcile/query or old row issued request/overwrote input")
            try expect(LoadedSearchHeader.same(model.feed.source(kind)?.rows.first?.title,after) && model.coverage(model.feed.source(kind)!)==sourceCoverage,"Header reconcile changed source bytes/coverage")
            model.reconcile(feed(before,2,epoch));let current=model.control!,hit=model.matches.first!;await transport.holdDetails()
            let reading=Task {await model.open(hit,expected:current)};await transport.wait(0);let card=model.control!
            await transport.resolve(0,try response(after));await reading.value
            let actual=kind == .clients ? model.profile.detail?.client.title:model.detail?.title
            try expect(model.failure==nil && !model.loading && LoadedSearchHeader.same(actual,after),"Independent detail did not retain exact read title")
            try expect((model.suppressed[hit.id] != nil)==changed && model.matches.contains(hit) == !changed,"Changed/withheld independent header silently restored old list title")
            try expect(model.coverage(model.feed.source(kind)!) == (changed ? .partial:sourceCoverage),"Suppression invented complete coverage")
            if changed {
                let retry=Task {await model.retry(expected:card)};await transport.wait(1);await transport.resolve(1,try response(before));await retry.value
                try expect(model.suppressed[hit.id]==hit.token && model.matches.isEmpty,"Matching independent reread unsuppressed older provided header")
            }
            model.back(expected:model.control);try expect(model.query==" SHARED " && model.selected==nil && model.detail==nil && model.profile.detail==nil,"Back lost raw query or retained independent detail")
            model.reconcile(feed(before,3,epoch));try expect(model.matches.count==1 && model.suppressed.isEmpty,"Fresh provided source token failed to clear scoped suppression")
            let fresh=model.control!,freshHit=model.matches.first!,heldIndex=changed ? 2:1
            let late=Task {await model.open(freshHit,expected:fresh)};await transport.wait(heldIndex)
            model.reconcile(feed(after,3,epoch))
            if changed {try expect(model.selected==nil && !model.loading,"Changed same-token header retained selected old hit")}
            await transport.resolve(heldIndex,try response(before));await late.value
            try expect(changed ? model.selected==nil && model.detail==nil && model.profile.detail==nil : model.selected==freshHit,"Late old raw-header read restored replaced title/selection")
            let stale=model.control;model.reconcile(feed(before,4,epoch+100));model.search("old epoch",expected:stale);await model.retry(expected:stale)
            try expect(model.query.isEmpty && model.selected==nil && model.feed.epoch==epoch+100,"Old header control affected new same-Business epoch")
            let requests=await transport.recorded();try expect(requests.allSatisfy {$0.path=="/api/mobile/v1/\(kind == .inbox ? "inbox":kind.rawValue)/\(id)/" && $0.query==(kind == .inbox ? ["business":"101","limit":"30"]:["business":"101"])},"Header validation invented request or omitted scoped existing route")
        }
    }
    return count
}

@MainActor private func checkLoadedSearchFeedVisits(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    func feed(_ title:String,_ extra:Bool=false)->LoadedSearchFeed {
        var sources=[LoadedSearchSource(kind:.tasks,token:LoadedSearchToken(kind:.tasks,business:101,epoch:2400,generation:1),coverage:.loaded,rows:[LoadedSearchRow(id:1101,title:title)])]
        if extra {sources.append(LoadedSearchSource(kind:.clients,token:LoadedSearchToken(kind:.clients,business:101,epoch:2400,generation:1),coverage:.partial,rows:[LoadedSearchRow(id:701,title:"Shared extra")]))}
        return LoadedSearchFeed(business:101,epoch:2400,sources:sources)
    }
    let transport=SearchTransport(directory),model=LoadedSearchViewModel(repository:APIReadRepository(transport:transport))
    let original="Shared e\u{301}",changed="Shared é"
    model.reconcile(feed(original));model.search("Shared",input:model.inputControl);let old=model.control!,hit=model.matches.first!
    model.reconcile(feed(original));try expect(model.control==old,"Identical exact feed reconstruction broke continuous input")
    model.reconcile(feed(changed));model.reconcile(feed(original));let current=model.control!
    model.search("stale input",expected:old);await model.open(hit,expected:old)
    let empty=await transport.recorded();try expect(current != old && empty.isEmpty && model.query=="Shared" && model.sourceTab(.tasks,expected:old)==nil,"Feed A-B-A revived stale input/row/source-tab callback")
    await transport.holdDetails();let reading=Task {await model.open(hit,expected:current)};await transport.wait(0);let card=model.control!
    model.reconcile(feed(original,true));let replacement=model.control!
    model.back(expected:card);await model.retry(expected:card)
    let pending=await transport.recorded();try expect(model.selected==hit && model.loading && replacement != card && pending.count==1,"Unrelated source feed changed read ticket/selection or allowed old card action")
    var object=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-101-1101.json"))) as! [String:Any],task=object["task"] as! [String:Any];task["title"]=original;object["task"]=task
    await transport.resolve(0,ReadResponse(status:200,data:try JSONSerialization.data(withJSONObject:object)));await reading.value
    try expect(!model.loading && model.failure==nil && LoadedSearchHeader.same(model.detail?.title,original) && model.selected==hit,"Unrelated feed update stranded valid independent detail read")
    model.back(expected:model.control);model.search("Shared e",expected:model.control)
    try expect(model.selected==nil && model.detail==nil && model.feed.source(.clients)?.coverage == .partial,"Current Back/input failed after independent read across unrelated source update")
    return count
}

@MainActor private func checkLoadedSearchQueryWindows(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let cases=(try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("loaded-search-query-window-cases.json"))) as! [String:Any])["cases"] as! [[String:Any]]
    for (index,row) in cases.enumerated() {
        let before=row["before"] as! String,after=row["after"] as! String,title=row["title"] as! String,changed=row["changed"] as! Bool,epoch=2700+index
        for kind in LoadedSearchKind.allCases {
            let id:Int,file:String,field:String
            switch kind {case .appointments:id=501;file="appointment-101-501";field="appointment";case .clients:id=701;file="client-101-701";field="client";case .inbox:id=901;file="inbox-101-901";field="conversation";case .tasks:id=1101;file="task-101-1101";field="task"}
            let coverage:LoadedSearchCoverage=index%2==0 ? .loaded:.partial
            func feed(_ epoch:Int)->LoadedSearchFeed {LoadedSearchFeed(business:101,epoch:epoch,sources:[LoadedSearchSource(kind:kind,token:LoadedSearchToken(kind:kind,business:101,epoch:epoch,generation:1),coverage:coverage,rows:[LoadedSearchRow(id:id,title:title)])])}
            let transport=SearchTransport(directory),model=LoadedSearchViewModel(repository:APIReadRepository(transport:transport));let provided=feed(epoch)
            model.reconcile(provided);let input=model.inputControl!;model.search(before,input:input);let old=model.control!,hit=model.matches.first!;model.search(after,input:input);let current=model.control!
            try expect(model.query.utf8.elementsEqual(after.utf8) && model.inputControl==input,"Raw search query lost bytes or invalidated continuous input mid-typing")
            try expect((current != old)==changed && model.matches==[hit],"Changed raw query kept old result action window or changed same provided row")
            if changed {await model.open(hit,expected:old);model.search("old action-input",expected:old);try expect(model.sourceTab(kind,expected:old)==nil,"Old raw query window entered source tab")}
            let noReads=await transport.recorded();try expect(noReads.isEmpty && model.selected==nil && model.query.utf8.elementsEqual(after.utf8),"Raw query/stale same-row action made GET or overwrote current query")
            try expect(model.feed==provided && model.coverage(model.feed.source(kind)!)==coverage && model.suppressed.isEmpty,"Raw query altered provided source/token/coverage/suppression")
            model.search(after,input:input);try expect(model.control==current && model.inputControl==input,"Byte-identical callback advanced query action window")
            model.search(before,input:input);model.search(after,input:input)
            if changed {await model.open(hit,expected:current);try expect(model.control != current && model.sourceTab(kind,expected:current)==nil,"Raw query A-B-A revived old same-row/source action")}
            let ready=model.control!;try expect(model.sourceTab(kind,expected:ready)==kind.tab,"Current raw query window could not enter source locally")
            await transport.holdDetails();let reading=Task {await model.open(hit,expected:ready)};await transport.wait(0);let card=model.control!
            model.search("hidden input",input:input);await model.open(hit,expected:ready);await model.retry(expected:card)
            let pending=await transport.recorded();try expect(model.inputControl==nil && model.loading && model.query.utf8.elementsEqual(after.utf8) && pending.count==1,"Old input/row or pending Retry altered selected detail/read")
            var object=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent(file+".json"))) as! [String:Any],entity=object[field] as! [String:Any];entity["title"]=title;object[field]=entity
            await transport.resolve(0,ReadResponse(status:200,data:try JSONSerialization.data(withJSONObject:object)));await reading.value
            let actual=kind == .clients ? model.profile.detail?.client.title:model.detail?.title
            try expect(!model.loading && model.failure==nil && LoadedSearchHeader.same(actual,title) && model.suppressed.isEmpty,"Query window invalidated independent read ticket/title")
            model.back(expected:model.control);let returned=model.inputControl!;model.search("old after Back",input:input);await model.open(hit,expected:ready)
            let afterBack=await transport.recorded();try expect(returned != input && model.query.utf8.elementsEqual(after.utf8) && model.selected==nil && afterBack.count==1,"Back revived prior query input/action or lost raw input")
            model.search("__not_in_loaded_title__",input:returned);try expect(model.matches.isEmpty && model.showsNoMatches && model.coverage(model.feed.source(kind)!)==coverage && model.feed==provided,"Local no-match invented source/coverage changes")
            let prior=model.inputControl!,priorAction=model.control!;model.reconcile(feed(epoch+100));model.search("old epoch",input:prior);await model.open(hit,expected:priorAction)
            let afterEpoch=await transport.recorded();try expect(model.query.isEmpty && model.selected==nil && model.feed.epoch==epoch+100 && afterEpoch.count==1,"Old raw query owner entered new same-Business epoch")
            let expectedQuery=kind == .inbox ? ["business":"101","limit":"30"]:["business":"101"]
            try expect(afterEpoch[0].path=="/api/mobile/v1/\(kind == .inbox ? "inbox":kind.rawValue)/\(id)/" && afterEpoch[0].query==expectedQuery,"Query window changed exact accepted scoped detail GET")
        }
    }
    return count
}
