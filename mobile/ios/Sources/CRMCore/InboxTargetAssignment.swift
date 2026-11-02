import Foundation

// Observed generic conversation only. No permission, version or command recovery inference.
public typealias InboxTargetAssignmentSource = InboxSelfAssignmentSource
// Qualified observed membership is identity/input, never command authorization.
public struct InboxTargetAssignmentCandidate:Equatable,Sendable {
    public let source:InboxTargetAssignmentSource
    public let reference:QualifiedMemberReference
    public init?(source:InboxTargetAssignmentSource,reference:QualifiedMemberReference) {guard source.valid,reference.valid,reference.context==source.context else {return nil};self.source=source;self.reference=reference}
    public var valid:Bool {source.valid && reference.valid && reference.context==source.context}
}
public struct SyntheticInboxTargetAssignmentGrant:Decodable,Sendable {
    public let business:Int,conversation:Int,actor:Int,manage:Bool
    public init(business:Int,conversation:Int,actor:Int,manage:Bool) {self.business=business;self.conversation=conversation;self.actor=actor;self.manage=manage}
    public func authorization(for c:InboxConversationFilesContext)->SyntheticInboxTargetAssignmentAuthorization? {guard c.valid,business==c.business,conversation==c.conversation,actor>0,actor<=Int(Int32.max),manage else {return nil};return SyntheticInboxTargetAssignmentAuthorization(context:c,actor:actor)}
}
public struct SyntheticInboxTargetAssignmentAuthorization:Equatable,Sendable {public let context:InboxConversationFilesContext;public let actor:Int;fileprivate init(context:InboxConversationFilesContext,actor:Int) {self.context=context;self.actor=actor}}
// Injected separately from actor MANAGE and separately from observed GET is_active.
public struct SyntheticInboxTargetMembershipContext:Decodable,Equatable,Sendable {
    public let business:Int,user:Int,active_member:Bool
    public init(business:Int,user:Int,activeMember:Bool) {self.business=business;self.user=user;active_member=activeMember}
    public func matches(_ ref:QualifiedMemberReference)->Bool {ref.valid && business==ref.context.business && user==ref.source.user.id && active_member}
}
public struct InboxTargetAssignmentReview:Equatable,Sendable {
    public let source:InboxTargetAssignmentSource,authorization:SyntheticInboxTargetAssignmentAuthorization,candidate:InboxTargetAssignmentCandidate,targetMembership:SyntheticInboxTargetMembershipContext,visit:Int
    public init(source:InboxTargetAssignmentSource,authorization:SyntheticInboxTargetAssignmentAuthorization,candidate:InboxTargetAssignmentCandidate,targetMembership:SyntheticInboxTargetMembershipContext,visit:Int) {self.source=source;self.authorization=authorization;self.candidate=candidate;self.targetMembership=targetMembership;self.visit=visit}
    public var valid:Bool {source.valid && candidate.valid && candidate.source==source && authorization.context==source.context && authorization.actor>0 && targetMembership.matches(candidate.reference) && visit>0}
}
public struct InboxTargetAssignmentAttempt:Equatable,Sendable {
    public let localID:Int,review:InboxTargetAssignmentReview
    public var path:String {"/api/inbox/conversations/\(review.source.context.conversation)/assign/"}
    public var query:[String:String] {[:]}
    public var headers:[String:String] {[:]}
    public func preparedBody()->Data {Data("{\"user_id\":\(review.candidate.reference.source.user.id)}".utf8)}
}
public struct InboxTargetAssignmentReceipt:Equatable,Sendable {
    public let source:InboxTargetAssignmentSource
    public static func decode(_ data:Data,attempt a:InboxTargetAssignmentAttempt)->Self? {
        guard a.review.valid,let source=InboxTargetAssignmentSource.decode(data,context:a.review.source.context),source.assignedTo==a.review.candidate.reference.source.user.id else {return nil};return Self(source:source)
    }
}
public enum SyntheticInboxTargetAssignmentOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticInboxTargetAssignmentPort:Sendable {var grants:[SyntheticInboxTargetAssignmentGrant] {get};var targetMemberships:[SyntheticInboxTargetMembershipContext] {get};func execute(_ attempt:InboxTargetAssignmentAttempt) async throws -> SyntheticInboxTargetAssignmentOutcome}
public enum InboxTargetAssignmentPhase:Equatable,Sendable {case pending,response,rejected,unknown}
public struct InboxTargetAssignmentRecord:Equatable,Sendable {public let attempt:InboxTargetAssignmentAttempt;public var phase:InboxTargetAssignmentPhase;public var result:InboxTargetAssignmentReceipt?}
public struct InboxTargetAssignmentLedger:Sendable {
    public private(set) var records:[InboxTargetAssignmentRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:InboxConversationFilesContext)->String {"\(c.business)/\(c.conversation)"}
    public func blocked(business:Int,conversation:Int)->Bool {active["\(business)/\(conversation)"] != nil}
    public func visible(_ auth:SyntheticInboxTargetAssignmentAuthorization?)->InboxTargetAssignmentRecord? {guard let auth,let i=active[key(auth.context)],records[i].attempt.review.authorization.actor==auth.actor else {return nil};return records[i]}
    public mutating func begin(_ review:InboxTargetAssignmentReview)->InboxTargetAssignmentAttempt? {
        guard review.valid,!blocked(business:review.source.context.business,conversation:review.source.context.conversation) else {return nil};let a=InboxTargetAssignmentAttempt(localID:records.count+1,review:review);active[key(review.source.context)]=records.count;records.append(InboxTargetAssignmentRecord(attempt:a,phase:.pending,result:nil));return a
    }
    public mutating func complete(_ a:InboxTargetAssignmentAttempt,outcome:SyntheticInboxTargetAssignmentOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==a}),records[i].phase == .pending else {return}
        switch outcome {case .unknown:records[i].phase = .unknown;case .rejectedWithoutWrite:records[i].phase = .rejected;case .response(let status,let data):if status==200,let receipt=InboxTargetAssignmentReceipt.decode(data,attempt:a) {records[i].phase = .response;records[i].result=receipt} else {records[i].phase = .unknown}}
    }
    @discardableResult public mutating func acknowledge(_ auth:SyntheticInboxTargetAssignmentAuthorization,record:InboxTargetAssignmentRecord)->Bool {guard visible(auth)==record,record.phase == .response || record.phase == .rejected else {return false};active.removeValue(forKey:key(auth.context));return true}
}
public protocol InboxTargetAssignmentRepository:Sendable {func source(_ context:InboxConversationFilesContext) async throws -> InboxTargetAssignmentSource}
public struct APIInboxTargetAssignmentRepository:InboxTargetAssignmentRepository {
    private let transport:any ReadTransport
    public init(transport:any ReadTransport) {self.transport=transport}
    public func source(_ context:InboxConversationFilesContext) async throws -> InboxTargetAssignmentSource {
        guard context.valid else {throw ReadFailure.invalidContext};let r=try await transport.get(ReadRequest(path:"/api/inbox/conversations/\(context.conversation)/"));guard r.status==200 else {throw r.status==403 ? ReadFailure.denied:r.status==404 ? .notFound:.unavailable};guard let s=InboxTargetAssignmentSource.decode(r.data,context:context) else {throw ReadFailure.invalidPayload};return s
    }
}
// Separate explicit fixture command and GET adapters. No HTTP command implementation.
public struct FixtureInboxTargetAssignmentPort:SyntheticInboxTargetAssignmentPort {
    private struct Scenario:Decodable,Sendable {let business:Int,conversation:Int,actor:Int,user_id:Int,member_id:Int,original_assigned_to:Int?,outcome:String;let status:Int?;let response_json:String?}
    private struct Catalog:Decodable {let fixture_only:Bool;let grants:[SyntheticInboxTargetAssignmentGrant];let target_memberships:[SyntheticInboxTargetMembershipContext];let scenarios:[Scenario]}
    public let grants:[SyntheticInboxTargetAssignmentGrant];public let targetMemberships:[SyntheticInboxTargetMembershipContext];private let scenarios:[Scenario]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-target-assignment.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {grants=c.grants;targetMemberships=c.target_memberships;scenarios=c.scenarios} else {grants=[];targetMemberships=[];scenarios=[]}}
    public func execute(_ a:InboxTargetAssignmentAttempt) async throws -> SyntheticInboxTargetAssignmentOutcome {let auth=a.review.authorization,c=auth.context;guard a.review.valid,grants.compactMap({$0.authorization(for:c)}).contains(auth),targetMemberships.contains(a.review.targetMembership),let s=scenarios.first(where:{$0.business==c.business && $0.conversation==c.conversation && $0.actor==auth.actor && $0.user_id==a.review.candidate.reference.source.user.id && $0.member_id==a.review.candidate.reference.source.id && $0.original_assigned_to==a.review.source.assignedTo}) else {return .rejectedWithoutWrite};if s.outcome=="response",let status=s.status,let raw=s.response_json {return .response(status:status,data:Data(raw.utf8))};return s.outcome=="rejected" ? .rejectedWithoutWrite:.unknown}
}
public struct FixtureInboxTargetAssignmentReadTransport:ReadTransport {
    private struct Row:Decodable,Sendable {let path:String,response_json:String}
    private struct Catalog:Decodable {let fixture_only:Bool;let reads:[Row]}
    private let rows:[Row]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-target-assignment.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {rows=c.reads} else {rows=[]}}
    public func get(_ q:ReadRequest) async throws -> ReadResponse {guard q.query.isEmpty,let row=rows.first(where:{$0.path==q.path}) else {throw ReadFailure.invalidContext};return ReadResponse(status:200,data:Data(row.response_json.utf8))}
}
