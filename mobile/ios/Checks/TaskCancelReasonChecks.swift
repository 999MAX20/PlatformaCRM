import Foundation
import CRMCore

func runTaskCancelReasonChecks(directory: URL) throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    struct Reference: Decodable {struct Row: Decodable {let raw: String;let preview: String;let problem: String?};let cases: [Row]}
    let reference=try JSONDecoder().decode(Reference.self,from:Data(contentsOf:directory.appendingPathComponent("task-cancel-reason-validation.json")))
    let read=TaskCommentRead(context:TaskCommentContext(business:101,task:1101,epoch:1),revision:1)
    var s=TaskCancelReasonSession();try expect(!s.open(expected:read),"Unbound reason opened")
    s.begin(read);s.receive(verified:true,status:"open",expected:read);_=s.open(expected:read);let first=s.selection!
    for row in reference.cases {
        s.update(row.raw,expected:first)
        try expect(TaskCancelReasonText.preview(row.raw)==row.preview,"Reason trim chain differs from executed JS/Python source")
        try expect(TaskCancelReasonText.problem(row.raw)?.rawValue==row.problem,"Reason min/max/characters changed source semantics")
        try expect(s.prepare(expected:first)==(row.problem==nil) && s.text==row.raw,"Validation rewrote raw reason or used UTF16 as Python length")
        if row.problem==nil {try expect(s.review?.text==row.preview,"Unsent preview changed normalized reason");s.back(expected:first)}
    }
    s.update("  Manual reason\nsecond line  ",expected:first);_=s.prepare(expected:first);let review=s.review
    s.update("Late review edit",expected:first);try expect(s.review==review && s.text=="  Manual reason\nsecond line  ","Review accepted editable callback")
    s.back(expected:first);s.back(expected:first);try expect(s.selection==nil && s.text.hasPrefix("  Manual"),"Back discarded raw reason")
    _=s.open(expected:read);let current=s.selection!;s.discard(expected:first);s.update("stale",expected:first)
    try expect(s.selection==current && s.text.hasPrefix("  Manual"),"Old modal callback replaced reopened reason")
    s.pause();try expect(!s.available && s.text.isEmpty && s.read==nil,"Parent Back exposed reason buffer")
    let fresh=TaskCommentRead(context:read.context,revision:2);s.begin(fresh);s.receive(verified:true,status:"done",expected:fresh)
    try expect(!s.available && s.text.isEmpty && !s.open(expected:fresh),"Closed Task enabled cancellation-reason preparation")
    s.begin(fresh);s.receive(verified:true,status:"in_progress",expected:fresh)
    try expect(s.available && s.text.hasPrefix("  Manual"),"Verified own active return lost manual reason")
    for status in ["cancelled","future_status","",nil] {
        s.begin(fresh);s.receive(verified:true,status:status,expected:fresh)
        try expect(!s.available && s.text.isEmpty,"Unknown/terminal status acquired local eligibility")
    }
    s.begin(fresh);s.receive(verified:false,status:"open",expected:fresh);try expect(!s.available,"Opaque source enabled form")
    s.begin(fresh);s.receive(verified:true,status:"open",expected:read);try expect(!s.available,"Old read generation enabled form")
    s.receive(verified:true,status:"open",expected:fresh);_=s.open(expected:fresh);s.discard(expected:s.selection!)
    try expect(s.text.isEmpty && s.selection==nil,"Explicit clear failed")
    _=s.open(expected:fresh);s.update("Own Task A reason",expected:s.selection!)
    let other=TaskCommentRead(context:TaskCommentContext(business:101,task:1102,epoch:1),revision:3);s.begin(other);s.receive(verified:true,status:"open",expected:other)
    try expect(s.text.isEmpty,"Another Task inherited reason")
    s.begin(fresh);s.receive(verified:true,status:"open",expected:fresh);try expect(s.text=="Own Task A reason","Per-Task buffers mixed")
    var comment=TaskCommentSession();comment.begin(fresh);comment.receive(verified:true,expected:fresh);_=comment.open(expected:fresh);comment.update("Different comment input",expected:comment.selection!)
    try expect(s.text=="Own Task A reason" && s.text != comment.text,"Reason reused comment instance/input instead of only its engine")
    s.retainOwner(business:202,epoch:2);s.begin(fresh);s.receive(verified:true,status:"open",expected:fresh)
    try expect(s.text.isEmpty,"Business/epoch return restored prior owner reason")
    return count
}
