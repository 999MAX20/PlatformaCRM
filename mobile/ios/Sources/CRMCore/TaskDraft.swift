import Foundation

// Unsent manual Task input, not the Appointment's built-in follow-up or a command.
public struct TaskDraftContext: Equatable, Sendable {
    public let business: Int;public let epoch: Int
    public init(business: Int,epoch: Int) { self.business=business;self.epoch=epoch }
    public var valid: Bool { business>0 && epoch>0 }
}
public struct TaskDraftSelection: Equatable, Sendable { public let context: TaskDraftContext;public let generation: Int }
public enum TaskDraftField: String, CaseIterable, Hashable, Sendable { case title, description, priority, dueAt, reminderAt }
public enum TaskDraftProblem: String, Sendable { case required, titleLength, priority, characters, date }
public struct TaskDraftIssue: Equatable, Sendable { public let field: TaskDraftField;public let problem: TaskDraftProblem }
public struct TaskDraftValues: Equatable, Sendable {
    public var title="",description="",priority="normal"
    public var client:TaskDraftClientChoice?
    public var appointment:TaskDraftAppointmentChoice?
    public var parentTask:TaskDraftParentChoice?
    public var dueDate=TaskDraftDueDate()
    // Shared set/omit semantics, independent raw and mode; never copied from dueDate.
    public var reminderDate=TaskDraftDueDate()
    public init() {}
    public static let priorities=["low","normal","high","urgent"]
    // Raw spelling is part of the immutable local input, not Unicode canonical identity.
    public static func ==(lhs:Self,rhs:Self)->Bool {
        lhs.title.utf8.elementsEqual(rhs.title.utf8) && lhs.description.utf8.elementsEqual(rhs.description.utf8) && lhs.priority.utf8.elementsEqual(rhs.priority.utf8) && lhs.dueDate==rhs.dueDate && lhs.reminderDate==rhs.reminderDate && lhs.client==rhs.client && lhs.appointment==rhs.appointment && lhs.parentTask==rhs.parentTask
    }
    public var preview: TaskDraftPreview {
        TaskDraftPreview(title:SourceTextTrim.pythonStrip(SourceTextTrim.javascriptTrim(title)),description:SourceTextTrim.pythonStrip(description),priority:priority,dueAt:dueDate.selected,reminderAt:reminderDate.selected,clientID:client?.id,appointmentID:appointment?.id,parentTaskID:parentTask?.id)
    }
    public func validClient(for business:Int)->Bool {client?.valid(for:business) ?? true}
    public func validAppointment(for business:Int)->Bool {appointment?.valid(for:business) ?? true}
    public func validParent(for business:Int)->Bool {parentTask?.valid(for:business) ?? true}
    public var issues: [TaskDraftIssue] {
        let value=preview;var result: [TaskDraftIssue]=[]
        if value.title.isEmpty {result.append(TaskDraftIssue(field:.title,problem:.required))}
        if value.title.unicodeScalars.count>255 {result.append(TaskDraftIssue(field:.title,problem:.titleLength))}
        for (field,text) in [(TaskDraftField.title,value.title),(.description,value.description)] {
            if text.unicodeScalars.contains(where:{$0.value==0}) {result.append(TaskDraftIssue(field:field,problem:.characters))}
        }
        if !Self.priorities.contains(priority) {result.append(TaskDraftIssue(field:.priority,problem:.priority))}
        if !dueDate.valid {result.append(TaskDraftIssue(field:.dueAt,problem:.date))}
        if !reminderDate.valid {result.append(TaskDraftIssue(field:.reminderAt,problem:.date))}
        return result
    }
}
public enum TaskDraftPhase: Equatable, Sendable { case closed, editing, review }
// Existing selected Task create fields; text normalization and independent date intents.
public struct TaskDraftPreview: Equatable,Sendable {
    public let title: String;public let description: String;public let priority: String
    public let dueAt:String?;public let reminderAt:String?;public let clientID:Int?;public let appointmentID:Int?;public let parentTaskID:Int?
    init(title:String,description:String,priority:String,dueAt:String?=nil,reminderAt:String?=nil,clientID:Int?=nil,appointmentID:Int?=nil,parentTaskID:Int?=nil) {self.title=title;self.description=description;self.priority=priority;self.dueAt=dueAt;self.reminderAt=reminderAt;self.clientID=clientID;self.appointmentID=appointmentID;self.parentTaskID=parentTaskID}
    public static func ==(lhs:Self,rhs:Self)->Bool {
        lhs.title.utf8.elementsEqual(rhs.title.utf8) && lhs.description.utf8.elementsEqual(rhs.description.utf8) && lhs.priority.utf8.elementsEqual(rhs.priority.utf8) && lhs.dueAt.map({Data($0.utf8)})==rhs.dueAt.map({Data($0.utf8)}) && lhs.reminderAt.map({Data($0.utf8)})==rhs.reminderAt.map({Data($0.utf8)}) && lhs.clientID==rhs.clientID && lhs.appointmentID==rhs.appointmentID && lhs.parentTaskID==rhs.parentTaskID
    }
}
public struct TaskDraftReview: Equatable, Sendable {public let selection: TaskDraftSelection;public let values: TaskDraftValues;public let preview: TaskDraftPreview}
public struct TaskDraftSession: Sendable {
    public private(set) var context: TaskDraftContext?
    public private(set) var selection: TaskDraftSelection?
    public private(set) var values = TaskDraftValues()
    public private(set) var issues: [TaskDraftIssue] = []
    public private(set) var review: TaskDraftReview?
    public private(set) var phase: TaskDraftPhase = .closed
    private var generation = 0
    public init() {}
    public mutating func bind(_ next: TaskDraftContext?) {
        let valid = next?.valid == true ? next : nil
        guard context != valid else { return }
        generation += 1; context = valid; selection = nil; values = TaskDraftValues(); issues = []; review = nil; phase = .closed
    }
    @discardableResult public mutating func open(expected: TaskDraftContext) -> Bool {
        guard expected.valid, context == expected else { return false }
        generation += 1; selection = TaskDraftSelection(context:expected,generation:generation); phase = .editing; issues = []; review = nil; return true
    }
    public mutating func update(_ field: TaskDraftField, value: String, expected: TaskDraftSelection) {
        guard selection == expected, phase == .editing else { return }
        switch field { case .title: values.title = value; case .description: values.description = value; case .priority: values.priority = value; case .dueAt: if values.dueDate.mode == .setDate {values.dueDate.raw=value};case .reminderAt: if values.reminderDate.mode == .setDate {values.reminderDate.raw=value} }
        issues.removeAll { $0.field == field }
    }
    public mutating func chooseDue(_ mode:TaskDraftDueMode,expected:TaskDraftSelection) {
        guard selection==expected,phase == .editing else {return};values.dueDate.mode=mode;issues.removeAll {$0.field == .dueAt}
    }
    public mutating func chooseReminder(_ mode:TaskDraftDueMode,expected:TaskDraftSelection) {
        guard selection==expected,phase == .editing else {return};values.reminderDate.mode=mode;issues.removeAll {$0.field == .reminderAt}
    }
    public mutating func chooseClient(_ choice:TaskDraftClientChoice?,expected:TaskDraftSelection) {
        guard selection==expected,phase == .editing,choice?.valid(for:expected.context.business) ?? true else {return}
        values.client=choice
    }
    public mutating func chooseAppointment(_ choice:TaskDraftAppointmentChoice?,expected:TaskDraftSelection) {
        guard selection==expected,phase == .editing,choice?.valid(for:expected.context.business) ?? true else {return}
        values.appointment=choice
    }
    public mutating func chooseParent(_ choice:TaskDraftParentChoice?,expected:TaskDraftSelection) {
        guard selection==expected,phase == .editing,choice?.valid(for:expected.context.business) ?? true else {return}
        values.parentTask=choice
    }
    @discardableResult public mutating func prepare(expected: TaskDraftSelection) -> Bool {
        guard selection == expected, phase == .editing else { return false }
        issues = values.issues
        guard issues.isEmpty,values.validClient(for:expected.context.business),values.validAppointment(for:expected.context.business),values.validParent(for:expected.context.business) else { return false }
        review = TaskDraftReview(selection:expected,values:values,preview:values.preview); phase = .review; return true
    }
    public mutating func back(expected: TaskDraftSelection) {
        guard selection == expected else { return }
        if phase == .review { review = nil; phase = .editing } else { close(expected:expected) }
    }
    public mutating func close(expected: TaskDraftSelection) {
        guard selection == expected else { return }
        generation += 1; selection = nil; review = nil; phase = .closed
    }
    public mutating func discard(expected: TaskDraftSelection) {
        guard selection == expected else { return }
        close(expected:expected); values = TaskDraftValues(); issues = []
    }
}
