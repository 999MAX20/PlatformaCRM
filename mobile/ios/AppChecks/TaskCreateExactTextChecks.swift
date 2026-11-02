import Foundation
import CRMCore

actor ExactTextCreatePort:SyntheticTaskCreatePort {
    nonisolated let grants=[SyntheticTaskCreateGrant(business:101,actor:9001,create:true)]
    private let outcome:SyntheticTaskCreateOutcome
    private var attempts:[TaskCreateAttempt]=[]
    init(_ outcome:SyntheticTaskCreateOutcome) {self.outcome=outcome}
    func execute(_ attempt:TaskCreateAttempt) async throws -> SyntheticTaskCreateOutcome {attempts.append(attempt);return outcome}
    func recorded()->[TaskCreateAttempt] {attempts}
}
@MainActor func checkTaskCreateExactText(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let f=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-create-exact-text.json"))) as! [String:Any],context=TaskDraftContext(business:101,epoch:230)
    for row in f["snapshot_cases"] as! [[String:Any]] {
        let lhs=row["left"] as! [String:Any],rhs=row["right"] as! [String:Any],field:TaskDraftField=(row["field"] as! String)=="title" ? .title:.description,m=TaskDraftViewModel();m.bind(context);m.open(expected:m.entryControl)
        m.update(.title,lhs["title"] as! String,input:m.inputControl);m.update(.description,lhs["description"] as! String,input:m.inputControl);m.askClear(expected:m.control);let question=m.clearConfirmation!
        m.update(field,rhs[field.rawValue] as! String,input:m.inputControl);m.confirmClear(question)
        try expect(m.clearConfirmation==nil && m.session.selection != nil,"Canonically-equivalent changed raw retained stale reset confirmation")
        try expect(m.session.values.title.utf8.elementsEqual((rhs["title"] as! String).utf8) && m.session.values.description.utf8.elementsEqual((rhs["description"] as! String).utf8),"Old clear discarded new exact input")
    }
    let port=ExactTextCreatePort(.rejectedWithoutWrite),m=TaskDraftViewModel(port:port);m.bind(context);m.open(expected:m.entryControl);m.update(.title," e\u{0301} ",input:m.inputControl);m.update(.description," s\u{0301} ",input:m.inputControl);m.prepare(expected:m.control);let old=m.session.review!;m.back(expected:m.returnControl)
    m.update(.title," é ",input:m.inputControl);m.update(.description," ś ",input:m.inputControl);m.prepare(expected:m.control);let current=m.session.review!;await m.submit(old,expected:m.control);let before=await port.recorded()
    try expect(before.isEmpty && m.submission==nil && m.session.review==current,"Old canonically equivalent review submitted under current UI visit")
    await m.submit(current,expected:m.control);let rejected=m.submission!,calls=await port.recorded()
    try expect(calls.count==1 && rejected.phase == .rejected && rejected.attempt.review==current,"Exact current review failed separate fake port")
    m.acknowledge(expected:m.control,record:rejected);try expect(m.session.phase == .editing && m.session.values==current.values && m.session.review==nil,"No-write lost exact input or reused review")
    let row=(f["cases"] as! [[String:Any]])[1],task=try JSONDecoder().decode(WorkTask.self,from:JSONSerialization.data(withJSONObject:row["response"]!)),bad=TaskDraftViewModel(port:ExactTextCreatePort(.response(status:201,task:task)))
    bad.bind(context);bad.open(expected:bad.entryControl);bad.update(.title," e\u{0301} ",input:bad.inputControl);bad.update(.description," s\u{0301} ",input:bad.inputControl);bad.update(.priority,"high",input:bad.inputControl);bad.prepare(expected:bad.control);let reviewed=bad.session.review!;await bad.submit(reviewed,expected:bad.control);let unknown=bad.submission!
    try expect(unknown.phase == .unknown && unknown.attempt.review==reviewed,"Canonically equivalent returned title was accepted or raw lost")
    bad.acknowledge(expected:bad.control,record:unknown);bad.bind(TaskDraftContext(business:101,epoch:231));try expect(bad.submissionBlocked && bad.submission==nil && bad.retainedAttemptCount==1,"Epoch/reread recovered create outcome")
    return count
}
