import Foundation
import CRMCore

@MainActor func checkClientSearchWindows(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let data=try Data(contentsOf:directory.appendingPathComponent("client-search-catalogue-101.json"))
    func page(_ query:String) throws -> ReadResponse {try FixtureClientSearch.list(data,business:101,search:query)}
    let transport=ClientQueryTransport(directory),m=ClientSearchViewModel(repository:APIReadRepository(transport:transport)),context=ClientSearchContext(business:101,epoch:1)
    try expect(m.control==nil && m.inputControl==nil && !m.matches(nil),"Closed search created window/input control")
    m.bind(context);m.open(context);let input=m.inputControl!,feature=m.session.selection!
    try expect(await transport.recorded().isEmpty && !m.session.loaded,"Opening query feature auto-fetched results")
    let raw="\u{001C} catalogue \n";m.update(raw,input:input);let before=m.control!
    await transport.holdSearch(true);await transport.holdProfiles(true)
    let old=Task {await m.submit(expected:before)};await transport.wait(0);await m.submit(expected:m.control);m.clear(expected:before)
    try expect(await transport.recorded().count==1 && m.session.query==raw && m.inputControl==input,"Pending duplicate/old Clear repeated search or rewrote raw input")
    m.update("catalogue 05",input:input);let current=Task {await m.submit(expected:m.control)};await transport.wait(1)
    await transport.resolve(1,try page("catalogue 05"));await current.value;let rows=m.control!
    await transport.resolve(0,try page("catalogue"));await old.value
    try expect(m.control==rows && m.session.submitted=="catalogue 05" && m.session.items.contains(where:{$0.id==1754}) && m.inputControl==input,"Late old query changed current window or invalidated continuous input")
    m.update("catalogue",input:input);let next=Task {await m.submit(expected:m.control)};await transport.wait(2);await transport.resolve(2,try page("catalogue"));await next.value
    await m.openClient(1754,expected:rows);m.clear(expected:rows);await m.submit(expected:rows)
    try expect(await transport.recorded().count==3 && m.session.items.contains(where:{$0.id==1754}) && m.session.profileSelection==nil && m.session.query=="catalogue","Old same-ID result/Clear/Submit affected a new window")
    let open=Task {await m.openClient(1754,expected:m.control)};await transport.wait(3);let pending=m.control!
    await m.retryProfile(expected:pending);m.update("leak",input:input)
    try expect(await transport.recorded().count==4 && m.session.query=="catalogue","Pending profile retry/old input repeated GET or changed parent query")
    await transport.resolve(3,ReadResponse(status:403,data:Data()));await open.value;let denied=m.control!
    let retry=Task {await m.retryProfile(expected:denied)};await transport.wait(4);m.backProfile(expected:denied);await m.retryProfile(expected:denied)
    try expect(await transport.recorded().count==5 && m.session.selectedID==1754 && m.profile.loading,"Old profile Back/retry operated on newer independent read")
    await transport.resolve(4,try FixtureClientSearch.profile(data,business:101,id:1754));await retry.value;let result=m.control!
    try expect(m.profile.detail?.client.id==1754 && m.profile.failure==nil,"Captured current result did not validate independent profile")
    m.backProfile(expected:result);m.close(expected:result);m.update("old input",input:input)
    try expect(m.session.selection==feature && m.session.profileSelection==nil && m.session.query=="catalogue" && m.session.partial && m.session.items.count==50,"Old profile close/input erased retained query/result window")
    let beforeClearInput=m.inputControl!;m.clear(expected:m.control);m.update("old",input:beforeClearInput)
    try expect(m.session.query.isEmpty && !m.session.loaded && !m.session.showsEmpty,"Clear reused old input visit or asserted successful empty")
    let blank=Task {await m.submit(expected:m.control)};await transport.wait(5);await transport.resolve(5,try page(""));await blank.value
    try expect(m.session.items.count==50 && m.session.total==56 && m.session.partial,"Explicit empty query lost bounded source total")
    m.update("fixture-note-tag",input:m.inputControl);let notes=Task {await m.submit(expected:m.control)};await transport.wait(6);await transport.resolve(6,try page("fixture-note-tag"));await notes.value
    try expect(m.session.items.map(\.id)==[1702],"Source-only notes match was locally filtered by visible contact fields")
    let oldWindow=m.control!,oldInput=m.inputControl!;let newer=ClientSearchContext(business:101,epoch:2);m.bind(newer);m.open(newer)
    m.update("old",input:oldInput);m.clear(expected:oldWindow);m.close(expected:oldWindow);await m.submit(expected:oldWindow);await m.openClient(1702,expected:oldWindow)
    let requests=await transport.recorded()
    try expect(requests.count==7 && m.session.selection?.context==newer && m.session.query.isEmpty,"Old same-Business epoch controls fetched/closed/changed current search")
    try expect(requests[0].query==["business":"101","limit":"50","search":"catalogue"] && requests[3].path=="/api/mobile/v1/clients/1754/","Wire search/profile query changed or old raw input escaped source normalization")
    return count
}
