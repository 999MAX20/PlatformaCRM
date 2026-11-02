import Foundation

// Explicit fake context only; keys are configured opaque test values, never GET metadata.
public struct SyntheticInboxReplyGrant:Decodable,Sendable {
    public let business:Int;public let conversation:Int;public let actor:Int;public let update:Bool;public let keys:[String]
    public init(business:Int,conversation:Int,actor:Int,update:Bool,keys:[String]) {self.business=business;self.conversation=conversation;self.actor=actor;self.update=update;self.keys=keys}
    public func authorization(for c:ReplyDraftContext)->SyntheticInboxReplyAuthorization? {
        guard c.valid,c.business==business,c.conversation==conversation,actor>0,update,!keys.isEmpty,keys.allSatisfy({!$0.isEmpty && $0.utf8.elementsEqual(SourceTextTrim.pythonStrip($0).utf8)}),Set(keys.map {Data($0.utf8)}).count==keys.count else {return nil}
        return SyntheticInboxReplyAuthorization(context:c,actor:actor,keys:keys)
    }
}
public struct SyntheticInboxReplyAuthorization:Equatable,Sendable {
    public let context:ReplyDraftContext;public let actor:Int;public let keys:[String]
    fileprivate init(context:ReplyDraftContext,actor:Int,keys:[String]) {self.context=context;self.actor=actor;self.keys=keys}
    public static func ==(lhs:Self,rhs:Self)->Bool {lhs.context==rhs.context && lhs.actor==rhs.actor && lhs.keys.map({Data($0.utf8)})==rhs.keys.map({Data($0.utf8)})}
}
public struct InboxReplyAttempt:Equatable,Sendable {
    public let localID:Int;public let authorization:SyntheticInboxReplyAuthorization;public let review:ReplyDraftReview;public let key:String
    private let bodyData:Data?
    init(localID:Int,authorization:SyntheticInboxReplyAuthorization,review:ReplyDraftReview,key:String) {
        self.localID=localID;self.authorization=authorization;self.review=review;self.key=key
        // Freeze the existing request-shaped body once; JSON object key order is not canonical evidence.
        bodyData=try? JSONSerialization.data(withJSONObject:["business":authorization.context.business,"text":review.text])
    }
    // Existing source request-shaped data only. No HTTP implementation.
    public var path:String {"/api/mobile/v1/inbox/\(authorization.context.conversation)/reply/"}
    public var preparedHeaders:[String:String] {["Idempotency-Key":key]}
    public func preparedBody()->Data? {bodyData}
    public static func ==(lhs:Self,rhs:Self)->Bool {lhs.localID==rhs.localID && lhs.authorization==rhs.authorization && lhs.review==rhs.review && lhs.key.utf8.elementsEqual(rhs.key.utf8) && lhs.bodyData==rhs.bodyData}
}
public enum SyntheticInboxReplyOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticInboxReplyPort:Sendable {var grants:[SyntheticInboxReplyGrant] {get};func execute(_ attempt:InboxReplyAttempt) async throws -> SyntheticInboxReplyOutcome}
public enum InboxReplyPhase:Equatable,Sendable {case pending,confirmed,rejected,unknown}
public enum InboxReplyDelivery:String,Sendable {case queued,sent,failed}
// Narrow existing HTTP200 reply receipt. No conversation model/GET source/provider error promotion.
public struct InboxReplyReceipt:Equatable,Sendable {
    public let conversation:Int;public let message:Int;public let text:String;public let delivery:InboxReplyDelivery;public let createdAt:String;public let sentAt:String?;public let replayed:Bool
    private struct NullableText:Decodable {
        let value:String?
        init(from decoder:any Decoder) throws {let c=try decoder.singleValueContainer();value=c.decodeNil() ? nil : try c.decode(String.self)}
    }
    private struct Flags:Decodable {
        struct Conversation:Decodable {let id:Int}
        struct Message:Decodable {let id:Int;let conversation_id:Int;let direction:String;let sender_type:String;let text:String;let status:String;let created_at:String;let sent_at:NullableText}
        let ok:Bool;let replayed:Bool;let conversation:Conversation;let message:Message
    }
    public static func decode(_ data:Data)->Self? {
        guard let flags=try? JSONDecoder().decode(Flags.self,from:data),flags.ok,let root=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let c=root["conversation"] as? [String:Any],let m=root["message"] as? [String:Any] else {return nil}
        func integer(_ o:[String:Any],_ key:String)->Int? {guard let n=o[key] as? NSNumber,["q","i","s","l","Q","I","S","L"].contains(String(cString:n.objCType)),n.int64Value>0,n.int64Value<=Int64(Int32.max),let v=Int(exactly:n.int64Value) else {return nil};return v}
        guard let conversation=integer(c,"id"),let parent=integer(m,"conversation_id"),conversation==parent,conversation==flags.conversation.id,parent==flags.message.conversation_id,let message=integer(m,"id"),message==flags.message.id,flags.message.direction=="outbound",flags.message.sender_type=="manager",let delivery=InboxReplyDelivery(rawValue:flags.message.status),TaskSnoozeValue.parse(flags.message.created_at) != nil else {return nil}
        let text=flags.message.text,created=flags.message.created_at,sent=flags.message.sent_at.value
        if let sent,TaskSnoozeValue.parse(sent)==nil {return nil}
        guard (delivery == .sent)==(sent != nil) else {return nil}
        return Self(conversation:conversation,message:message,text:text,delivery:delivery,createdAt:created,sentAt:sent,replayed:flags.replayed)
    }
    public func matches(_ attempt:InboxReplyAttempt)->Bool {
        //500 is response evidence size, not a manual input limit. Excerpt is not full-text proof.
        conversation==attempt.authorization.context.conversation && attempt.review.text.unicodeScalars.count<=500 && text.utf8.elementsEqual(attempt.review.text.utf8)
    }
}
public struct InboxReplyRecord:Equatable,Sendable {public let attempt:InboxReplyAttempt;public var phase:InboxReplyPhase;public var receipt:InboxReplyReceipt?}
public struct InboxReplyLedger:Sendable {
    public private(set) var records:[InboxReplyRecord]=[]
    private var active:[String:Int]=[:]
    private var usedKeys:[String:Set<Data>]=[:]
    public init() {}
    private func owner(_ c:ReplyDraftContext)->String {"\(c.business)/\(c.conversation)"}
    private func namespace(_ a:SyntheticInboxReplyAuthorization)->String {"\(a.context.business)/\(a.actor)"}
    private func nextKey(_ a:SyntheticInboxReplyAuthorization)->String? {a.keys.first {!(usedKeys[namespace(a)] ?? []).contains(Data($0.utf8))}}
    public func blocked(_ c:ReplyDraftContext)->Bool {active[owner(c)] != nil}
    public func visible(_ a:SyntheticInboxReplyAuthorization?)->InboxReplyRecord? {guard let a,let i=active[owner(a.context)],records[i].attempt.authorization==a else {return nil};return records[i]}
    public func canBegin(_ a:SyntheticInboxReplyAuthorization?)->Bool {guard let a else {return false};return !blocked(a.context) && nextKey(a) != nil}
    public mutating func begin(_ review:ReplyDraftReview,authorization a:SyntheticInboxReplyAuthorization)->InboxReplyAttempt? {
        guard review.selection.context==a.context,review.selection.generation>0,!review.text.isEmpty,review.text.utf8.elementsEqual(ReplyDraftText.stripped(review.raw).utf8),canBegin(a),let key=nextKey(a) else {return nil}
        let attempt=InboxReplyAttempt(localID:records.count+1,authorization:a,review:review,key:key)
        usedKeys[namespace(a),default:[]].insert(Data(key.utf8));active[owner(a.context)]=records.count;records.append(InboxReplyRecord(attempt:attempt,phase:.pending));return attempt
    }
    public mutating func complete(_ attempt:InboxReplyAttempt,outcome:SyntheticInboxReplyOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==attempt}),records[i].phase == .pending else {return}
        var phase:InboxReplyPhase = .unknown;var receipt:InboxReplyReceipt?
        switch outcome {case .unknown:break;case .rejectedWithoutWrite:phase = .rejected
        case .response(let status,let data):if status==200,let r=InboxReplyReceipt.decode(data),r.matches(attempt) {phase = .confirmed;receipt=r}}
        records[i].phase=phase;records[i].receipt=receipt
    }
    @discardableResult public mutating func acknowledge(_ a:SyntheticInboxReplyAuthorization)->Bool {guard let r=visible(a),r.phase == .confirmed || r.phase == .rejected else {return false};active.removeValue(forKey:owner(a.context));return true}
}
public struct FixtureInboxReplyPort:SyntheticInboxReplyPort {
    private struct Row:Sendable {let grant:SyntheticInboxReplyGrant;let outcome:String;let response:Data?}
    private struct Metadata:Decodable {struct Row:Decodable {let grant:SyntheticInboxReplyGrant;let outcome:String};let fixture_only:Bool;let scenarios:[Row]}
    private let rows:[Row]
    public var grants:[SyntheticInboxReplyGrant] {rows.map(\.grant)}
    public init(directory:URL) {
        if let data=try? Data(contentsOf:directory.appendingPathComponent("inbox-reply-outcome.json")),let meta=try? JSONDecoder().decode(Metadata.self,from:data),meta.fixture_only,let o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let items=o["scenarios"] as? [[String:Any]],items.count==meta.scenarios.count {
            rows=meta.scenarios.enumerated().map {i,row in
                let response:Data?;if let v=items[i]["response"],JSONSerialization.isValidJSONObject(v) {response=try? JSONSerialization.data(withJSONObject:v)} else {response=nil}
                return Row(grant:row.grant,outcome:row.outcome,response:response)
            }
        } else {rows=[]}
    }
    public func execute(_ attempt:InboxReplyAttempt) async throws -> SyntheticInboxReplyOutcome {
        guard let row=rows.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}),attempt.authorization.keys.contains(where:{$0.utf8.elementsEqual(attempt.key.utf8)}) else {return .unknown}
        if row.outcome=="rejected_without_write" {return .rejectedWithoutWrite}
        guard row.outcome=="response",let data=row.response,var o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],var message=o["message"] as? [String:Any] else {return .unknown}
        message["text"]=String(String.UnicodeScalarView(attempt.review.text.unicodeScalars.prefix(500)));o["message"]=message
        guard let reply=try? JSONSerialization.data(withJSONObject:o) else {return .unknown};return .response(status:200,data:reply)
    }
}
