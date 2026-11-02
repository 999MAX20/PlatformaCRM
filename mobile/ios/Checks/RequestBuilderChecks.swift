import Foundation
import CRMCore

private struct RequestCheckError: Error { let message: String }
func runNativeRequestChecks() throws -> Int {
        var checks = 0
        func check(_ condition: @autoclosure () -> Bool, _ name: String) throws {
            guard condition() else { throw RequestCheckError(message: name) }; checks += 1
        }
        func rejects(_ expected: RequestConfigurationFailure, _ body: () throws -> Void) throws {
            do { try body(); throw RequestCheckError(message: "Expected rejection") }
            catch let error as RequestConfigurationFailure { try check(error == expected, "Wrong failure") }
        }
        let builder = try NativeRequestBuilder(origin: URL(string: "https://fixture-api.example.invalid")!, timeout: 7)
        let request = try builder.request(for: ReadRequest(path: "/api/mobile/v1/appointments/", query: ["business":"101","date":"2026-10-28","status":"created&business=999 + К"] ))
        try check(request.httpMethod == "GET" && request.httpBody == nil, "Read-only wire request")
        try check(request.url?.host == "fixture-api.example.invalid", "Pinned injected origin")
        try check(request.value(forHTTPHeaderField: "Accept") == "application/json", "JSON response contract")
        try check(request.value(forHTTPHeaderField: "Authorization") == nil && !request.httpShouldHandleCookies, "No implicit credentials")
        try check(request.timeoutInterval == 7, "Explicit caller-supplied timeout")
        let query = URLComponents(url: request.url!, resolvingAgainstBaseURL: false)!.queryItems!
        try check(query.first(where: {  $0.name == "status" })?.value == "created&business=999 + К", "Query cannot inject another parameter")
        let encoded = URLComponents(url: request.url!, resolvingAgainstBaseURL: false)!.percentEncodedQuery!
        let wireValue = encoded.split(separator: "&").first(where: { $0.hasPrefix("status=") })!.dropFirst("status=".count)
        let formDecoded = String(wireValue).replacingOccurrences(of: "+", with: " ").removingPercentEncoding
        try check(formDecoded == "created&business=999 + К", "Backend form-style query decode preserves literal plus")
        try check(query.map(\.name) == ["business","date","status"], "Deterministic query order")
        for origin in ["http://fixture-api.example.invalid", "https://user:pass@fixture-api.example.invalid", "https://fixture-api.example.invalid/api", "https://fixture-api.example.invalid?business=999", "https://fixture-api.example.invalid#fragment", "https://fixture-api.example.invalid:0"] {
            try rejects(.invalidOrigin) { _ = try NativeRequestBuilder(origin: URL(string: origin)!, timeout: 7) }
        }
        try rejects(.invalidTimeout) { _ = try NativeRequestBuilder(origin: URL(string: "https://fixture-api.example.invalid")!, timeout: 0) }
        for path in ["//foreign.example.invalid/api/mobile/v1/appointments/", "/api/mobile/v1/../outside/", "/api/mobile/v1/%2e%2e/outside/", "/api/mobile/v1/appointments/?business=999", "/api/mobile/v1/appointments/#fragment", "/api/mobile/v1//appointments/"] {
            try rejects(.invalidPath) { _ = try builder.request(for: ReadRequest(path: path)) }
        }
        return checks
}

private actor RecordingReadHTTPExchange: NativeReadHTTPExchange {
    private var rows:[URLRequest]=[]
    let response:ReadResponse
    init(_ response:ReadResponse) {self.response=response}
    func execute(_ request:URLRequest) async throws -> ReadResponse {rows.append(request);return response}
    func recorded() -> [URLRequest] {rows}
}
private actor HeldReadHTTPExchange: NativeReadHTTPExchange {
    private var pending:CheckedContinuation<ReadResponse,Never>?
    private var waiter:CheckedContinuation<Void,Never>?
    func execute(_ request:URLRequest) async throws -> ReadResponse {await withCheckedContinuation {pending=$0;waiter?.resume();waiter=nil}}
    func wait() async {if pending==nil {await withCheckedContinuation {waiter=$0}}}
    func resolve(_ response:ReadResponse) {pending!.resume(returning:response);pending=nil}
}
func runBackendReadTransportChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("backend-read-transport.json"))) as! [String:Any]
    for row in catalog["config_cases"] as! [[String:Any]] {
        let expected=row["expected"] as! String
        do {
            let config=try NativeConnectionConfiguration(publicValues:row["values"] as! [String:String])
            try expect(expected=="configured" && config.timeoutMilliseconds==(row["milliseconds"] as? Int64),"Public configuration accepted invalid value or changed milliseconds")
            let request=try config.requestBuilder().request(for:ReadRequest(path:"/api/mobile/v1/clients/",query:["business":"101"]))
            try expect(request.timeoutInterval==Double(config.timeoutMilliseconds)/1000 && request.url?.host=="fixture-api.example.invalid" && request.value(forHTTPHeaderField:"Authorization")==nil,"Public config invented timeout/origin/credentials")
        } catch let error as NativeConnectionConfigurationFailure {
            try expect((error == .unconfigured ? "unconfigured":"unexpectedKey")==expected,"Wrong missing/unexpected config state")
        } catch let error as RequestConfigurationFailure {
            let kind=error == .invalidOrigin ? "invalidOrigin":"invalidTimeout"
            try expect(kind==expected,"Wrong invalid public setting state")
        }
    }
    let config=try NativeConnectionConfiguration(publicValues:["CRM_API_ORIGIN":catalog["origin"] as! String,"CRM_READ_TIMEOUT_SECONDS":"1.25"])
    for row in catalog["status_cases"] as! [[String:Any]] {
        let status=row["status"] as! Int,expected=row["expected"] as! String
        let bytes=try (row["response_fixture"] as? String).map {try Data(contentsOf:directory.appendingPathComponent($0))} ?? Data("not a success DTO".utf8)
        let exchange=RecordingReadHTTPExchange(ReadResponse(status:status,data:bytes)),transport=BackendReadTransport(builder:try config.requestBuilder(),exchange:exchange)
        let raw=try await transport.get(ReadRequest(path:"/api/mobile/v1/clients/",query:["business":"101"]))
        try expect(raw.status==status && raw.data==bytes,"Read transport changed HTTP status/body or substituted fixtures")
        let repo=APIReadRepository(transport:transport)
        do {let list=try await repo.clients(business:101);try expect(expected=="loaded" && list.business==101 && list.items.map(\.id)==[701,702],"Configured adapter did not feed existing repository")}
        catch let failure as ReadFailure {let kind=failure == .denied ? "denied":failure == .notFound ? "notFound":"unavailable";try expect(kind==expected,"HTTP error became success or wrong repository state")}
        let reads=await exchange.recorded()
        try expect(reads.count==2 && reads.allSatisfy {$0.httpMethod=="GET" && $0.httpBody==nil && $0.url?.host=="fixture-api.example.invalid" && URLComponents(url:$0.url!,resolvingAgainstBaseURL:false)?.path=="/api/mobile/v1/clients/" && $0.timeoutInterval==1.25 && $0.value(forHTTPHeaderField:"Authorization")==nil && !$0.httpShouldHandleCookies},"Adapter added retries/body/credentials/route drift")
        try expect(reads.map {URLComponents(url:$0.url!,resolvingAgainstBaseURL:false)!.percentEncodedQuery!}==["business=101","business=101&limit=50"],"Configured transport changed exact existing query contract")
        do {_=try await transport.get(ReadRequest(path:"/api/mobile/v1/../outside/"));throw CheckFailure(message:"Invalid path entered exchange")}
        catch let error as RequestConfigurationFailure {let recordedCount=await exchange.recorded().count;try expect(error == .invalidPath && recordedCount==2,"Path rejection ran HTTP exchange")}
    }
    let malformed=BackendReadTransport(builder:try config.requestBuilder(),exchange:RecordingReadHTTPExchange(ReadResponse(status:200,data:Data("{".utf8))))
    do {_=try await APIReadRepository(transport:malformed).clients(business:101);throw CheckFailure(message:"Malformed200 became fixture success")}
    catch let error as ReadFailure {try expect(error == .invalidPayload,"Malformed200 lost typed payload error")}
    let held=HeldReadHTTPExchange(),pending=BackendReadTransport(builder:try config.requestBuilder(),exchange:held)
    let task=Task {try await pending.get(ReadRequest(path:"/api/mobile/v1/clients/",query:["business":"101"]))};await held.wait();task.cancel();await held.resolve(ReadResponse(status:200,data:Data()))
    do {_=try await task.value;throw CheckFailure(message:"Cancelled exchange returned successful read")}
    catch is CancellationError {try expect(true,"Cancellation propagated")}
    return count
}

private func authFixtureInput(_ o:[String:Any]) -> MobileLoginInput {
    func optional(_ key:String) -> String? {o[key] as? String}
    let device=MobileAuthDeviceInput(deviceID:o["device_id"] as! String,platform:MobileDevicePlatform(rawValue:o["platform"] as! String)!,appVersion:optional("app_version"),buildNumber:optional("build_number"),osVersion:optional("os_version"),deviceModel:optional("device_model"))
    return MobileLoginInput(device:device,email:o["email"] as! String,password:o["password"] as! String,business:o["business"] as? Int)
}
func runMobileAuthContractChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ condition:Bool,_ message:String) throws {guard condition else {throw CheckFailure(message:message)};count += 1}
    let fixture=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("mobile-auth-contracts.json"))) as! [String:Any]
    try expect(fixture["fixture_only"] as? Bool==true,"Auth schemas need explicit synthetic fixture source")
    let inputs=fixture["login_inputs"] as! [String:[String:Any]]
    for row in fixture["request_cases"] as! [[String:Any]] {
        let values=row["values"] as! [String:Any],expected=row["expected_body"] as! [String:Any],operation=row["operation"] as! String
        let bytes:Data,descriptions:[String]
        if operation=="login" {let value=authFixtureInput(values);bytes=try JSONEncoder().encode(value);descriptions=[String(describing:value),String(reflecting:value),String(describing:value.device)]}
        else if operation=="refresh" {let value=MobileRefreshInput(refresh:values["refresh"] as! String);bytes=try JSONEncoder().encode(value);descriptions=[String(describing:value),String(reflecting:value)]}
        else {let value=MobileLogoutInput(refresh:values["refresh"] as? String);bytes=try JSONEncoder().encode(value);descriptions=[String(describing:value),String(reflecting:value)]}
        let body=try JSONSerialization.jsonObject(with:bytes) as! [String:Any]
        try expect(Set(body.keys)==Set(expected.keys),"Auth request invented, omitted or defaulted a field")
        for (key,value) in expected {
            if let raw=value as? String {try expect((body[key] as? String).map {SourceTextIdentity.same($0,raw)}==true,"Auth request normalized raw caller text")}
            else {try expect((body[key] as? Int)==(value as? Int),"Auth request changed explicit Business")}
        }
        try expect(descriptions.allSatisfy {$0.contains("redacted") && !$0.contains("synthetic-") && !$0.contains("Example.invalid")},"Auth input debug text leaked synthetic sensitive values")
    }
    for row in fixture["response_cases"] as! [[String:Any]] {
        let operation=row["operation"] as! String,expected=row["expected"] as! String,body=row["body"] as! [String:Any]
        let bytes=try JSONSerialization.data(withJSONObject:body)
        do {
            if operation=="login" {
                let input=authFixtureInput(inputs[row["input"] as! String]!),reply=try MobileAuthJSON.loginResponse(bytes,for:input)
                try expect(SourceTextIdentity.same(reply.tokens.access,(body["access"] as! String)) && SourceTextIdentity.same(reply.tokens.refresh,(body["refresh"] as! String)),"Opaque auth response tokens changed")
                let business=body["business"] as! [String:Any],device=body["device"] as! [String:Any]
                try expect(reply.business.id==business["id"] as? Int && reply.device.business==reply.business.id && reply.device.id==device["id"] as? Int,"Auth schema inferred actor/device from Business/input")
                try expect(reply.business.permissions.count==(business["permissions"] as! [Any]).count && SourceTextIdentity.same(reply.business.name,(business["name"] as! String)),"Auth supplied permission descriptors/name changed")
                try expect(String(reflecting:reply)=="MobileLoginReply(redacted)" && String(reflecting:reply.tokens)=="MobileTokenReply(redacted)","Auth response debug leaked token fields")
            } else if operation=="refresh" {let reply=try MobileAuthJSON.refreshResponse(bytes);try expect(SourceTextIdentity.same(reply.access,(body["access"] as! String)) && SourceTextIdentity.same(reply.refresh,(body["refresh"] as! String)),"Refresh response reused/defaulted token")}
            else {try expect(try MobileAuthJSON.logoutResponse(bytes).ok,"Source logout schema rejected true")}
            try expect(expected=="loaded","Auth schema accepted unsupported response")
        } catch let failure as MobileAuthContractFailure {
            try expect(expected==(failure == .contextMismatch ? "contextMismatch":"invalidPayload"),"Auth schema returned wrong rejection")
        }
    }
    return count
}

func runAppointmentLifecycleChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-lifecycle.json"))) as! [String:Any]
    let first=(catalog["sources"] as! [[String:Any]])[0],grant=try JSONDecoder().decode(SyntheticAppointmentLifecycleGrant.self,from:JSONSerialization.data(withJSONObject:first["grant"]!))
    let page=try JSONDecoder().decode(AppointmentList.self,from:Data(contentsOf:directory.appendingPathComponent("appointments-101.json"))),boot=try JSONDecoder().decode(Bootstrap.self,from:Data(contentsOf:directory.appendingPathComponent("bootstrap.json")))
    var session=AgendaSession();try session.install(boot);let scope=try session.begin(businessID:101,day:page.date);try session.receive(page,for:scope);let read=try session.beginDetail(id:501)
    let source=AppointmentLifecycleSource(read:read,epoch:1,appointment:page.items[0])
    for row in catalog["receipt_cases"] as! [[String:Any]] {
        var ledger=AppointmentLifecycleLedger();let action=AppointmentLifecycleAction(rawValue:row["action"] as! String)!,auth=grant.authorization(source,action:action)!,review=AppointmentLifecycleReview(source:source,action:action,visit:1),attempt=ledger.begin(review,authorization:auth)!
        let body=try JSONSerialization.jsonObject(with:attempt.body) as! [String:Any]
        try expect(Set(body.keys)==["business"] && body["business"] as? Int==101 && attempt.path=="/api/mobile/v1/appointments/501/confirm/" && SourceTextIdentity.same(attempt.authorization.key,grant.confirm_key),"Lifecycle invented body/key/version/reason or changed supplied identity")
        try expect(ledger.begin(AppointmentLifecycleReview(source:source,action:.cancel,visit:2),authorization:grant.authorization(source,action:.cancel)!)==nil,"Pending confirm failed to block cancel")
        let bytes=try JSONSerialization.data(withJSONObject:row["body"]!)
        ledger.complete(attempt,outcome:.response(status:row["status"] as! Int,data:bytes))
        let record=ledger.records[0],expected=row["expected"] as! String
        try expect((record.phase == .acceptedFixture ? "acceptedFixture":"unknown")==expected && (record.receipt != nil)==(expected=="acceptedFixture"),"Lifecycle receipt/status misclassified, omitted fields defaulted or HTTP error treated as no-write")
        if record.phase == .unknown {
            ledger.complete(attempt,outcome:.response(status:200,data:try JSONSerialization.data(withJSONObject:(catalog["receipt_cases"] as! [[String:Any]])[0]["body"]!)))
            try expect(ledger.records[0].phase == .unknown && !ledger.acknowledge(record) && ledger.blocked(source) && ledger.records[0].attempt.body==attempt.body,"Unknown lost original input/attempt/body or was resolved by another matching response")
        } else {try expect(ledger.acknowledge(record) && ledger.used(source,.confirm) && !ledger.blocked(source),"Known fake acceptance not scoped/consumed")}
    }
    var ledger=AppointmentLifecycleLedger();let attempt=ledger.begin(AppointmentLifecycleReview(source:source,action:.cancel,visit:1),authorization:grant.authorization(source,action:.cancel)!)!
    ledger.complete(attempt,outcome:.rejectedWithoutWrite);let rejected=ledger.records[0]
    try expect(rejected.phase == .rejectedFixture && ledger.acknowledge(rejected) && !ledger.used(source,.cancel),"Explicit synthetic no-write rejection conflated with unknown/receipt")
    for action in AppointmentLifecycleAction.allCases {
        for denied in [SyntheticAppointmentLifecycleGrant(business:202,appointment:501,actor:5001,update:true,confirmKey:"key",cancelKey:"key"),SyntheticAppointmentLifecycleGrant(business:101,appointment:502,actor:5001,update:true,confirmKey:"key",cancelKey:"key"),SyntheticAppointmentLifecycleGrant(business:101,appointment:501,actor:0,update:true,confirmKey:"key",cancelKey:"key"),SyntheticAppointmentLifecycleGrant(business:101,appointment:501,actor:5001,update:false,confirmKey:"key",cancelKey:"key"),SyntheticAppointmentLifecycleGrant(business:101,appointment:501,actor:5001,update:true,confirmKey:" \t",cancelKey:nil)] {
            try expect(denied.authorization(source,action:action)==nil,"GET or invalid/missing synthetic context created authority")
        }
    }
    let rawA=SyntheticAppointmentLifecycleGrant(business:101,appointment:501,actor:5001,update:true,confirmKey:"e\u{301}",cancelKey:nil),rawB=SyntheticAppointmentLifecycleGrant(business:101,appointment:501,actor:5001,update:true,confirmKey:"é",cancelKey:nil)
    try expect(rawA != rawB && rawA.authorization(source,action:.confirm) != rawB.authorization(source,action:.confirm),"Opaque supplied key identity was normalized")
    return count
}

func runAppointmentRescheduleChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-reschedule.json"))) as! [String:Any]
    let raw=(catalog["inputs"] as! [String:[String:Any]])["501"]!,rawStart=raw["start_at"] as! String,rawReason=raw["reason_raw"] as! String
    let boot=try JSONDecoder().decode(Bootstrap.self,from:Data(contentsOf:directory.appendingPathComponent("bootstrap.json"))),page=try JSONDecoder().decode(AppointmentList.self,from:Data(contentsOf:directory.appendingPathComponent("appointments-101.json")))
    var session=AgendaSession();try session.install(boot);let scope=try session.begin(businessID:101,day:page.date);try session.receive(page,for:scope)
    let source=AppointmentLifecycleSource(read:try session.beginDetail(id:501),epoch:1,appointment:page.items[0],linkedResourceID:9001)
    let lifecycle=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-lifecycle.json"))) as! [String:Any]
    let grant=try JSONDecoder().decode(SyntheticAppointmentLifecycleGrant.self,from:JSONSerialization.data(withJSONObject:(lifecycle["sources"] as! [[String:Any]])[0]["grant"]!)),a=grant.authorization(source,action:.reschedule)!
    for row in catalog["time_cases"] as! [[String:Any]] {
        let raw=row["raw"] as! String,value=AppointmentRescheduleInput(source:source,startAt:raw,reason:rawReason,resource:.clear)
        try expect((value != nil)==(row["valid"] as! Bool),"Reschedule explicit time subset accepted naive/invalid/rounded/default instant or rejected supported value")
        if let value {try expect(SourceTextIdentity.same(value.start.raw,raw) && SourceTextIdentity.same(value.rawReason,rawReason) && value.reason==SourceTextTrim.pythonStrip(rawReason),"Reschedule rewrote raw time/reason or changed source strip")}
    }
    let resourceData=try Data(contentsOf:directory.appendingPathComponent("resource-reference-9001.json")),reference=AppointmentReferenceDetail.decode(resourceData,kind:.resource)!
    let linked=AppointmentRescheduleInput(source:source,startAt:rawStart,reason:rawReason,resource:.linked(reference))!
    try expect(linked.resource.id==9001,"Scoped linked resource lost explicit identity")
    var bad=try JSONSerialization.jsonObject(with:resourceData) as! [String:Any];bad["business"]=202
    let wrong=AppointmentReferenceDetail.decode(try JSONSerialization.data(withJSONObject:bad),kind:.resource)!
    try expect(AppointmentRescheduleInput(source:source,startAt:rawStart,reason:rawReason,resource:.linked(wrong))==nil,"Cross-Business reference entered reschedule")
    let absent=AppointmentLifecycleSource(read:source.read,epoch:1,appointment:source.appointment)
    try expect(AppointmentRescheduleInput(source:absent,startAt:rawStart,reason:rawReason,resource:.linked(reference))==nil && AppointmentRescheduleInput(source:absent,startAt:rawStart,reason:rawReason,resource:.clear) != nil,"Missing linked original implied keep/choose or blocked explicit clear")
    let input=AppointmentRescheduleInput(source:source,startAt:rawStart,reason:rawReason,resource:.clear)!
    for row in catalog["receipt_cases"] as! [[String:Any]] {
        var ledger=AppointmentLifecycleLedger();let attempt=ledger.begin(AppointmentLifecycleReview(source:source,action:.reschedule,visit:1,reschedule:input),authorization:a)!
        let body=try JSONSerialization.jsonObject(with:attempt.body) as! [String:Any]
        try expect(Set(body.keys)==["business","start_at","resource","reason"] && body["resource"] is NSNull && (body["business"] as? Int)==101 && SourceTextIdentity.same(body["start_at"] as? String,rawStart) && SourceTextIdentity.same(body["reason"] as? String,input.reason) && SourceTextIdentity.same(attempt.authorization.key,grant.reschedule_key) && attempt.path=="/api/mobile/v1/appointments/501/reschedule/","Reschedule body invented version/default/recovery or lost raw time/explicit null/source reason/key")
        for action in AppointmentLifecycleAction.allCases {
            let review=AppointmentLifecycleReview(source:source,action:action,visit:2,reschedule:action == .reschedule ? input:nil)
            let candidate=grant.authorization(source,action:action) ?? SyntheticAppointmentTerminalGrant(business:101,appointment:501,actor:5001,update:true,actions:[.complete,.noShow]).authorization(source,action:action)!
            try expect(ledger.begin(review,authorization:candidate)==nil,"Pending reschedule did not block another lifecycle action")
        }
        ledger.complete(attempt,outcome:.response(status:row["status"] as! Int,data:try JSONSerialization.data(withJSONObject:row["body"]!)))
        let record=ledger.records[0],expected=row["expected"] as! String
        try expect((record.phase == .acceptedFixture ? "acceptedFixture":"unknown")==expected,"Reschedule receipt status/instant/original-status/required-field oracle failed")
        if record.phase == .unknown {try expect(!ledger.acknowledge(record) && ledger.blocked(source) && ledger.records[0].attempt.body==attempt.body && ledger.records[0].attempt.review.reschedule==input,"Unknown lost frozen reschedule input/body/key or was acknowledged")}
        else {try expect(ledger.acknowledge(record) && ledger.used(source,.reschedule),"Accepted fixture reschedule was silently replayable")}
    }
    var linkedLedger=AppointmentLifecycleLedger();let linkedAttempt=linkedLedger.begin(AppointmentLifecycleReview(source:source,action:.reschedule,visit:1,reschedule:linked),authorization:a)!
    let linkedBody=try JSONSerialization.jsonObject(with:linkedAttempt.body) as! [String:Any]
    try expect(linkedBody["resource"] as? Int==9001,"Explicit loaded Resource was silently omitted/cleared")
    var item=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-101-501.json"))) as! [String:Any]
    for status in ["cancelled","completed","no_show"] {
        var fields=item["appointment"] as! [String:Any];fields["status"]=status;item["appointment"]=fields
        let detail=try JSONDecoder().decode(AppointmentDetail.self,from:JSONSerialization.data(withJSONObject:item)),terminal=AppointmentLifecycleSource(read:source.read,epoch:1,appointment:detail.appointment,linkedResourceID:9001)
        try expect(AppointmentRescheduleInput(source:terminal,startAt:rawStart,reason:rawReason,resource:.clear)==nil,"Existing terminal reschedule source guard ignored")
    }
    return count
}

func runAppointmentTerminalChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-terminal.json"))) as! [String:Any]
    let boot=try JSONDecoder().decode(Bootstrap.self,from:Data(contentsOf:directory.appendingPathComponent("bootstrap.json"))),page=try JSONDecoder().decode(AppointmentList.self,from:Data(contentsOf:directory.appendingPathComponent("appointments-101.json")))
    var session=AgendaSession();try session.install(boot);let scope=try session.begin(businessID:101,day:page.date);try session.receive(page,for:scope)
    let source=AppointmentLifecycleSource(read:try session.beginDetail(id:501),epoch:1,appointment:page.items[0]),grant=SyntheticAppointmentTerminalGrant(business:101,appointment:501,actor:5001,update:true,actions:[.complete,.noShow])
    let fixture=FixtureAppointmentTerminalPort(directory:directory),mobile=fixture.grants.first {$0.business==101 && $0.appointment==501}!
    let input=AppointmentRescheduleInput(source:source,startAt:"2026-10-28T05:00:00Z",reason:"retained",resource:.clear)!
    for action in [AppointmentLifecycleAction.complete,.noShow] {
        try expect(mobile.authorization(source,action:action)==nil,"GET/mobile-key grant authorized distinct generic terminal action")
        for denied in [SyntheticAppointmentTerminalGrant(business:202,appointment:501,actor:5001,update:true,actions:[action]),SyntheticAppointmentTerminalGrant(business:101,appointment:502,actor:5001,update:true,actions:[action]),SyntheticAppointmentTerminalGrant(business:101,appointment:501,actor:0,update:true,actions:[action]),SyntheticAppointmentTerminalGrant(business:101,appointment:501,actor:5001,update:false,actions:[action]),SyntheticAppointmentTerminalGrant(business:101,appointment:501,actor:5001,update:true,actions:[])] {try expect(denied.authorization(source,action:action)==nil,"Missing explicit terminal actor/UPDATE/scope/action admitted")}
        for row in catalog["receipt_cases"] as! [[String:Any]] {
            var ledger=AppointmentLifecycleLedger();let a=grant.authorization(source,action:action)!,review=AppointmentLifecycleReview(source:source,action:action,visit:1),attempt=ledger.begin(review,authorization:a)!
            let body=try JSONSerialization.jsonObject(with:attempt.body) as! [String:Any]
            try expect(attempt.method=="POST" && attempt.path=="/api/appointments/501/\(action.rawValue)/" && attempt.query==["business":"101"] && body.isEmpty && a.key==nil,"Generic terminal invented mobile route/body/key/reason/version or lost explicit scope")
            for other in AppointmentLifecycleAction.allCases {
                let auth=mobile.authorization(source,action:other) ?? grant.authorization(source,action:other)!
                try expect(ledger.begin(AppointmentLifecycleReview(source:source,action:other,visit:2,reschedule:other == .reschedule ? input:nil),authorization:auth)==nil,"Pending generic terminal escaped shared5-action barrier")
            }
            var response=row["body"] as! [String:Any];if action == .noShow,response["status"] as? String=="completed" {response["status"]="no_show"}
            let bytes=try JSONSerialization.data(withJSONObject:response,options:.sortedKeys)
            ledger.complete(attempt,outcome:.response(status:row["status"] as! Int,data:bytes));let record=ledger.records[0],accepted=row["expected"] as! String=="acceptedFixture"
            try expect((record.phase == .acceptedFixture)==accepted && record.receipt==nil && (record.terminalReceipt != nil)==accepted,"Plain terminal malformed/mismatch/error receipt classified as known or mobile envelope mixed")
            if accepted {try expect(record.terminalReceipt?.raw==bytes && ledger.acknowledge(record) && ledger.used(source,action),"Known fixture did not retain exact response/consume local action")}
            else {
                let reread=AppointmentLifecycleSource(read:source.read,epoch:2,appointment:source.appointment)
                try expect(ledger.blocked(reread) && !ledger.acknowledge(record) && record.attempt==attempt && record.attempt.body==attempt.body && record.attempt.query==attempt.query,"Unknown/reread lost original review/body/query/attempt or released barrier")
                let known=(catalog["receipt_cases"] as! [[String:Any]])[0]["body"]!
                ledger.complete(attempt,outcome:.response(status:200,data:try JSONSerialization.data(withJSONObject:known)))
                try expect(ledger.records[0].phase == .unknown,"Matching later reply resolved unknown or silently retried")
            }
        }
        var ledger=AppointmentLifecycleLedger();let auth=grant.authorization(source,action:action)!
        try expect(ledger.begin(AppointmentLifecycleReview(source:source,action:action,visit:1,reschedule:input),authorization:auth)==nil,"Generic empty-body action accepted unrelated reschedule input")
        let attempt=ledger.begin(AppointmentLifecycleReview(source:source,action:action,visit:2),authorization:auth)!;ledger.complete(attempt,outcome:.rejectedWithoutWrite)
        try expect(ledger.acknowledge(ledger.records[0]) && !ledger.used(source,action),"Explicit synthetic rejectedWithoutWrite treated as unknown/known success")
    }
    return count
}
