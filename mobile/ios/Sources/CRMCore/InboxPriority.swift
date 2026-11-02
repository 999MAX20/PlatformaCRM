import Foundation

// Observed generic conversation only. No permission, version or command recovery inference.
public struct InboxPrioritySource:Equatable,Sendable {
    public let context:InboxConversationFilesContext,priority:String,updatedAt:String
    private init(_ c:InboxConversationFilesContext,_ priority:String,_ updated:String) {context=c;self.priority=priority;updatedAt=updated}
    public var valid:Bool {context.valid && !updatedAt.isEmpty}
    public static func ==(a:Self,b:Self)->Bool {a.context==b.context && SourceTextIdentity.same(a.priority,b.priority) && SourceTextIdentity.same(a.updatedAt,b.updatedAt)}
    public static func decode(_ data:Data,context c:InboxConversationFilesContext)->Self? {guard c.valid,let row=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],InboxFileReadJSON.anchor(row,business:c.business,conversation:c.conversation),let priority=row["priority"] as? String,let updated=row["updated_at"] as? String,!updated.isEmpty else {return nil};return Self(c,priority,updated)}
}
public enum InboxPriorityValue:String,CaseIterable,Equatable,Sendable {case low,normal,high,urgent}
public struct SyntheticInboxPriorityGrant:Decodable,Sendable {
    public let business:Int,conversation:Int,actor:Int,update:Bool
    public init(business:Int,conversation:Int,actor:Int,update:Bool) {self.business=business;self.conversation=conversation;self.actor=actor;self.update=update}
    public func authorization(for c:InboxConversationFilesContext)->SyntheticInboxPriorityAuthorization? {guard c.valid,business==c.business,conversation==c.conversation,actor>0,actor<=Int(Int32.max),update else {return nil};return SyntheticInboxPriorityAuthorization(context:c,actor:actor)}
}
public struct SyntheticInboxPriorityAuthorization:Equatable,Sendable {public let context:InboxConversationFilesContext;public let actor:Int;fileprivate init(context:InboxConversationFilesContext,actor:Int) {self.context=context;self.actor=actor}}
public struct InboxPriorityReview:Equatable,Sendable {
    public let source:InboxPrioritySource,authorization:SyntheticInboxPriorityAuthorization,value:InboxPriorityValue,visit:Int
    public init(source:InboxPrioritySource,authorization:SyntheticInboxPriorityAuthorization,value:InboxPriorityValue,visit:Int) {self.source=source;self.authorization=authorization;self.value=value;self.visit=visit}
    public var valid:Bool {source.valid && authorization.context==source.context && authorization.actor>0 && visit>0}
}
public struct InboxPriorityAttempt:Equatable,Sendable {
    public let localID:Int,review:InboxPriorityReview
    public var path:String {"/api/inbox/conversations/\(review.source.context.conversation)/set-priority/"}
    public var query:[String:String] {[:]}
    public var headers:[String:String] {[:]}
    public func preparedBody()->Data {Data("{\"priority\":\"\(review.value.rawValue)\"}".utf8)}
}
public struct InboxPriorityReceipt:Equatable,Sendable {
    public let source:InboxPrioritySource
    public static func decode(_ data:Data,attempt a:InboxPriorityAttempt)->Self? {guard a.review.valid,let source=InboxPrioritySource.decode(data,context:a.review.source.context),SourceTextIdentity.same(source.priority,a.review.value.rawValue) else {return nil};return Self(source:source)}
}
public enum SyntheticInboxPriorityOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticInboxPriorityPort:Sendable {var grants:[SyntheticInboxPriorityGrant] {get};func execute(_ attempt:InboxPriorityAttempt) async throws -> SyntheticInboxPriorityOutcome}
public enum InboxPriorityPhase:Equatable,Sendable {case pending,response,rejected,unknown}
public struct InboxPriorityRecord:Equatable,Sendable {public let attempt:InboxPriorityAttempt;public var phase:InboxPriorityPhase;public var result:InboxPriorityReceipt?}
public struct InboxPriorityLedger:Sendable {
    public private(set) var records:[InboxPriorityRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:InboxConversationFilesContext)->String {"\(c.business)/\(c.conversation)"}
    public func blocked(business:Int,conversation:Int)->Bool {active["\(business)/\(conversation)"] != nil}
    public func visible(_ auth:SyntheticInboxPriorityAuthorization?)->InboxPriorityRecord? {guard let auth,let i=active[key(auth.context)],records[i].attempt.review.authorization.actor==auth.actor else {return nil};return records[i]}
    public mutating func begin(_ review:InboxPriorityReview)->InboxPriorityAttempt? {
        guard review.valid,!blocked(business:review.source.context.business,conversation:review.source.context.conversation) else {return nil};let a=InboxPriorityAttempt(localID:records.count+1,review:review);active[key(review.source.context)]=records.count;records.append(InboxPriorityRecord(attempt:a,phase:.pending,result:nil));return a
    }
    public mutating func complete(_ a:InboxPriorityAttempt,outcome:SyntheticInboxPriorityOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==a}),records[i].phase == .pending else {return}
        switch outcome {case .unknown:records[i].phase = .unknown;case .rejectedWithoutWrite:records[i].phase = .rejected;case .response(let status,let data):if status==200,let receipt=InboxPriorityReceipt.decode(data,attempt:a) {records[i].phase = .response;records[i].result=receipt} else {records[i].phase = .unknown}}
    }
    @discardableResult public mutating func acknowledge(_ auth:SyntheticInboxPriorityAuthorization,record:InboxPriorityRecord)->Bool {guard visible(auth)==record,record.phase == .response || record.phase == .rejected else {return false};active.removeValue(forKey:key(auth.context));return true}
}
public protocol InboxPriorityRepository:Sendable {func source(_ context:InboxConversationFilesContext) async throws -> InboxPrioritySource}
public struct APIInboxPriorityRepository:InboxPriorityRepository {
    private let transport:any ReadTransport
    public init(transport:any ReadTransport) {self.transport=transport}
    public func source(_ context:InboxConversationFilesContext) async throws -> InboxPrioritySource {
        guard context.valid else {throw ReadFailure.invalidContext};let r=try await transport.get(ReadRequest(path:"/api/inbox/conversations/\(context.conversation)/"));guard r.status==200 else {throw r.status==403 ? ReadFailure.denied:r.status==404 ? .notFound:.unavailable};guard let s=InboxPrioritySource.decode(r.data,context:context) else {throw ReadFailure.invalidPayload};return s
    }
}
// Separate explicit fixture command and GET adapters. No HTTP command implementation.
public struct FixtureInboxPriorityPort:SyntheticInboxPriorityPort {
    private struct Scenario:Decodable,Sendable {let business:Int,conversation:Int,actor:Int,priority:String,outcome:String;let status:Int?;let response_json:String?}
    private struct Catalog:Decodable {let fixture_only:Bool;let grants:[SyntheticInboxPriorityGrant];let scenarios:[Scenario]}
    public let grants:[SyntheticInboxPriorityGrant];private let scenarios:[Scenario]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-priority.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {grants=c.grants;scenarios=c.scenarios} else {grants=[];scenarios=[]}}
    public func execute(_ a:InboxPriorityAttempt) async throws -> SyntheticInboxPriorityOutcome {let auth=a.review.authorization,c=auth.context;guard a.review.valid,grants.compactMap({$0.authorization(for:c)}).contains(auth),let s=scenarios.first(where:{$0.business==c.business && $0.conversation==c.conversation && $0.actor==auth.actor && $0.priority==a.review.value.rawValue}) else {return .rejectedWithoutWrite};if s.outcome=="response",let status=s.status,let raw=s.response_json {return .response(status:status,data:Data(raw.utf8))};return s.outcome=="rejected" ? .rejectedWithoutWrite:.unknown}
}
public struct FixtureInboxPriorityReadTransport:ReadTransport {
    private struct Row:Decodable,Sendable {let path:String,response_json:String}
    private struct Catalog:Decodable {let fixture_only:Bool;let reads:[Row]}
    private let rows:[Row]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-priority.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {rows=c.reads} else {rows=[]}}
    public func get(_ q:ReadRequest) async throws -> ReadResponse {guard q.query.isEmpty,let row=rows.first(where:{$0.path==q.path}) else {throw ReadFailure.invalidContext};return ReadResponse(status:200,data:Data(row.response_json.utf8))}
}
