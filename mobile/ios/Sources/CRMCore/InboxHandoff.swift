import Foundation

public struct HandoffReason:Equatable,Sendable {
    public let raw:String;public let reason:String
    private init(raw:String,reason:String) {self.raw=raw;self.reason=reason}
    public static func make(_ raw:String)->Self? {let value=SourceTextTrim.pythonStrip(raw);guard !value.unicodeScalars.contains(where:{$0.value==0}) else {return nil};return Self(raw:raw,reason:value)}
    public static func ==(lhs:Self,rhs:Self)->Bool {lhs.raw.utf8.elementsEqual(rhs.raw.utf8) && lhs.reason.utf8.elementsEqual(rhs.reason.utf8)}
}
public struct HandoffReview:Equatable,Sendable {public let selection:ReplyDraftSelection;public let value:HandoffReason}
// Own new reason only, never a prefill/roundtrip of an unexposed original reason.
public struct HandoffDraftSession:Sendable {
    public private(set) var context:ReplyDraftContext?;public private(set) var available=false
    public private(set) var selection:ReplyDraftSelection?;public private(set) var phase:ReplyDraftPhase = .closed
    public private(set) var raw="";public private(set) var inputError=false;public private(set) var review:HandoffReview?
    private var buffers:[Int:String]=[:];private var generation=0
    public init() {}
    private mutating func stash() {if available,let context {buffers[context.conversation]=raw}}
    public mutating func bind(_ next:ReplyDraftContext?,available:Bool) {
        guard let next,next.valid else {clear();return}
        if context?.business==next.business && context?.epoch==next.epoch {stash()} else {buffers=[:]}
        let changed=context != next || !self.available || !available
        if changed {generation += 1;selection=nil;review=nil;phase = .closed;inputError=false}
        context=next;self.available=available;if changed {raw=available ? (buffers[next.conversation] ?? "") : ""}
    }
    public mutating func retainOwner(business:Int?,epoch:Int?) {guard let context,context.business==business,context.epoch==epoch else {clear();return};pause()}
    public mutating func pause() {stash();generation += 1;available=false;selection=nil;review=nil;phase = .closed;raw="";inputError=false}
    @discardableResult public mutating func open(_ c:ReplyDraftContext)->Bool {guard c==context,available,selection==nil else {return false};generation += 1;selection=ReplyDraftSelection(context:c,generation:generation);phase = .editing;review=nil;inputError=false;return true}
    public mutating func update(_ raw:String,selection:ReplyDraftSelection) {guard self.selection==selection,available,phase == .editing else {return};self.raw=raw;inputError=false;stash()}
    @discardableResult public mutating func prepare(_ selection:ReplyDraftSelection)->Bool {guard self.selection==selection,available,phase == .editing else {return false};guard let value=HandoffReason.make(raw) else {inputError=true;return false};review=HandoffReview(selection:selection,value:value);inputError=false;phase = .review;return true}
    public mutating func back(_ selection:ReplyDraftSelection) {guard self.selection==selection else {return};if phase == .review {phase = .editing;review=nil} else {close(selection)}}
    public mutating func close(_ selection:ReplyDraftSelection) {guard self.selection==selection else {return};stash();generation += 1;self.selection=nil;review=nil;phase = .closed}
    public mutating func discard(_ selection:ReplyDraftSelection) {guard self.selection==selection else {return};raw="";stash();close(selection);inputError=false}
    public mutating func clear() {generation += 1;context=nil;available=false;selection=nil;phase = .closed;raw="";inputError=false;review=nil;buffers=[:]}
}
public struct SyntheticHandoffGrant:Decodable,Equatable,Sendable {
    public let business:Int;public let conversation:Int;public let actor:Int;public let update:Bool
    public init(business:Int,conversation:Int,actor:Int,update:Bool) {self.business=business;self.conversation=conversation;self.actor=actor;self.update=update}
    public func authorization(_ c:ReplyDraftContext)->SyntheticHandoffAuthorization? {guard c.valid,c.business==business,c.conversation==conversation,actor>0,update else {return nil};return SyntheticHandoffAuthorization(context:c,actor:actor)}
}
public struct SyntheticHandoffAuthorization:Equatable,Sendable {public let context:ReplyDraftContext;public let actor:Int;fileprivate init(context:ReplyDraftContext,actor:Int) {self.context=context;self.actor=actor}}
public struct HandoffAttempt:Equatable,Sendable {
    public let localID:Int;public let authorization:SyntheticHandoffAuthorization;public let review:HandoffReview
    // Existing web action request shape only, not an added read/live route. No server key/version contract.
    public var path:String {"/api/inbox/conversations/\(authorization.context.conversation)/handoff/"}
    public var preparedHeaders:[String:String] {[:]}
    public func preparedBody()->Data? {try? JSONSerialization.data(withJSONObject:["reason":review.value.reason])}
}
public enum SyntheticHandoffOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticHandoffPort:Sendable {var grants:[SyntheticHandoffGrant] {get};func execute(_ attempt:HandoffAttempt) async throws -> SyntheticHandoffOutcome}
public enum HandoffPhase:Equatable,Sendable {case pending,confirmed,rejected,unknown}
public struct HandoffReceipt:Equatable,Sendable {
    public let business:Int;public let conversation:Int;public let reason:String;public let updatedAt:String
    private struct Flags:Decodable {let id:Int;let business:Int;let handoff_required:Bool;let bot_enabled:Bool;let handoff_reason:String;let updated_at:String}
    public static func decode(_ data:Data)->Self? {
        guard let flags=try? JSONDecoder().decode(Flags.self,from:data),flags.handoff_required,!flags.bot_enabled,let o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],TaskSnoozeValue.parse(flags.updated_at) != nil else {return nil}
        func integer(_ key:String)->Int? {guard let n=o[key] as? NSNumber,["q","i","s","l","Q","I","S","L"].contains(String(cString:n.objCType)),n.int64Value>0,n.int64Value<=Int64(Int32.max) else {return nil};return Int(n.int64Value)}
        guard let business=integer("business"),let conversation=integer("id"),business==flags.business,conversation==flags.id else {return nil};return Self(business:business,conversation:conversation,reason:flags.handoff_reason,updatedAt:flags.updated_at)
    }
    public func matches(_ a:HandoffAttempt)->Bool {business==a.authorization.context.business && conversation==a.authorization.context.conversation && reason.utf8.elementsEqual(a.review.value.reason.utf8)}
}
public struct HandoffRecord:Equatable,Sendable {public let attempt:HandoffAttempt;public var phase:HandoffPhase;public var receipt:HandoffReceipt?}
public struct HandoffLedger:Sendable {
    public private(set) var records:[HandoffRecord]=[];private var active:[String:Int]=[:]
    public init() {}
    private func owner(_ c:ReplyDraftContext)->String {"\(c.business)/\(c.conversation)"}
    public func blocked(_ c:ReplyDraftContext)->Bool {active[owner(c)] != nil}
    public func visible(_ a:SyntheticHandoffAuthorization?)->HandoffRecord? {guard let a,let i=active[owner(a.context)],records[i].attempt.authorization==a else {return nil};return records[i]}
    public mutating func begin(_ r:HandoffReview,authorization a:SyntheticHandoffAuthorization)->HandoffAttempt? {guard r.selection.context==a.context,r.selection.generation>0,HandoffReason.make(r.value.raw)==r.value,!blocked(a.context) else {return nil};let attempt=HandoffAttempt(localID:records.count+1,authorization:a,review:r);active[owner(a.context)]=records.count;records.append(HandoffRecord(attempt:attempt,phase:.pending));return attempt}
    public mutating func complete(_ a:HandoffAttempt,outcome:SyntheticHandoffOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==a}),records[i].phase == .pending else {return};var phase:HandoffPhase = .unknown;var receipt:HandoffReceipt?
        switch outcome {case .unknown:break;case .rejectedWithoutWrite:phase = .rejected;case .response(let status,let data):if status==200,let value=HandoffReceipt.decode(data),value.matches(a) {phase = .confirmed;receipt=value}}
        records[i].phase=phase;records[i].receipt=receipt
    }
    @discardableResult public mutating func acknowledge(_ a:SyntheticHandoffAuthorization)->Bool {guard let r=visible(a),r.phase == .confirmed || r.phase == .rejected else {return false};active.removeValue(forKey:owner(a.context));return true}
}
public struct FixtureHandoffPort:SyntheticHandoffPort {
    private struct Metadata:Decodable {struct Row:Decodable {let grant:SyntheticHandoffGrant;let outcome:String};let fixture_only:Bool;let scenarios:[Row]}
    private struct Row:Sendable {let grant:SyntheticHandoffGrant;let outcome:String;let response:Data?}
    private let rows:[Row];public var grants:[SyntheticHandoffGrant] {rows.map(\.grant)}
    public init(directory:URL) {
        if let data=try? Data(contentsOf:directory.appendingPathComponent("inbox-handoff-outcome.json")),let meta=try? JSONDecoder().decode(Metadata.self,from:data),meta.fixture_only,let o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let values=o["scenarios"] as? [[String:Any]],values.count==meta.scenarios.count {
            rows=meta.scenarios.enumerated().map {i,r in let v=values[i]["response"];let data=v.flatMap {JSONSerialization.isValidJSONObject($0) ? try? JSONSerialization.data(withJSONObject:$0):nil};return Row(grant:r.grant,outcome:r.outcome,response:data)}
        } else {rows=[]}
    }
    public func execute(_ a:HandoffAttempt) async throws -> SyntheticHandoffOutcome {
        guard let row=rows.first(where:{$0.grant.authorization(a.authorization.context)==a.authorization}) else {return .unknown}
        if row.outcome=="rejected_without_write" {return .rejectedWithoutWrite}
        guard row.outcome=="response",let data=row.response,var o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any] else {return .unknown};o["handoff_reason"]=a.review.value.reason
        guard let data=try? JSONSerialization.data(withJSONObject:o) else {return .unknown};return .response(status:200,data:data)
    }
}
