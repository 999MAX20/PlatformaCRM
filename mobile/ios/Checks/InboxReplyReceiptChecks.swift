import Foundation
import CRMCore

func runInboxReplyReceiptChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ v:Bool,_ message:String) throws {guard v else {throw CheckFailure(message:message)};count += 1}
    let f=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("inbox-reply-outcome.json"))) as! [String:Any],ctx=ReplyDraftContext(business:101,conversation:901,epoch:270),port=FixtureInboxReplyPort(directory:directory),grant=port.grants.first(where:{$0.business==101 && $0.conversation==901})!,auth=grant.authorization(for:ctx)!
    func review(_ raw:String,context:ReplyDraftContext?=nil)->ReplyDraftReview {let context=context ?? ctx;var s=ReplyDraftSession();s.bind(context,available:true);_=s.open(expected:context);s.update(raw,expected:s.selection!);_=s.prepare(expected:s.selection!);return s.review!}
    for row in f["validation_cases"] as! [[String:Any]] {
        let r=review(exactFixtureString(row,"raw"));var ledger=InboxReplyLedger();let a=ledger.begin(r,authorization:auth)!
        try expect(ledger.begin(r,authorization:auth)==nil,"Pending reply duplicated")
        try expect(a.preparedHeaders==["Idempotency-Key":grant.keys[0]] && a.path=="/api/mobile/v1/inbox/901/reply/","Existing explicit header/path changed or localID used as key")
        struct Body:Decodable {let business:Int;let text:String};let data=a.preparedBody()!,body=try JSONSerialization.jsonObject(with:data) as! [String:Any],value=try JSONDecoder().decode(Body.self,from:data);try expect(Set(body.keys)==["business","text"] && value.business==101 && value.text.utf8.elementsEqual(r.text.utf8),"Reply body exact fields: \(row["name"]!)")
        ledger.complete(a,outcome:.response(status:row["status"] as! Int,data:exactFixtureResponse(row)));let record=ledger.visible(auth)!,yes=row["expected"] as! String=="confirmed"
        try expect(record.phase == (yes ? .confirmed:.unknown),"Reply receipt: \(row["name"]!)")
        try expect(record.attempt.review==r && record.attempt.key.utf8.elementsEqual(a.key.utf8),"Reply lost full raw/review/key")
        if yes {try expect(record.receipt?.matches(a)==true,"Receipt lost captured request association")}
        ledger.complete(a,outcome:.rejectedWithoutWrite);try expect(ledger.visible(auth)==record && ledger.acknowledge(auth)==yes,"Terminal overwritten or unknown acknowledged")
        if !yes {let newer=ReplyDraftContext(business:101,conversation:901,epoch:271);try expect(ledger.blocked(newer) && ledger.visible(grant.authorization(for:newer))==nil,"Reread/epoch proved unknown reply outcome")}
    }
    for bad in [SyntheticInboxReplyGrant(business:101,conversation:901,actor:9001,update:false,keys:["k"]),SyntheticInboxReplyGrant(business:101,conversation:901,actor:0,update:true,keys:["k"]),SyntheticInboxReplyGrant(business:202,conversation:901,actor:9001,update:true,keys:["k"]),SyntheticInboxReplyGrant(business:101,conversation:901,actor:9001,update:true,keys:[]),SyntheticInboxReplyGrant(business:101,conversation:901,actor:9001,update:true,keys:[" "]),SyntheticInboxReplyGrant(business:101,conversation:901,actor:9001,update:true,keys:["same","same"])] {try expect(bad.authorization(for:ctx)==nil,"GET/malformed fake catalogue became UPDATE/key context")}
    let keys=SyntheticInboxReplyGrant(business:101,conversation:901,actor:9001,update:true,keys:["e\u{0301}","é"]),a=keys.authorization(for:ctx)!;var ledger=InboxReplyLedger();let first=ledger.begin(review("Reply"),authorization:a)!;ledger.complete(first,outcome:.rejectedWithoutWrite);_=ledger.acknowledge(a);let second=ledger.begin(review("Reply"),authorization:a)!
    try expect(first.key.utf8.elementsEqual(keys.keys[0].utf8) && second.key.utf8.elementsEqual(keys.keys[1].utf8) && !first.key.utf8.elementsEqual(second.key.utf8),"Opaque key namespace normalized/reused exact key")
    ledger.complete(second,outcome:.rejectedWithoutWrite);_=ledger.acknowledge(a);try expect(!ledger.canBegin(a) && ledger.begin(review("Reply"),authorization:a)==nil,"Exhausted test catalogue generated a key/timer")
    let foreign=ReplyDraftContext(business:101,conversation:902,epoch:270),cross=SyntheticInboxReplyGrant(business:101,conversation:902,actor:9001,update:true,keys:[keys.keys[0]]).authorization(for:foreign)!
    try expect(!ledger.canBegin(cross),"Same Business/actor/endpoint key reused for another path")
    let rawRows=(try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("quick-reply-raw-unicode-cases.json"))) as! [String:Any])["cases"] as! [[String:Any]]
    for row in rawRows {
        var frozen=InboxReplyLedger();let r=review(row["inserted"] as! String),attempt=frozen.begin(r,authorization:auth)!,bytes=attempt.preparedBody()!,headers=attempt.preparedHeaders
        let body=try JSONSerialization.jsonObject(with:bytes) as! [String:Any]
        try expect(Set(body.keys)==["business","text"] && body["business"] as? Int==101 && (body["text"] as! String).utf8.elementsEqual(r.text.utf8),"Frozen reply body changed source fields/text")
        try expect((0..<64).allSatisfy {_ in attempt.preparedBody()==bytes},"Repeated body reads reserialized one immutable attempt")
        var external=bytes;external.append(0);try expect(attempt.preparedBody()==bytes && external != bytes,"Returned mutable Data copy altered retained attempt body")
        frozen.complete(attempt,outcome:.unknown);let record=frozen.visible(auth)!
        try expect(record.phase == .unknown && record.attempt==attempt && record.attempt.preparedBody()==bytes && record.attempt.preparedHeaders==headers && record.attempt.review==r,"Unknown did not retain exact attempt/body/header/review")
        try expect(!frozen.acknowledge(auth) && frozen.begin(r,authorization:auth)==nil && frozen.blocked(ReplyDraftContext(business:101,conversation:901,epoch:271)),"Frozen body allowed unknown replay/ack/epoch rekey")
    }
    return count
}
