import Foundation

// Manual text only. A read ticket is local freshness, never a Task entity version.
public struct TaskCommentContext: Equatable, Sendable {
    public let business: Int;public let task: Int;public let epoch: Int
    public init(business: Int,task: Int,epoch: Int) {self.business=business;self.task=task;self.epoch=epoch}
    public var valid: Bool {business>0 && task>0 && epoch>0}
}
public struct TaskCommentRead: Equatable, Sendable {
    public let context: TaskCommentContext;public let revision: Int
    public init(context: TaskCommentContext,revision: Int) {self.context=context;self.revision=revision}
}
public struct TaskCommentSelection: Equatable, Sendable {public let read: TaskCommentRead;public let generation: Int}
public enum TaskCommentPhase: Equatable, Sendable {case closed,editing,review}
public struct TaskCommentReview: Equatable, Sendable {public let selection: TaskCommentSelection;public let text: String
    public static func ==(lhs:Self,rhs:Self)->Bool {lhs.selection==rhs.selection && lhs.text.utf8.elementsEqual(rhs.text.utf8)}
}
public enum TaskCommentText {public static func preview(_ raw: String) -> String {SourceTextTrim.pythonStrip(SourceTextTrim.javascriptTrim(raw))}}
public protocol TaskCommentDraftSource: Sendable {func matchesFixture(_ detail: TaskDetails) async -> Bool}
public struct FixtureTaskCommentDraftSource: TaskCommentDraftSource {
    private let directory: URL
    public init(directory: URL) {self.directory=directory}
    // Pure fixture-reference comparison, not a production permission or raw JSON proof.
    public static func verified(_ detail:TaskDetails,reference:TaskDetails)->Bool {
        [101,202].contains(detail.business) && detail.valid(for:detail.business,id:detail.task.id) && reference==detail
    }
    public func matchesFixture(_ detail: TaskDetails) async -> Bool {
        guard [101,202].contains(detail.business),detail.valid(for:detail.business,id:detail.task.id),let data=try? Data(contentsOf:directory.appendingPathComponent("task-\(detail.business)-\(detail.task.id).json")),let reference=try? TaskDetails.decodeSource(data) else {return false}
        return Self.verified(detail,reference:reference)
    }
}
public struct TaskCommentSession: Sendable {
    public private(set) var read: TaskCommentRead?
    public private(set) var available=false
    public private(set) var selection: TaskCommentSelection?
    public private(set) var text=""
    public private(set) var emptyError=false
    public private(set) var phase: TaskCommentPhase = .closed
    public private(set) var review: TaskCommentReview?
    private var ownerBusiness: Int?,ownerEpoch: Int?,generation=0
    private var buffers: [Int:String]=[:]
    public init() {}
    private mutating func stash() {if available,let read {buffers[read.context.task]=text}}
    private mutating func hide() {generation += 1;available=false;selection=nil;text="";emptyError=false;phase = .closed;review=nil;read=nil}
    public mutating func retainOwner(business: Int?,epoch: Int?) {
        stash();hide()
        if ownerBusiness != business || ownerEpoch != epoch || business == nil || epoch == nil {buffers=[:]}
        ownerBusiness=business;ownerEpoch=epoch
    }
    public mutating func begin(_ next: TaskCommentRead?) {
        stash();hide()
        guard let next,next.context.valid,next.revision>0 else {buffers=[:];ownerBusiness=nil;ownerEpoch=nil;return}
        if ownerBusiness != next.context.business || ownerEpoch != next.context.epoch {buffers=[:]}
        ownerBusiness=next.context.business;ownerEpoch=next.context.epoch;read=next
    }
    public mutating func receive(verified: Bool,expected: TaskCommentRead) {
        guard read==expected else {return};stash();hide();read=expected;available=verified
        if verified {text=buffers[expected.context.task] ?? ""}
    }
    public mutating func pause() {stash();hide()}
    @discardableResult public mutating func open(expected: TaskCommentRead) -> Bool {
        guard read==expected,available else {return false}
        generation += 1;selection=TaskCommentSelection(read:expected,generation:generation);phase = .editing;review=nil;emptyError=false;return true
    }
    public mutating func update(_ value: String,expected: TaskCommentSelection) {
        guard selection==expected,available,phase == .editing else {return};text=value;emptyError=false;stash()
    }
    @discardableResult public mutating func prepare(expected: TaskCommentSelection) -> Bool {
        guard selection==expected,available,phase == .editing else {return false}
        let preview=TaskCommentText.preview(text);emptyError=preview.isEmpty;guard !emptyError else {return false}
        review=TaskCommentReview(selection:expected,text:preview);phase = .review;return true
    }
    public mutating func back(expected: TaskCommentSelection) {guard selection==expected else {return};if phase == .review {phase = .editing;review=nil} else {close(expected:expected)}}
    public mutating func close(expected: TaskCommentSelection) {guard selection==expected else {return};stash();generation += 1;selection=nil;review=nil;phase = .closed}
    public mutating func discard(expected: TaskCommentSelection) {guard selection==expected else {return};text="";emptyError=false;close(expected:expected)}
}
