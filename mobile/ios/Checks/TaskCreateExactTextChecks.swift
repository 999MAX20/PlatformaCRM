import Foundation
import CRMCore

func runTaskCreateExactTextChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    struct Values:Decodable {let title:String;let description:String;let priority:String}
    struct Row:Decodable {let name:String;let raw:Values;let preview:Values;let response:WorkTask;let status:Int;let expected:String}
    struct Pair:Decodable {let left:Values;let right:Values;let raw_equal:Bool;let preview_equal:Bool}
    struct Catalog:Decodable {let cases:[Row];let snapshot_cases:[Pair]}
    let f=try JSONDecoder().decode(Catalog.self,from:Data(contentsOf:directory.appendingPathComponent("task-create-exact-text.json"))),context=TaskDraftContext(business:101,epoch:230),grant=SyntheticTaskCreateGrant(business:101,actor:9001,create:true),auth=grant.authorization(for:context)!
    func session(_ raw:Values)->TaskDraftSession {var s=TaskDraftSession();s.bind(context);_=s.open(expected:context);let c=s.selection!;s.update(.title,value:raw.title,expected:c);s.update(.description,value:raw.description,expected:c);s.update(.priority,value:raw.priority,expected:c);_=s.prepare(expected:c);return s}
    for row in f.cases {
        let s=session(row.raw),review=s.review!,expected=row.expected=="confirmed",v=row.preview
        try expect(review.preview.title.utf8.elementsEqual(v.title.utf8) && review.preview.description.utf8.elementsEqual(v.description.utf8),"Create preview changed text representation: \(row.name)")
        var ledger=TaskCreateAttemptLedger();let a=ledger.begin(review:review,authorization:auth)!
        ledger.complete(a,outcome:.response(status:row.status,task:row.response));let record=ledger.visible(auth)!
        try expect(record.phase == (expected ? .confirmed:.unknown),"Create exact text: \(row.name)")
        try expect(record.attempt.review==review,"Create raw/review snapshot changed")
        ledger.complete(a,outcome:.rejectedWithoutWrite);try expect(ledger.visible(auth)==record && ledger.acknowledge(auth)==expected,"Terminal overwritten/unknown acknowledged")
        if !expected {let newer=TaskDraftContext(business:101,epoch:231);try expect(ledger.blocked(newer) && ledger.visible(grant.authorization(for:newer))==nil,"New epoch recovered create text outcome")}
    }
    for row in f.snapshot_cases {
        let lhs=session(row.left),rhs=session(row.right)
        try expect((lhs.values==rhs.values)==row.raw_equal,"Create raw equality discarded exact input")
        try expect((lhs.values.preview==rhs.values.preview)==row.preview_equal,"Create review-preview consistency used canonical equivalence")
    }
    return count
}
