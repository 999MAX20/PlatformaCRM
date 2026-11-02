import Foundation
import CRMCore

func runTaskDraftChecks(directory: URL) throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    struct Fixture: Decodable {struct Row: Decodable {let title: String;let required: Bool;let too_long: Bool};let cases: [Row]}
    let f=try JSONDecoder().decode(Fixture.self,from:Data(contentsOf:directory.appendingPathComponent("task-draft-validation.json")))
    for row in f.cases {
        var v=TaskDraftValues();v.title=row.title
        try expect(v.issues.contains(where:{$0.problem == .required})==row.required,"Task required title differs from existing trim flow")
        try expect(v.issues.contains(where:{$0.problem == .titleLength})==row.too_long,"Task255 codepoint limit differs from model")
        try expect(v.title==row.title,"Validation rewrote raw title")
    }
    var v=TaskDraftValues();v.title="A";v.description=String(repeating:"Synthetic note\n",count:4000)
    try expect(v.priority=="normal" && v.issues.isEmpty,"Default or long optional description rule invented")
    for priority in TaskDraftValues.priorities {v.priority=priority;try expect(v.issues.isEmpty,"Source priority unavailable")}
    v.priority="invented";try expect(v.issues.contains(where:{$0.problem == .priority}),"Unknown priority accepted")
    let a=TaskDraftContext(business:101,epoch:1),b=TaskDraftContext(business:202,epoch:2)
    var s=TaskDraftSession();try expect(!s.open(expected:a),"Unbound Task draft opened")
    s.bind(a);_=s.open(expected:a);let old=s.selection!;s.update(.description,value:v.description,expected:old)
    try expect(!s.prepare(expected:old) && s.values.description==v.description && s.phase == .editing,"Local error lost input")
    s.update(.title,value:" Synthetic Task ",expected:old);_=s.prepare(expected:old);let review=s.review;s.update(.title,value:"late",expected:old)
    try expect(s.review==review && s.values.title==" Synthetic Task ","Review mutated through editing callback")
    s.back(expected:old);s.back(expected:old);try expect(s.selection==nil && s.values.title==" Synthetic Task ","Back discarded draft")
    _=s.open(expected:a);let current=s.selection!;s.discard(expected:old);s.close(expected:old);s.update(.title,value:"old event",expected:old)
    try expect(s.selection==current && s.values.title==" Synthetic Task ","Stale selection changed reopened Task form")
    s.bind(a);try expect(s.selection==current,"Same-context retry closed form")
    s.bind(b);try expect(s.values==TaskDraftValues() && s.selection==nil,"Business switch retained Task input")
    s.bind(TaskDraftContext(business:101,epoch:3));_=s.open(expected:s.context!);s.update(.title,value:"New",expected:s.selection!);s.discard(expected:s.selection!)
    try expect(s.values==TaskDraftValues() && s.phase == .closed,"Explicit clear failed")
    s.bind(TaskDraftContext(business:101,epoch:0));try expect(s.context==nil,"Invalid epoch accepted")
    return count
}
