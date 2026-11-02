import Foundation

public enum TaskDraftDueMode:String,CaseIterable,Sendable,Hashable {case omit,setDate}
// Omission retains unsent raw but neither sends null nor asserts a server default date.
public struct TaskDraftDueDate:Equatable,Sendable {
    public var mode:TaskDraftDueMode = .omit
    public var raw=""
    public init() {}
    public var valid:Bool {mode == .omit || TaskSnoozeValue.parse(raw) != nil}
    public var selected:String? {mode == .setDate ? raw:nil}
    public func matches(_ returned:String?)->Bool {guard mode == .setDate else {return true};guard let wanted=TaskSnoozeValue.parse(raw),let returned,let actual=TaskSnoozeValue.parse(returned) else {return false};return wanted.microseconds==actual.microseconds}
    public static func ==(lhs:Self,rhs:Self)->Bool {lhs.mode==rhs.mode && lhs.raw.utf8.elementsEqual(rhs.raw.utf8)}
}
