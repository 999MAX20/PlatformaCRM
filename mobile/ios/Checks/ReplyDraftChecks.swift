import Foundation
import CRMCore

func runReplyDraftChecks(directory: URL) throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws { guard value else { throw CheckFailure(message:message) };count += 1 }
    struct Fixture: Decodable { struct Row: Decodable { let raw: String;let stripped: String };let cases: [Row] }
    let f=try JSONDecoder().decode(Fixture.self,from:Data(contentsOf:directory.appendingPathComponent("reply-draft-validation.json")))
    let a=ReplyDraftContext(business:101,conversation:901,epoch:1),other=ReplyDraftContext(business:101,conversation:902,epoch:1)
    for row in f.cases {
        try expect(ReplyDraftText.stripped(row.raw)==row.stripped,"Reply trim differs from source Python strip")
        var s=ReplyDraftSession();s.bind(a,available:true);_=s.open(expected:a);let selection=s.selection!
        s.update(row.raw,expected:selection);let ready=s.prepare(expected:selection)
        try expect(ready == !row.stripped.isEmpty && s.text==row.raw,"Validation lost raw input or accepted empty source text")
        try expect(ready ? s.review?.text==row.stripped : s.emptyError,"Preview did not match source text")
    }
    var s=ReplyDraftSession();try expect(!s.open(expected:a),"Unverified draft opened")
    s.bind(a,available:true);_=s.open(expected:a);let old=s.selection!;s.update("  First draft  ",expected:old)
    _=s.prepare(expected:old);let review=s.review;s.update("late edit",expected:old)
    try expect(s.review==review && s.text=="  First draft  ","Preview mutated after editing callback")
    s.back(expected:old);try expect(s.phase == .editing && s.review==nil,"Back did not return to editable raw input")
    s.back(expected:old);try expect(s.selection==nil && s.text=="  First draft  ","Back cleared draft")
    s.pause();try expect(s.text.isEmpty && !s.available,"Paused read retained visible input")
    s.bind(a,available:false);try expect(!s.open(expected:a),"Read in progress exposed cached draft")
    s.bind(a,available:true);_=s.open(expected:a);let fresh=s.selection!
    try expect(s.text=="  First draft  " && fresh != old,"Same verified thread lost buffer or reused UI token")
    s.update("old event",expected:old);s.discard(expected:old);try expect(s.selection==fresh && s.text=="  First draft  ","Old UI edited or cleared new route")
    s.bind(other,available:true);_=s.open(expected:other);let second=s.selection!;try expect(s.text.isEmpty,"Another dialogue inherited text")
    s.update("Second",expected:second);s.bind(a,available:true);try expect(s.text=="  First draft  ","Thread buffers were mixed")
    s.bind(a,available:false);try expect(!s.available && s.selection==nil && s.text.isEmpty,"Closed/unknown read exposed draft")
    s.bind(a,available:true);_=s.open(expected:a);s.discard(expected:s.selection!);s.pause();s.bind(a,available:true)
    try expect(s.text.isEmpty,"Explicit clear resurrected text")
    s.bind(other,available:true);try expect(s.text=="Second","Clearing one dialogue erased another")
    s.bind(ReplyDraftContext(business:101,conversation:902,epoch:2),available:true);try expect(s.text.isEmpty && s.selection==nil,"New session epoch retained draft")
    s.bind(a,available:true);_=s.open(expected:a);s.update("Private",expected:s.selection!);s.retainOwner(business:202,epoch:3)
    s.bind(a,available:true);try expect(s.text.isEmpty,"Business switch retained old buffer")
    s.bind(ReplyDraftContext(business:0,conversation:901,epoch:1),available:true);try expect(s.context==nil && !s.available,"Invalid context accepted")
    return count
}
