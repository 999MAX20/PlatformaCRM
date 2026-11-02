import Foundation

public enum TaskCancelReasonProblem: String,Sendable {case minimum,maximum,characters}
public enum TaskCancelReasonText {
    public static func preview(_ raw: String) -> String {TaskCommentText.preview(raw)}
    public static func problem(_ raw: String) -> TaskCancelReasonProblem? {
        let web=SourceTextTrim.javascriptTrim(raw),value=preview(raw)
        if web.utf16.count<3 || value.unicodeScalars.count<3 {return .minimum}
        if value.unicodeScalars.count>2000 {return .maximum}
        if value.unicodeScalars.contains(where:{$0.value==0}) {return .characters}
        return nil
    }
}
// Distinct event type; a comment selection cannot be passed to this editor.
public struct TaskCancelReasonSelection: Equatable,Sendable {
    fileprivate let source: TaskCommentSelection
    public var read: TaskCommentRead {source.read}
}
public struct TaskCancelReasonReview: Equatable,Sendable {public let selection: TaskCancelReasonSelection;public let text: String}
public struct TaskCancelReasonSession: Sendable {
    // Reuse the existing manual Task-text RAM engine, never its instance/input.
    private var manual=TaskCommentSession()
    public private(set) var problem: TaskCancelReasonProblem?
    public var read: TaskCommentRead? {manual.read}
    public var available: Bool {manual.available}
    public var text: String {manual.text}
    public var phase: TaskCommentPhase {manual.phase}
    public var selection: TaskCancelReasonSelection? {manual.selection.map {TaskCancelReasonSelection(source:$0)}}
    public var review: TaskCancelReasonReview? {manual.review.map {TaskCancelReasonReview(selection:TaskCancelReasonSelection(source:$0.selection),text:$0.text)}}
    public init() {}
    public mutating func retainOwner(business: Int?,epoch: Int?) {manual.retainOwner(business:business,epoch:epoch);problem=nil}
    public mutating func begin(_ next: TaskCommentRead?) {manual.begin(next);problem=nil}
    public mutating func receive(verified: Bool,status: String?,expected: TaskCommentRead) {
        guard manual.read==expected else {return};problem=nil
        manual.receive(verified:verified && ["open","in_progress"].contains(status ?? ""),expected:expected)
    }
    public mutating func pause() {manual.pause();problem=nil}
    @discardableResult public mutating func open(expected: TaskCommentRead) -> Bool {let opened=manual.open(expected:expected);if opened {problem=nil};return opened}
    public mutating func update(_ value: String,expected: TaskCancelReasonSelection) {
        guard manual.selection==expected.source,manual.available,manual.phase == .editing else {return}
        manual.update(value,expected:expected.source);problem=nil
    }
    @discardableResult public mutating func prepare(expected: TaskCancelReasonSelection) -> Bool {
        guard manual.selection==expected.source,manual.available,manual.phase == .editing else {return false}
        problem=TaskCancelReasonText.problem(manual.text);guard problem==nil else {return false}
        return manual.prepare(expected:expected.source)
    }
    public mutating func back(expected: TaskCancelReasonSelection) {guard manual.selection==expected.source else {return};manual.back(expected:expected.source);problem=nil}
    public mutating func close(expected: TaskCancelReasonSelection) {guard manual.selection==expected.source else {return};manual.close(expected:expected.source);problem=nil}
    public mutating func discard(expected: TaskCancelReasonSelection) {guard manual.selection==expected.source else {return};manual.discard(expected:expected.source);problem=nil}
}
