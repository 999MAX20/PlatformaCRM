import Foundation

// TASKS.CREATE is injected independently of generic conversation GET and other task endpoints.
public struct SyntheticInboxCreateTaskGrant:Decodable,Sendable {
    public let business:Int,conversation:Int,actor:Int,create:Bool
    public init(business:Int,conversation:Int,actor:Int,create:Bool) {self.business=business;self.conversation=conversation;self.actor=actor;self.create=create}
    public func authorization(for c:InboxConversationFilesContext)->SyntheticInboxCreateTaskAuthorization? {guard c.valid,business==c.business,conversation==c.conversation,actor>0,actor<=Int(Int32.max),create else {return nil};return SyntheticInboxCreateTaskAuthorization(context:c,actor:actor)}
}
public struct SyntheticInboxCreateTaskAuthorization:Equatable,Sendable {public let context:InboxConversationFilesContext;public let actor:Int;fileprivate init(context:InboxConversationFilesContext,actor:Int) {self.context=context;self.actor=actor}}
public struct InboxCreateTaskReview:Equatable,Sendable {
    public let reference:QualifiedInboxTaskSource,authorization:SyntheticInboxCreateTaskAuthorization,visit:Int
    public var source:InboxTaskSource {reference.source}
    public init(reference:QualifiedInboxTaskSource,authorization:SyntheticInboxCreateTaskAuthorization,visit:Int) {self.reference=reference;self.authorization=authorization;self.visit=visit}
    public var valid:Bool {reference.valid && authorization.context==reference.context && authorization.actor>0 && visit>0}
}
public struct InboxCreateTaskAttempt:Equatable,Sendable {
    public let localID:Int,review:InboxCreateTaskReview
    public var path:String {"/api/inbox/conversations/\(review.source.context.conversation)/create-task/"}
    public var query:[String:String] {[:]}
    public var headers:[String:String] {[:]}
    public func preparedBody()->Data {Data("{}".utf8)}
}
// Narrow existing TaskSerializer result. The observed title is never reconstructed from hidden Client data.
public struct InboxCreateTaskReceipt:Equatable,Sendable {
    public let id:Int,business:Int,title:String,description:String,client:Int?,lead:Int?,assignee:Int,createdBy:Int,priority:String,dueAt:String?,updatedAt:String
    private init(id:Int,business:Int,title:String,description:String,client:Int?,lead:Int?,assignee:Int,createdBy:Int,priority:String,updatedAt:String) {self.id=id;self.business=business;self.title=title;self.description=description;self.client=client;self.lead=lead;self.assignee=assignee;self.createdBy=createdBy;self.priority=priority;dueAt=nil;self.updatedAt=updatedAt}
    public static func ==(a:Self,b:Self)->Bool {a.id==b.id && a.business==b.business && SourceTextIdentity.same(a.title,b.title) && SourceTextIdentity.same(a.description,b.description) && a.client==b.client && a.lead==b.lead && a.assignee==b.assignee && a.createdBy==b.createdBy && a.priority==b.priority && a.dueAt==b.dueAt && SourceTextIdentity.same(a.updatedAt,b.updatedAt)}
    public static func decode(_ data:Data,attempt a:InboxCreateTaskAttempt)->Self? {
        guard a.review.valid,let row=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let id=DirectoryReadJSON.integer(row["id"]),id>0,id<=Int64(Int32.max),DirectoryReadJSON.integer(row["business"])==Int64(a.review.source.context.business),let title=row["title"] as? String,!title.isEmpty,let description=row["description"] as? String,description.isEmpty,let priority=row["priority"] as? String,priority=="normal",row["due_at"] is NSNull,DirectoryReadJSON.integer(row["assignee"])==Int64(a.review.authorization.actor),DirectoryReadJSON.integer(row["created_by"])==Int64(a.review.authorization.actor),let updated=row["updated_at"] as? String,!updated.isEmpty else {return nil}
        for (key,value) in [("client",a.review.source.client),("lead",a.review.source.lead)] {guard let field=row[key] else {return nil};if let value {guard DirectoryReadJSON.integer(field)==Int64(value) else {return nil}} else {guard field is NSNull else {return nil}}}
        return Self(id:Int(id),business:a.review.source.context.business,title:title,description:description,client:a.review.source.client,lead:a.review.source.lead,assignee:a.review.authorization.actor,createdBy:a.review.authorization.actor,priority:priority,updatedAt:updated)
    }
}
public enum SyntheticInboxCreateTaskOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticInboxCreateTaskPort:Sendable {var grants:[SyntheticInboxCreateTaskGrant] {get};func execute(_ attempt:InboxCreateTaskAttempt) async throws -> SyntheticInboxCreateTaskOutcome}
public enum InboxCreateTaskPhase:Equatable,Sendable {case pending,response,rejected,unknown}
public struct InboxCreateTaskRecord:Equatable,Sendable {public let attempt:InboxCreateTaskAttempt;public var phase:InboxCreateTaskPhase;public var result:InboxCreateTaskReceipt?}
public struct InboxCreateTaskLedger:Sendable {
    public private(set) var records:[InboxCreateTaskRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:InboxConversationFilesContext)->String {"\(c.business)/\(c.conversation)"}
    public func blocked(business:Int,conversation:Int)->Bool {active["\(business)/\(conversation)"] != nil}
    public func visible(_ auth:SyntheticInboxCreateTaskAuthorization?)->InboxCreateTaskRecord? {guard let auth,let i=active[key(auth.context)],records[i].attempt.review.authorization.actor==auth.actor else {return nil};return records[i]}
    public mutating func begin(_ review:InboxCreateTaskReview)->InboxCreateTaskAttempt? {
        guard review.valid,!blocked(business:review.source.context.business,conversation:review.source.context.conversation) else {return nil};let a=InboxCreateTaskAttempt(localID:records.count+1,review:review);active[key(review.source.context)]=records.count;records.append(InboxCreateTaskRecord(attempt:a,phase:.pending,result:nil));return a
    }
    public mutating func complete(_ a:InboxCreateTaskAttempt,outcome:SyntheticInboxCreateTaskOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==a}),records[i].phase == .pending else {return}
        switch outcome {case .unknown:records[i].phase = .unknown;case .rejectedWithoutWrite:records[i].phase = .rejected;case .response(let status,let data):if status==201,let receipt=InboxCreateTaskReceipt.decode(data,attempt:a) {records[i].phase = .response;records[i].result=receipt} else {records[i].phase = .unknown}}
    }
    @discardableResult public mutating func acknowledge(_ auth:SyntheticInboxCreateTaskAuthorization,record:InboxCreateTaskRecord)->Bool {guard visible(auth)==record,record.phase == .response || record.phase == .rejected else {return false};active.removeValue(forKey:key(auth.context));return true}
}
// Explicit synthetic port only; generic GET lives in InboxTaskSourceRepository.
public struct FixtureInboxCreateTaskPort:SyntheticInboxCreateTaskPort {
    private struct Scenario:Decodable,Sendable {let business:Int,conversation:Int,actor:Int,original_client:Int?,original_lead:Int?,original_updated_at:String,outcome:String;let status:Int?;let response_json:String?}
    private struct Catalog:Decodable {let fixture_only:Bool;let grants:[SyntheticInboxCreateTaskGrant];let scenarios:[Scenario]}
    public let grants:[SyntheticInboxCreateTaskGrant];private let scenarios:[Scenario]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-create-task.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {grants=c.grants;scenarios=c.scenarios} else {grants=[];scenarios=[]}}
    public func execute(_ a:InboxCreateTaskAttempt) async throws -> SyntheticInboxCreateTaskOutcome {let auth=a.review.authorization,c=auth.context;guard a.review.valid,grants.compactMap({$0.authorization(for:c)}).contains(auth),let s=scenarios.first(where:{$0.business==c.business && $0.conversation==c.conversation && $0.actor==auth.actor && $0.original_client==a.review.source.client && $0.original_lead==a.review.source.lead && SourceTextIdentity.same($0.original_updated_at,a.review.source.updatedAt)}) else {return .rejectedWithoutWrite};if s.outcome=="response",let status=s.status,let raw=s.response_json {return .response(status:status,data:Data(raw.utf8))};return s.outcome=="rejected" ? .rejectedWithoutWrite:.unknown}
}
