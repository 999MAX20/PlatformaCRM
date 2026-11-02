import Foundation

// Observed generic conversation only. No permission, version or command recovery inference.
public struct InboxSelfAssignmentSource:Equatable,Sendable {
    public let context:InboxConversationFilesContext,assignedTo:Int?,updatedAt:String
    private init(_ context:InboxConversationFilesContext,_ assigned:Int?,_ updated:String) {self.context=context;assignedTo=assigned;updatedAt=updated}
    public var valid:Bool {context.valid && !updatedAt.isEmpty && (assignedTo==nil || assignedTo!>0)}
    public static func ==(a:Self,b:Self)->Bool {a.context==b.context && a.assignedTo==b.assignedTo && SourceTextIdentity.same(a.updatedAt,b.updatedAt)}
    public static func decode(_ data:Data,context c:InboxConversationFilesContext)->Self? {
        guard c.valid,let row=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],InboxFileReadJSON.anchor(row,business:c.business,conversation:c.conversation),let value=row["assigned_to"],let updated=row["updated_at"] as? String,!updated.isEmpty else {return nil}
        if value is NSNull {return Self(c,nil,updated)}
        guard let id=DirectoryReadJSON.integer(value),id>0,id<=Int64(Int32.max) else {return nil};return Self(c,Int(id),updated)
    }
}
public struct SyntheticInboxSelfAssignmentGrant:Decodable,Sendable {
    public let business:Int,conversation:Int,actor:Int,manage:Bool,active_member:Bool
    public init(business:Int,conversation:Int,actor:Int,manage:Bool,activeMember:Bool) {self.business=business;self.conversation=conversation;self.actor=actor;self.manage=manage;active_member=activeMember}
    public func authorization(for c:InboxConversationFilesContext)->SyntheticInboxSelfAssignmentAuthorization? {guard c.valid,business==c.business,conversation==c.conversation,actor>0,actor<=Int(Int32.max),manage,active_member else {return nil};return SyntheticInboxSelfAssignmentAuthorization(context:c,actor:actor)}
}
public struct SyntheticInboxSelfAssignmentAuthorization:Equatable,Sendable {public let context:InboxConversationFilesContext;public let actor:Int;fileprivate init(context:InboxConversationFilesContext,actor:Int) {self.context=context;self.actor=actor}}
public struct InboxSelfAssignmentReview:Equatable,Sendable {
    public let source:InboxSelfAssignmentSource,authorization:SyntheticInboxSelfAssignmentAuthorization,visit:Int
    public init(source:InboxSelfAssignmentSource,authorization:SyntheticInboxSelfAssignmentAuthorization,visit:Int) {self.source=source;self.authorization=authorization;self.visit=visit}
    public var valid:Bool {source.valid && authorization.context==source.context && authorization.actor>0 && visit>0}
}
public struct InboxSelfAssignmentAttempt:Equatable,Sendable {
    public let localID:Int,review:InboxSelfAssignmentReview
    public var path:String {"/api/inbox/conversations/\(review.source.context.conversation)/assign/"}
    public var query:[String:String] {[:]}
    public var headers:[String:String] {[:]}
    public func preparedBody()->Data {Data("{}".utf8)}
}
public struct InboxSelfAssignmentReceipt:Equatable,Sendable {
    public let source:InboxSelfAssignmentSource
    public static func decode(_ data:Data,attempt a:InboxSelfAssignmentAttempt)->Self? {guard a.review.valid,let source=InboxSelfAssignmentSource.decode(data,context:a.review.source.context),source.assignedTo==a.review.authorization.actor else {return nil};return Self(source:source)}
}
public enum SyntheticInboxSelfAssignmentOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticInboxSelfAssignmentPort:Sendable {var grants:[SyntheticInboxSelfAssignmentGrant] {get};func execute(_ attempt:InboxSelfAssignmentAttempt) async throws -> SyntheticInboxSelfAssignmentOutcome}
public enum InboxSelfAssignmentPhase:Equatable,Sendable {case pending,response,rejected,unknown}
public struct InboxSelfAssignmentRecord:Equatable,Sendable {public let attempt:InboxSelfAssignmentAttempt;public var phase:InboxSelfAssignmentPhase;public var result:InboxSelfAssignmentReceipt?}
public struct InboxSelfAssignmentLedger:Sendable {
    public private(set) var records:[InboxSelfAssignmentRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:InboxConversationFilesContext)->String {"\(c.business)/\(c.conversation)"}
    public func blocked(business:Int,conversation:Int)->Bool {active["\(business)/\(conversation)"] != nil}
    public func visible(_ auth:SyntheticInboxSelfAssignmentAuthorization?)->InboxSelfAssignmentRecord? {guard let auth,let i=active[key(auth.context)],records[i].attempt.review.authorization.actor==auth.actor else {return nil};return records[i]}
    public mutating func begin(_ review:InboxSelfAssignmentReview)->InboxSelfAssignmentAttempt? {
        guard review.valid,!blocked(business:review.source.context.business,conversation:review.source.context.conversation) else {return nil};let a=InboxSelfAssignmentAttempt(localID:records.count+1,review:review);active[key(review.source.context)]=records.count;records.append(InboxSelfAssignmentRecord(attempt:a,phase:.pending,result:nil));return a
    }
    public mutating func complete(_ a:InboxSelfAssignmentAttempt,outcome:SyntheticInboxSelfAssignmentOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==a}),records[i].phase == .pending else {return}
        switch outcome {case .unknown:records[i].phase = .unknown;case .rejectedWithoutWrite:records[i].phase = .rejected;case .response(let status,let data):if status==200,let receipt=InboxSelfAssignmentReceipt.decode(data,attempt:a) {records[i].phase = .response;records[i].result=receipt} else {records[i].phase = .unknown}}
    }
    @discardableResult public mutating func acknowledge(_ auth:SyntheticInboxSelfAssignmentAuthorization,record:InboxSelfAssignmentRecord)->Bool {guard visible(auth)==record,record.phase == .response || record.phase == .rejected else {return false};active.removeValue(forKey:key(auth.context));return true}
}
public protocol InboxSelfAssignmentRepository:Sendable {func source(_ context:InboxConversationFilesContext) async throws -> InboxSelfAssignmentSource}
public struct APIInboxSelfAssignmentRepository:InboxSelfAssignmentRepository {
    private let transport:any ReadTransport
    public init(transport:any ReadTransport) {self.transport=transport}
    public func source(_ context:InboxConversationFilesContext) async throws -> InboxSelfAssignmentSource {
        guard context.valid else {throw ReadFailure.invalidContext};let r=try await transport.get(ReadRequest(path:"/api/inbox/conversations/\(context.conversation)/"));guard r.status==200 else {throw r.status==403 ? ReadFailure.denied:r.status==404 ? .notFound:.unavailable};guard let s=InboxSelfAssignmentSource.decode(r.data,context:context) else {throw ReadFailure.invalidPayload};return s
    }
}
// Separate explicit fixture command and GET adapters. No HTTP command implementation.
public struct FixtureInboxSelfAssignmentPort:SyntheticInboxSelfAssignmentPort {
    private struct Scenario:Decodable,Sendable {let business:Int,conversation:Int,actor:Int,outcome:String;let status:Int?;let response_json:String?}
    private struct Catalog:Decodable {let fixture_only:Bool;let grants:[SyntheticInboxSelfAssignmentGrant];let scenarios:[Scenario]}
    public let grants:[SyntheticInboxSelfAssignmentGrant];private let scenarios:[Scenario]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-self-assignment.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {grants=c.grants;scenarios=c.scenarios} else {grants=[];scenarios=[]}}
    public func execute(_ a:InboxSelfAssignmentAttempt) async throws -> SyntheticInboxSelfAssignmentOutcome {let auth=a.review.authorization,c=auth.context;guard a.review.valid,grants.compactMap({$0.authorization(for:c)}).contains(auth),let s=scenarios.first(where:{$0.business==c.business && $0.conversation==c.conversation && $0.actor==auth.actor}) else {return .rejectedWithoutWrite};if s.outcome=="response",let status=s.status,let raw=s.response_json {return .response(status:status,data:Data(raw.utf8))};return s.outcome=="rejected" ? .rejectedWithoutWrite:.unknown}
}
public struct FixtureInboxSelfAssignmentReadTransport:ReadTransport {
    private struct Row:Decodable,Sendable {let path:String,response_json:String}
    private struct Catalog:Decodable {let fixture_only:Bool;let reads:[Row]}
    private let rows:[Row]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-self-assignment.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {rows=c.reads} else {rows=[]}}
    public func get(_ q:ReadRequest) async throws -> ReadResponse {guard q.query.isEmpty,let row=rows.first(where:{$0.path==q.path}) else {throw ReadFailure.invalidContext};return ReadResponse(status:200,data:Data(row.response_json.utf8))}
}
