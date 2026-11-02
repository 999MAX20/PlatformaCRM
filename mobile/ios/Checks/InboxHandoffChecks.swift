import Foundation
import CRMCore

func runInboxHandoffChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ v:Bool,_ message:String) throws {guard v else {throw CheckFailure(message:message)};count += 1}
    let f=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("inbox-handoff-outcome.json"))) as! [String:Any],ctx=ReplyDraftContext(business:101,conversation:901,epoch:280),g=SyntheticHandoffGrant(business:101,conversation:901,actor:9001,update:true),auth=g.authorization(ctx)!
    func review(_ raw:String)->HandoffReview {var s=HandoffDraftSession();s.bind(ctx,available:true);_=s.open(ctx);s.update(raw,selection:s.selection!);_=s.prepare(s.selection!);return s.review!}
    for row in f["input_cases"] as! [[String:Any]] {
        var s=HandoffDraftSession();s.bind(ctx,available:true);_=s.open(ctx);let selection=s.selection!;let raw=exactFixtureString(row,"raw");s.update(raw,selection:selection);let valid=row["valid"] as! Bool
        try expect(s.prepare(selection)==valid && s.raw.utf8.elementsEqual(raw.utf8),"Handoff input validation lost exact raw")
        if valid {try expect(s.review?.value.reason.utf8.elementsEqual(SourceTextTrim.pythonStrip(exactFixtureString(row,"raw")).utf8)==true,"Reason blank/Python trim/long scalar semantics changed");s.back(selection);try expect(s.raw.utf8.elementsEqual(raw.utf8),"Review Back lost handoff reason")}
    }
    for row in f["review_pairs"] as! [[String:Any]] {try expect((review(exactFixtureString(row,"left"))==review(exactFixtureString(row,"right")))==(row["equal"] as! Bool),"Handoff exact raw/review normalized canonically")}
    for row in f["validation_cases"] as! [[String:Any]] {
        var ledger=HandoffLedger();let r=review(exactFixtureString(row,"raw")),a=ledger.begin(r,authorization:auth)!
        try expect(a.path=="/api/inbox/conversations/901/handoff/" && a.preparedHeaders.isEmpty && ledger.begin(r,authorization:auth)==nil,"Invented handoff key/route or duplicate pending attempt")
        let data=a.preparedBody()!,body=try JSONDecoder().decode([String:String].self,from:data);try expect(Set(body.keys)==["reason"] && body["reason"]?.utf8.elementsEqual(r.value.reason.utf8)==true,"Handoff body borrowed reply Business/version/key or changed reason")
        ledger.complete(a,outcome:.response(status:row["status"] as! Int,data:exactFixtureResponse(row)));let known=row["expected"] as! String=="confirmed",record=ledger.visible(auth)!
        try expect(record.phase == (known ? .confirmed:.unknown),"Handoff receipt: \(row["name"]!)")
        ledger.complete(a,outcome:.rejectedWithoutWrite);try expect(ledger.visible(auth)==record && record.attempt.review==r && ledger.acknowledge(auth)==known,"Terminal/unknown handoff overwritten/acknowledged")
        if !known {let c=ReplyDraftContext(business:101,conversation:901,epoch:281);try expect(ledger.blocked(c) && ledger.visible(g.authorization(c))==nil,"Reread/epoch recovered unknown handoff")}
    }
    try expect(SyntheticHandoffGrant(business:101,conversation:901,actor:9001,update:false).authorization(ctx)==nil,"GET flag became UPDATE")
    try expect(SyntheticHandoffGrant(business:202,conversation:901,actor:9001,update:true).authorization(ctx)==nil && SyntheticHandoffGrant(business:101,conversation:901,actor:0,update:true).authorization(ctx)==nil,"Foreign Business/actor became action grant")
    var session=HandoffDraftSession();session.bind(ctx,available:true);_=session.open(ctx);session.update(" Own raw ",selection:session.selection!);session.pause();let other=ReplyDraftContext(business:101,conversation:902,epoch:280);session.bind(other,available:true);_=session.open(other);session.update(" Other raw ",selection:session.selection!);session.pause();session.bind(ctx,available:true);_=session.open(ctx);try expect(session.raw==" Own raw ","Same-owner per-conversation handoff buffer lost");session.bind(ReplyDraftContext(business:101,conversation:901,epoch:281),available:true);try expect(session.raw.isEmpty && session.selection==nil,"New epoch exposed old reason")
    return count
}
