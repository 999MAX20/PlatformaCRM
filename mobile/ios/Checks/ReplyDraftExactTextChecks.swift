import Foundation
import CRMCore

func runReplyDraftExactTextChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ v:Bool,_ message:String) throws {guard v else {throw CheckFailure(message:message)};count += 1}
    struct Row:Decodable {let raw:String;let text:String;let valid:Bool;let codepoints:Int}
    struct Pair:Decodable {let left:String;let right:String;let text_equal:Bool;let review_equal:Bool}
    struct Catalog:Decodable {let cases:[Row];let snapshot_cases:[Pair]}
    let f=try JSONDecoder().decode(Catalog.self,from:Data(contentsOf:directory.appendingPathComponent("reply-draft-exact-text.json"))),ctx=ReplyDraftContext(business:101,conversation:901,epoch:260)
    func session(_ raw:String)->ReplyDraftSession {var s=ReplyDraftSession();s.bind(ctx,available:true);_=s.open(expected:ctx);s.update(raw,expected:s.selection!);_=s.prepare(expected:s.selection!);return s}
    for row in f.cases {
        let raw=row.raw,text=row.text,valid=row.valid;var s=session(raw)
        try expect(s.text.utf8.elementsEqual(raw.utf8) && (s.phase == .review)==valid,"Reply raw modified/invalid review")
        guard valid else {try expect(s.emptyError && s.review==nil,"Empty reply prepared");continue}
        let selection=s.selection!,review=s.review!
        try expect(review.raw.utf8.elementsEqual(raw.utf8) && review.text.utf8.elementsEqual(text.utf8) && review.text.unicodeScalars.count==row.codepoints,"Reply review lost raw/normalized Unicode or imposed500 cap")
        s.update("late",expected:selection);try expect(s.review==review && s.text.utf8.elementsEqual(raw.utf8),"Review accepted late raw")
        s.back(expected:selection);try expect(s.phase == .editing && s.text.utf8.elementsEqual(raw.utf8),"Back normalized/truncated raw")
        s.pause();s.bind(ctx,available:true);_=s.open(expected:ctx);s.update("stale",expected:selection);try expect(s.text.utf8.elementsEqual(raw.utf8),"Same-owner pause/reopen lost full raw or accepted old callback")
        s.bind(ReplyDraftContext(business:101,conversation:901,epoch:261),available:true);try expect(s.text.isEmpty && s.review==nil && review.raw.utf8.elementsEqual(raw.utf8),"Epoch retained ordinary raw or rewrote immutable review")
    }
    for row in f.snapshot_cases {
        let a=session(row.left).review!,b=session(row.right).review!
        try expect(a.text.utf8.elementsEqual(b.text.utf8)==(row.text_equal),"Source Python normalization changed")
        try expect((a==b)==(row.review_equal),"Canonical equivalence erased different review raw/text")
    }
    return count
}
