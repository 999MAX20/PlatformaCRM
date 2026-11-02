import Foundation

// Local manual input only: no server Client, CREATE grant, wire command or storage.
public struct ClientDraftContext: Equatable, Sendable {
    public let business: Int; public let epoch: Int
    public init(business: Int, epoch: Int) { self.business = business; self.epoch = epoch }
    public var valid: Bool { business > 0 && epoch > 0 }
}
public struct ClientDraftSelection: Equatable, Sendable {
    public let context: ClientDraftContext; public let generation: Int
}
public enum ClientDraftField: String, CaseIterable, Hashable, Sendable { case fullName, phone, email, source, notes }
public enum ClientDraftProblem: String, Sendable { case name, nameLength, phoneLength, email, source, emailLength, characters }
public struct ClientDraftIssue: Equatable, Sendable { public let field: ClientDraftField; public let problem: ClientDraftProblem }
public struct ClientDraftValues: Equatable, Sendable {
    public var fullName = "", phone = "", email = "", source = "manual", notes = ""
    public init() {}
    public static let sources = ["manual", "website", "telegram", "whatsapp", "instagram", "parser", "other"]
    // Existing ClientForm uses zod3.25.76 .email().or(literal("")); no new
    // dependency. Pattern verified at the pinned official source types.ts:581.
    private static let emailPattern = #"^(?!\.)(?!.*\.\.)([A-Z0-9_'+\-\.]*)[A-Z0-9_+-]@([A-Z0-9][A-Z0-9\-]*\.)+[A-Z]{2,}$"#
    private static func webEmailAccepted(_ value: String) -> Bool {
        value.isEmpty || (value.unicodeScalars.allSatisfy {$0.value<128} && value.range(of:emailPattern,options:[.regularExpression,.caseInsensitive])==(value.startIndex..<value.endIndex))
    }
    public var preview: ClientDraftPreview {
        ClientDraftPreview(fullName:SourceTextTrim.pythonStrip(fullName),phone:SourceTextTrim.pythonStrip(phone),email:SourceTextTrim.pythonStrip(email),source:source,notes:SourceTextTrim.pythonStrip(notes))
    }
    // ClientForm's raw Zod stage is intentionally separate from server string rules.
    public var webIssues: [ClientDraftIssue] {
        var result:[ClientDraftIssue]=[]
        if fullName.utf16.count<2 {result.append(ClientDraftIssue(field:.fullName,problem:.name))}
        if !Self.webEmailAccepted(email) {result.append(ClientDraftIssue(field:.email,problem:.email))}
        return result
    }
    public var sourceIssues: [ClientDraftIssue] {
        let value=preview;var result:[ClientDraftIssue]=[]
        if value.fullName.isEmpty {result.append(ClientDraftIssue(field:.fullName,problem:.name))}
        if value.fullName.unicodeScalars.count>255 {result.append(ClientDraftIssue(field:.fullName,problem:.nameLength))}
        if value.phone.unicodeScalars.count>32 {result.append(ClientDraftIssue(field:.phone,problem:.phoneLength))}
        if value.email.unicodeScalars.count>254 {result.append(ClientDraftIssue(field:.email,problem:.emailLength))}
        // Only the already accepted Zod ASCII subset; not a general EmailValidator/IDNA clone.
        if !email.isEmpty,Self.webEmailAccepted(email),let domain=value.email.split(separator:"@").last {
            if domain.split(separator:".",omittingEmptySubsequences:false).contains(where:{$0.utf8.count>63 || $0.last=="-"}) {result.append(ClientDraftIssue(field:.email,problem:.email))}
        }
        for (field,text) in [(ClientDraftField.fullName,value.fullName),(.phone,value.phone),(.email,value.email),(.notes,value.notes)] {
            if text.unicodeScalars.contains(where:{$0.value==0}) {result.append(ClientDraftIssue(field:field,problem:.characters))}
        }
        if !Self.sources.contains(source) {result.append(ClientDraftIssue(field:.source,problem:.source))}
        return result
    }
    public var issues: [ClientDraftIssue] {
        (webIssues+sourceIssues).reduce(into:[ClientDraftIssue]()) {result,issue in if !result.contains(issue) {result.append(issue)}}
    }
}
public enum ClientDraftPhase: Equatable, Sendable { case closed, editing, review }
public struct ClientDraftPreview: Equatable,Sendable {public let fullName:String;public let phone:String;public let email:String;public let source:String;public let notes:String}
public struct ClientDraftReview: Equatable, Sendable {public let selection:ClientDraftSelection;public let values:ClientDraftValues;public let preview:ClientDraftPreview}
public struct ClientDraftSession: Sendable {
    public private(set) var context: ClientDraftContext?
    public private(set) var selection: ClientDraftSelection?
    public private(set) var values = ClientDraftValues()
    public private(set) var issues: [ClientDraftIssue] = []
    public private(set) var review: ClientDraftReview?
    public private(set) var phase: ClientDraftPhase = .closed
    private var generation = 0
    public init() {}
    public mutating func bind(_ next: ClientDraftContext?) {
        let valid = next?.valid == true ? next : nil
        guard context != valid else { return }
        generation += 1; context = valid; selection = nil; values = ClientDraftValues(); issues = []; review = nil; phase = .closed
    }
    @discardableResult public mutating func open(expected: ClientDraftContext) -> Bool {
        guard expected.valid, context == expected else { return false }
        generation += 1; selection = ClientDraftSelection(context:expected,generation:generation); phase = .editing; issues = []; review = nil; return true
    }
    public mutating func update(_ field: ClientDraftField, value: String, expected: ClientDraftSelection) {
        guard selection == expected, phase == .editing else { return }
        switch field { case .fullName: values.fullName = value; case .phone: values.phone = value; case .email: values.email = value; case .source: values.source = value; case .notes: values.notes = value }
        issues.removeAll { $0.field == field }
    }
    @discardableResult public mutating func prepare(expected: ClientDraftSelection) -> Bool {
        guard selection == expected, phase == .editing else { return false }
        issues = values.issues
        guard issues.isEmpty else { return false }
        review = ClientDraftReview(selection:expected,values:values,preview:values.preview); phase = .review; return true
    }
    public mutating func back(expected: ClientDraftSelection) {
        guard selection == expected else { return }
        if phase == .review { review = nil; phase = .editing } else { close(expected:expected) }
    }
    public mutating func close(expected: ClientDraftSelection) {
        guard selection == expected else { return }
        generation += 1; selection = nil; review = nil; phase = .closed
    }
    public mutating func discard(expected: ClientDraftSelection) {
        guard selection == expected else { return }
        close(expected:expected); values = ClientDraftValues(); issues = []
    }
}
