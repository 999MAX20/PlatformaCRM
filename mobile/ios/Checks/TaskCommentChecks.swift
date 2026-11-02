import Foundation
import CRMCore

func runTaskCommentChecks(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    struct Reference: Decodable {struct Row: Decodable {let raw: String;let preview: String;let valid: Bool};let cases: [Row]}
    let reference=try JSONDecoder().decode(Reference.self,from:Data(contentsOf:directory.appendingPathComponent("task-comment-validation.json")))
    let a=TaskCommentContext(business:101,task:1101,epoch:1),b=TaskCommentContext(business:101,task:1102,epoch:1)
    let first=TaskCommentRead(context:a,revision:1)
    var s=TaskCommentSession();try expect(!s.open(expected:first),"Unbound manual comment opened")
    s.begin(first);try expect(s.text.isEmpty && !s.available && !s.open(expected:first),"Pending detail exposed editable comment")
    s.receive(verified:true,expected:first);try expect(s.open(expected:first) && s.text.isEmpty,"New comment copied read history/description")
    let selection=s.selection!
    for row in reference.cases {
        s.update(row.raw,expected:selection)
        try expect(TaskCommentText.preview(row.raw)==row.preview,"Web JS/Python comment normalization differed from source-executed reference")
        try expect(s.prepare(expected:selection)==row.valid && s.text==row.raw,"Validation changed raw comment or invented500-character input cap")
        if row.valid {try expect(s.review?.text==row.preview,"Review was not source-normalized preview");s.back(expected:selection)}
    }
    s.update("  Manual task A\nsecond line  ",expected:selection);_=s.prepare(expected:selection);let review=s.review
    s.update("late editor",expected:selection);try expect(s.review==review && s.text=="  Manual task A\nsecond line  ","Review accepted mutable input")
    s.back(expected:selection);s.back(expected:selection);try expect(s.selection==nil && s.text=="  Manual task A\nsecond line  ","Back lost raw own comment")
    _=s.open(expected:first);let reopened=s.selection!;s.discard(expected:selection);s.update("stale",expected:selection)
    try expect(s.selection==reopened && s.text.hasPrefix("  Manual"),"Old sheet event replaced reopened comment")
    s.pause();try expect(s.text.isEmpty && s.read==nil && s.review==nil && !s.available,"Parent Back exposed private text")
    let fresh=TaskCommentRead(context:a,revision:2);s.begin(fresh);s.receive(verified:true,expected:first)
    try expect(!s.available && s.text.isEmpty,"Late previous read reenabled comment")
    s.receive(verified:true,expected:fresh);try expect(s.text=="  Manual task A\nsecond line  ","Fresh verified return lost own draft")
    let other=TaskCommentRead(context:b,revision:3);s.begin(other);s.receive(verified:true,expected:other)
    try expect(s.text.isEmpty,"Task B inherited Task A comment")
    _=s.open(expected:other);s.update("Task B",expected:s.selection!);s.begin(fresh);s.receive(verified:true,expected:fresh)
    try expect(s.text=="  Manual task A\nsecond line  ","Task buffers mixed")
    s.begin(fresh);s.receive(verified:false,expected:fresh);try expect(s.text.isEmpty && !s.available && s.review==nil,"Mismatched fixture read retained visible text")
    s.begin(fresh);s.receive(verified:true,expected:fresh);try expect(s.text.hasPrefix("  Manual task A"),"Mismatch erased own private manual input")
    _=s.open(expected:fresh);s.discard(expected:s.selection!);try expect(s.text.isEmpty && s.selection==nil,"Explicit clear failed")
    _=s.open(expected:fresh);s.update("Do not cross epoch",expected:s.selection!)
    s.retainOwner(business:101,epoch:1);try expect(s.text.isEmpty && !s.available,"List reload exposed private input")
    s.begin(fresh);s.receive(verified:true,expected:fresh);try expect(s.text=="Do not cross epoch","Same owner list reload erased input")
    s.retainOwner(business:101,epoch:2);let epoch=TaskCommentRead(context:TaskCommentContext(business:101,task:1101,epoch:2),revision:4);s.begin(epoch);s.receive(verified:true,expected:epoch)
    try expect(s.text.isEmpty,"New epoch inherited manual input")
    _=s.open(expected:epoch);s.update("Do not cross Business",expected:s.selection!)
    let business=TaskCommentRead(context:TaskCommentContext(business:202,task:1101,epoch:2),revision:5);s.begin(business);s.receive(verified:true,expected:business)
    try expect(s.text.isEmpty,"Business switch inherited manual text")
    s.begin(TaskCommentRead(context:a,revision:0));try expect(s.read==nil && !s.available,"Invalid read revision enabled composer")
    let provider=FixtureTaskCommentDraftSource(directory:directory)
    let data=try Data(contentsOf:directory.appendingPathComponent("task-101-1101.json")),detail=try JSONDecoder().decode(TaskDetails.self,from:data)
    try expect(await provider.matchesFixture(detail),"Known independent fixture did not match")
    var json=try JSONSerialization.jsonObject(with:data) as! [String:Any];var task=json["task"] as! [String:Any];task["title"]=NSNull();json["task"]=task
    let unknown=try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:json))
    try expect(!(await provider.matchesFixture(unknown)),"Opaque/changed profile acquired fixture capability")
    return count
}
