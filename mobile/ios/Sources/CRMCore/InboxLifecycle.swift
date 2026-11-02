import Foundation

// Observed generic conversation only. No permission, version or command recovery inference.
// Bounded close omits optional reason. No reason editor, prefill or reason echo contract.
public struct InboxLifecycleSource:Equatable,Sendable {
    public let context:InboxConversationFilesContext,status:String,botEnabled:Bool,handoffRequired:Bool,updatedAt:String
    private init(_ c:InboxConversationFilesContext,_ status:String,_ bot:Bool,_ handoff:Bool,_ updated:String) {context=c;self.status=status;botEnabled=bot;handoffRequired=handoff;updatedAt=updated}
    public var valid:Bool {context.valid && !updatedAt.isEmpty}
    public static func ==(a:Self,b:Self)->Bool {a.context==b.context && a.botEnabled==b.botEnabled && a.handoffRequired==b.handoffRequired && SourceTextIdentity.same(a.status,b.status) && SourceTextIdentity.same(a.updatedAt,b.updatedAt)}
    private struct Fields:Decodable {let status:String,bot_enabled:Bool,handoff_required:Bool,updated_at:String}
    public static func decode(_ data:Data,context c:InboxConversationFilesContext)->Self? {guard c.valid,let row=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],InboxFileReadJSON.anchor(row,business:c.business,conversation:c.conversation),let f=try? JSONDecoder().decode(Fields.self,from:data),!f.updated_at.isEmpty else {return nil};return Self(c,f.status,f.bot_enabled,f.handoff_required,f.updated_at)}
}
public enum InboxLifecycleAction:String,Equatable,Sendable {case close,reopen}
public struct SyntheticInboxLifecycleGrant:Decodable,Sendable {
    public let business:Int,conversation:Int,actor:Int,update:Bool
    public init(business:Int,conversation:Int,actor:Int,update:Bool) {self.business=business;self.conversation=conversation;self.actor=actor;self.update=update}
    public func authorization(for c:InboxConversationFilesContext)->SyntheticInboxLifecycleAuthorization? {guard c.valid,business==c.business,conversation==c.conversation,actor>0,actor<=Int(Int32.max),update else {return nil};return SyntheticInboxLifecycleAuthorization(context:c,actor:actor)}
}
public struct SyntheticInboxLifecycleAuthorization:Equatable,Sendable {public let context:InboxConversationFilesContext;public let actor:Int;fileprivate init(context:InboxConversationFilesContext,actor:Int) {self.context=context;self.actor=actor}}
public struct InboxLifecycleReview:Equatable,Sendable {
    public let source:InboxLifecycleSource,authorization:SyntheticInboxLifecycleAuthorization,action:InboxLifecycleAction,visit:Int
    public init(source:InboxLifecycleSource,authorization:SyntheticInboxLifecycleAuthorization,action:InboxLifecycleAction,visit:Int) {self.source=source;self.authorization=authorization;self.action=action;self.visit=visit}
    public var valid:Bool {source.valid && authorization.context==source.context && authorization.actor>0 && visit>0}
}
public struct InboxLifecycleAttempt:Equatable,Sendable {
    public let localID:Int,review:InboxLifecycleReview
    public var path:String {"/api/inbox/conversations/\(review.source.context.conversation)/\(review.action.rawValue)/"}
    public var query:[String:String] {[:]}
    public var headers:[String:String] {[:]}
    public func preparedBody()->Data {Data("{}".utf8)}
}
public struct InboxLifecycleReceipt:Equatable,Sendable {
    public let source:InboxLifecycleSource
    public static func decode(_ data:Data,attempt a:InboxLifecycleAttempt)->Self? {guard a.review.valid,let source=InboxLifecycleSource.decode(data,context:a.review.source.context),(a.review.action == .close ? source.status=="closed" && !source.botEnabled && !source.handoffRequired:source.status=="open") else {return nil};return Self(source:source)}
}
public enum SyntheticInboxLifecycleOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticInboxLifecyclePort:Sendable {var grants:[SyntheticInboxLifecycleGrant] {get};func execute(_ attempt:InboxLifecycleAttempt) async throws -> SyntheticInboxLifecycleOutcome}
public enum InboxLifecyclePhase:Equatable,Sendable {case pending,response,rejected,unknown}
public struct InboxLifecycleRecord:Equatable,Sendable {public let attempt:InboxLifecycleAttempt;public var phase:InboxLifecyclePhase;public var result:InboxLifecycleReceipt?}
public struct InboxLifecycleLedger:Sendable {
    public private(set) var records:[InboxLifecycleRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:InboxConversationFilesContext)->String {"\(c.business)/\(c.conversation)"}
    public func blocked(business:Int,conversation:Int)->Bool {active["\(business)/\(conversation)"] != nil}
    public func visible(_ auth:SyntheticInboxLifecycleAuthorization?)->InboxLifecycleRecord? {guard let auth,let i=active[key(auth.context)],records[i].attempt.review.authorization.actor==auth.actor else {return nil};return records[i]}
    public mutating func begin(_ review:InboxLifecycleReview)->InboxLifecycleAttempt? {
        guard review.valid,!blocked(business:review.source.context.business,conversation:review.source.context.conversation) else {return nil};let a=InboxLifecycleAttempt(localID:records.count+1,review:review);active[key(review.source.context)]=records.count;records.append(InboxLifecycleRecord(attempt:a,phase:.pending,result:nil));return a
    }
    public mutating func complete(_ a:InboxLifecycleAttempt,outcome:SyntheticInboxLifecycleOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==a}),records[i].phase == .pending else {return}
        switch outcome {case .unknown:records[i].phase = .unknown;case .rejectedWithoutWrite:records[i].phase = .rejected;case .response(let status,let data):if status==200,let receipt=InboxLifecycleReceipt.decode(data,attempt:a) {records[i].phase = .response;records[i].result=receipt} else {records[i].phase = .unknown}}
    }
    @discardableResult public mutating func acknowledge(_ auth:SyntheticInboxLifecycleAuthorization,record:InboxLifecycleRecord)->Bool {guard visible(auth)==record,record.phase == .response || record.phase == .rejected else {return false};active.removeValue(forKey:key(auth.context));return true}
}
public protocol InboxLifecycleRepository:Sendable {func source(_ context:InboxConversationFilesContext) async throws -> InboxLifecycleSource}
public struct APIInboxLifecycleRepository:InboxLifecycleRepository {
    private let transport:any ReadTransport
    public init(transport:any ReadTransport) {self.transport=transport}
    public func source(_ context:InboxConversationFilesContext) async throws -> InboxLifecycleSource {
        guard context.valid else {throw ReadFailure.invalidContext};let r=try await transport.get(ReadRequest(path:"/api/inbox/conversations/\(context.conversation)/"));guard r.status==200 else {throw r.status==403 ? ReadFailure.denied:r.status==404 ? .notFound:.unavailable};guard let s=InboxLifecycleSource.decode(r.data,context:context) else {throw ReadFailure.invalidPayload};return s
    }
}
// Separate explicit fixture command and GET adapters. No HTTP command implementation.
public struct FixtureInboxLifecyclePort:SyntheticInboxLifecyclePort {
    private struct Scenario:Decodable,Sendable {let business:Int,conversation:Int,actor:Int,action:String,outcome:String;let status:Int?;let response_json:String?}
    private struct Catalog:Decodable {let fixture_only:Bool;let grants:[SyntheticInboxLifecycleGrant];let scenarios:[Scenario]}
    public let grants:[SyntheticInboxLifecycleGrant];private let scenarios:[Scenario]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-lifecycle.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {grants=c.grants;scenarios=c.scenarios} else {grants=[];scenarios=[]}}
    public func execute(_ a:InboxLifecycleAttempt) async throws -> SyntheticInboxLifecycleOutcome {let auth=a.review.authorization,c=auth.context;guard a.review.valid,grants.compactMap({$0.authorization(for:c)}).contains(auth),let s=scenarios.first(where:{$0.business==c.business && $0.conversation==c.conversation && $0.actor==auth.actor && $0.action==a.review.action.rawValue}) else {return .rejectedWithoutWrite};if s.outcome=="response",let status=s.status,let raw=s.response_json {return .response(status:status,data:Data(raw.utf8))};return s.outcome=="rejected" ? .rejectedWithoutWrite:.unknown}
}
public struct FixtureInboxLifecycleReadTransport:ReadTransport {
    private struct Row:Decodable,Sendable {let path:String,response_json:String}
    private struct Catalog:Decodable {let fixture_only:Bool;let reads:[Row]}
    private let rows:[Row]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-lifecycle.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {rows=c.reads} else {rows=[]}}
    public func get(_ q:ReadRequest) async throws -> ReadResponse {guard q.query.isEmpty,let row=rows.first(where:{$0.path==q.path}) else {throw ReadFailure.invalidContext};return ReadResponse(status:200,data:Data(row.response_json.utf8))}
}
