import Foundation

public enum ReplyDraftText { public static func stripped(_ raw: String) -> String { SourceTextTrim.pythonStrip(raw) } }
public struct ReplyDraftContext: Equatable, Sendable {
    public let business: Int; public let conversation: Int; public let epoch: Int
    public init(business: Int,conversation: Int,epoch: Int) { self.business=business;self.conversation=conversation;self.epoch=epoch }
    public var valid: Bool { business > 0 && conversation > 0 && epoch > 0 }
}
public struct ReplyDraftSelection: Equatable, Sendable { public let context: ReplyDraftContext; public let generation: Int }
public enum ReplyDraftPhase: Equatable, Sendable { case closed, editing, review }
public struct ReplyDraftReview: Equatable, Sendable {
    public let selection: ReplyDraftSelection;public let text:String;public let raw:String
    public static func ==(lhs:Self,rhs:Self)->Bool {lhs.selection==rhs.selection && lhs.text.utf8.elementsEqual(rhs.text.utf8) && lhs.raw.utf8.elementsEqual(rhs.raw.utf8)}
}
// Own manual text only. Memory is isolated by Business/epoch; no durable queue,
// session authority, sent message, read marker or server command is represented.
public struct ReplyDraftSession: Sendable {
    public private(set) var context: ReplyDraftContext?
    public private(set) var available = false
    public private(set) var selection: ReplyDraftSelection?
    public private(set) var text = ""
    public private(set) var emptyError = false
    public private(set) var phase: ReplyDraftPhase = .closed
    public private(set) var review: ReplyDraftReview?
    private var buffers: [Int:String] = [:]
    private var generation = 0
    public init() {}
    private mutating func stash() {
        guard available,let context else { return }
        if text.isEmpty { buffers.removeValue(forKey:context.conversation) } else { buffers[context.conversation]=text }
    }
    public mutating func bind(_ next: ReplyDraftContext?,available nextAvailable: Bool) {
        guard let next,next.valid else { clear();return }
        let sameOwner = context?.business == next.business && context?.epoch == next.epoch
        if sameOwner { stash() } else { buffers = [:] }
        let changed = context != next || !available || !nextAvailable
        if changed { generation += 1;selection=nil;review=nil;phase = .closed;emptyError=false }
        context=next;available=nextAvailable
        if changed { text=nextAvailable ? (buffers[next.conversation] ?? "") : "" }
    }
    public mutating func retainOwner(business: Int?,epoch: Int?) {
        guard let context,context.business == business,context.epoch == epoch else { clear();return }
        pause()
    }
    public mutating func pause() {
        stash();generation += 1;available=false;selection=nil;review=nil;phase = .closed;text="";emptyError=false
    }
    @discardableResult public mutating func open(expected: ReplyDraftContext) -> Bool {
        guard available,context == expected else { return false }
        generation += 1;selection=ReplyDraftSelection(context:expected,generation:generation);review=nil;phase = .editing;emptyError=false;return true
    }
    public mutating func update(_ value: String,expected: ReplyDraftSelection) {
        guard selection == expected,available,phase == .editing else { return }
        text=value;emptyError=false;stash()
    }
    @discardableResult public mutating func insertTemplate(_ value: String,expected: ReplyDraftSelection) -> Bool {
        guard selection==expected,available,phase == .editing,!SourceTextTrim.pythonStrip(value).isEmpty else {return false}
        text=QuickReplyInsertion.text(draft:text,template:value);emptyError=false;stash()
        generation += 1;selection=ReplyDraftSelection(context:expected.context,generation:generation);return true
    }
    @discardableResult public mutating func prepare(expected: ReplyDraftSelection) -> Bool {
        guard selection == expected,available,phase == .editing else { return false }
        let preview=ReplyDraftText.stripped(text)
        guard !preview.isEmpty else { emptyError=true;return false }
        emptyError=false;review=ReplyDraftReview(selection:expected,text:preview,raw:text);phase = .review;return true
    }
    public mutating func back(expected: ReplyDraftSelection) {
        guard selection == expected else { return }
        if phase == .review { phase = .editing;review=nil } else { close(expected:expected) }
    }
    public mutating func close(expected: ReplyDraftSelection) {
        guard selection == expected else { return }
        stash();generation += 1;selection=nil;review=nil;phase = .closed
    }
    public mutating func discard(expected: ReplyDraftSelection) {
        guard selection == expected,let context else { return }
        text="";buffers.removeValue(forKey:context.conversation);close(expected:expected);emptyError=false
    }
    public mutating func clear() {
        generation += 1;context=nil;available=false;selection=nil;text="";emptyError=false;phase = .closed;review=nil;buffers=[:]
    }
}
