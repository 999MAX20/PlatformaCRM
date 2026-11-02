import Foundation
import CRMCore

func exactFixtureString(_ row:[String:Any],_ key:String)->String {try! JSONDecoder().decode(String.self,from:Data((row[key+"_json"] as! String).utf8))}
func exactFixtureResponse(_ row:[String:Any])->Data {Data((row["response_json"] as! String).utf8)}
func inboxReadSnapshot(_ thread:InboxThread?,_ rows:[InboxConversation])->Data {
    func nullable<T>(_ value:T?)->Any {value.map {$0 as Any} ?? NSNull()}
    func item(_ c:InboxConversation)->[String:Any] {["id":c.id,"title":nullable(c.title),"channel":nullable(c.channel),"unread_count":c.unread_count,"handoff_required":nullable(c.handoff_required),"preview":nullable(c.last_message_preview?.text)]}
    var object:[String:Any] = ["rows":rows.map(item)]
    if let t=thread {object["thread"]=["business":t.business,"conversation":item(t.conversation),"status":nullable(t.sourceStatus),"client":nullable(t.clientReferenceID),"budget":t.payload_budget.max_messages,"messages":t.messages.map {m in ["id":m.id,"parent":m.conversation_id,"direction":nullable(m.direction),"sender":nullable(m.sender_type),"text":nullable(m.text),"created":nullable(m.created_at),"state":m.sourceState.rawValue] as [String:Any]}]}
    else {object["thread"]=NSNull()}
    return try! JSONSerialization.data(withJSONObject:object,options:[.sortedKeys])
}
actor ControlledHandoffPort:SyntheticHandoffPort {
    nonisolated let grants:[SyntheticHandoffGrant]
    private var attempts:[HandoffAttempt]=[]
    private var pending:[Int:CheckedContinuation<SyntheticHandoffOutcome,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    init(_ grants:[SyntheticHandoffGrant]) {self.grants=grants}
    func execute(_ a:HandoffAttempt) async throws -> SyntheticHandoffOutcome {let i=attempts.count;attempts.append(a);return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ value:SyntheticHandoffOutcome) {pending.removeValue(forKey:i)!.resume(returning:value)}
    func fail(_ i:Int) {pending.removeValue(forKey:i)!.resume(throwing:ReadFailure.unavailable)}
    func recorded()->[HandoffAttempt] {attempts}
}
@MainActor func checkInboxHandoff(directory:URL) async throws -> Int {
    var count=0
    func expect(_ v:Bool,_ message:String) throws {guard v else {throw ViewModelCheckFailure(message:message)};count += 1}
    func thread(_ b:Int=101,_ id:Int=901) throws -> InboxThread {try JSONDecoder().decode(InboxThread.self,from:Data(contentsOf:directory.appendingPathComponent("inbox-\(b)-\(id).json")))}
    let original=try thread(),fixture=FixtureHandoffPort(directory:directory),p=ControlledHandoffPort(fixture.grants),m=InboxHandoffViewModel(port:p)
    func prepare(_ m:InboxHandoffViewModel,_ raw:String=" Manager review ",epoch:Int=280) {m.verified(original,business:101,id:901,epoch:epoch);m.open(expected:m.entryControl);m.update(raw,input:m.inputControl);m.prepare(expected:m.control)}
    func textEvidence(_ label:String,_ value:String)->String {
        let scalars=value.unicodeScalars.map {String(format:"U+%04X",$0.value)}.joined(separator:" ")
        let bytes=value.utf8.map {String(format:"%02X",$0)}.joined(separator:" ")
        return label+" characters="+String(value.count)+" scalars="+String(value.unicodeScalars.count)+" utf8="+String(value.utf8.count)+" ["+scalars+"] bytes=["+bytes+"]"
    }
    let feedbackRows=(try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("inbox-handoff-outcome.json"))) as! [String:Any])["input_cases"] as! [[String:Any]]
    for row in feedbackRows {
        let caseName=row["name"] as? String ?? "unnamed",raw=exactFixtureString(row,"raw"),valid=row["valid"] as! Bool,rp=ControlledHandoffPort(fixture.grants),visible=InboxHandoffViewModel(port:rp)
        visible.verified(original,business:101,id:901,epoch:280);visible.open(expected:visible.entryControl);let stale=visible.control
        visible.back(expected:visible.returnControl);visible.open(expected:visible.entryControl);visible.update(raw,input:visible.inputControl)
        let current=visible.control,input=visible.inputControl
        try expect(current != nil && input != nil && current != stale,"Feedback regression did not capture fresh editor")
        visible.prepare(expected:nil);visible.prepare(expected:stale)
        try expect(visible.control==current && visible.inputControl==input && !visible.session.inputError && visible.session.phase == .editing && visible.session.review==nil && visible.session.raw.utf8.elementsEqual(raw.utf8),"Null/stale prepare changed visible feedback or raw")
        visible.prepare(expected:current)
        let noCalls=await rp.recorded()
        try expect(visible.session.inputError == !valid && visible.session.raw.utf8.elementsEqual(raw.utf8) && visible.session.phase == (valid ? .review:.editing) && (visible.session.review != nil)==valid && visible.clearConfirmation==nil && visible.retainedAttemptCount==0 && visible.record==nil && !visible.blocked && noCalls.isEmpty,"Shared reason prepare feedback/raw/attempt regression; case="+caseName)
        if valid {
            guard let encodedBody=row["expected_body_json"] as? String else {throw ViewModelCheckFailure(message:"Missing independent expected body for "+caseName)}
            let expectedBody=try JSONDecoder().decode([String:String].self,from:Data(encodedBody.utf8))
            guard Set(expectedBody.keys)==["reason"],let expectedReason=expectedBody["reason"],let review=visible.session.review else {throw ViewModelCheckFailure(message:"Missing expected reason/review for "+caseName)}
            let exactRaw=review.value.raw.utf8.elementsEqual(raw.utf8)
            let exactReason=review.value.reason.utf8.elementsEqual(expectedReason.utf8)
            var message="Visible review changed exact optional/shared reason; case="+caseName
            if !exactRaw || !exactReason {
                let evidence=[textEvidence("raw.expected",raw),textEvidence("raw.actual",review.value.raw),textEvidence("reason.expected",expectedReason),textEvidence("reason.actual",review.value.reason)]
                message += "; "+evidence.joined(separator:"; ")
            }
            try expect(exactRaw && exactReason,message)
        } else {
            try expect(visible.control==current && visible.inputControl==input && !visible.canSubmit,"Rejected prepare invalidated retained editor or enabled submit")
            visible.update(" corrected ",input:input);try expect(!visible.session.inputError && visible.session.raw==" corrected ","Correction did not clear existing issue")
            visible.prepare(expected:visible.control);let after=await rp.recorded()
            try expect(!visible.session.inputError && visible.session.review?.value.reason=="corrected" && visible.session.review?.value.raw==" corrected " && visible.retainedAttemptCount==0 && after.isEmpty,"Explicit corrected review dispatched or lost raw")
        }
    }
    let plain=InboxHandoffViewModel();prepare(plain);try expect(plain.entryControl==nil && plain.control==nil && !plain.canSubmit,"GET became fake handoff UPDATE")
    let denied=InboxHandoffViewModel(port:ControlledHandoffPort([SyntheticHandoffGrant(business:101,conversation:901,actor:9001,update:false)]));prepare(denied);try expect(denied.entryControl==nil && !denied.canSubmit,"VIEW-only grant opened handoff")
    m.verified(original,business:101,id:901,epoch:280);m.open(expected:m.entryControl);m.update(" e\u{0301} ",input:m.inputControl);m.askClear(expected:m.control);let reset=m.clearConfirmation!;m.update(" é ",input:m.inputControl);m.confirmClear(reset);try expect(m.session.raw==" é " && m.control != nil && m.clearConfirmation==nil,"Canonical edit left old reset consent current")
    m.prepare(expected:m.control);let old=m.session.review!,oldControl=m.control!;m.back(expected:m.returnControl);m.update(" e\u{0301} ",input:m.inputControl);m.prepare(expected:m.control);await m.submit(old,expected:m.control);await m.submit(m.session.review!,expected:oldControl);let before=await p.recorded();try expect(before.isEmpty,"Stale raw/visit handoff submitted")
    let r=m.session.review!,c=m.control!,job=Task {await m.submit(r,expected:c)};await p.wait(0);let pending=m.record!,pc=m.control;m.update("lost",input:m.inputControl);m.askClear(expected:pc);m.prepare(expected:pc);m.acknowledge(expected:pc,record:pending);await m.submit(r,expected:pc);let calls=await p.recorded();try expect(calls.count==1 && m.record==pending && m.session.raw.utf8.elementsEqual(r.value.raw.utf8) && m.clearConfirmation==nil,"Pending handoff repeated/mutated/lost raw")
    m.back(expected:m.returnControl);m.open(expected:m.entryControl);try expect(m.record==pending && m.inputControl==nil,"Reopened pending handoff permitted edit")
    await p.fail(0);await job.value;let unknown=m.record!;m.acknowledge(expected:m.control,record:unknown);m.verified(original,business:101,id:901,epoch:281);m.open(expected:m.entryControl);try expect(m.blocked && m.record==nil && m.inputControl==nil && unknown.attempt.review==r,"Epoch/reread/ack erased unknown handoff")
    let np=ControlledHandoffPort(fixture.grants),noWrite=InboxHandoffViewModel(port:np);prepare(noWrite," \n ");let nr=noWrite.session.review!,nc=noWrite.control!;let nj=Task {await noWrite.submit(nr,expected:nc)};await np.wait(0);await np.resolve(0,.rejectedWithoutWrite);await nj.value;noWrite.acknowledge(expected:noWrite.control,record:noWrite.record!);await noWrite.submit(nr,expected:nc);let recorded=await np.recorded();try expect(noWrite.session.phase == .editing && noWrite.session.raw==nr.value.raw && noWrite.session.review==nil && recorded.count==1,"No-write blank reason lost/repeated without fresh review")
    noWrite.prepare(expected:noWrite.control);let next=Task {await noWrite.submit(noWrite.session.review!,expected:noWrite.control)};await np.wait(1);let history=await np.recorded();try expect(history[0].localID != history[1].localID && history.allSatisfy {$0.preparedHeaders.isEmpty} && history[1].review.value==nr.value,"Fresh reason invented server key or changed blank intent");await np.resolve(1,.unknown);await next.value
    let transport=SearchTransport(directory),owner=InboxViewModel(repository:APIReadRepository(transport:transport),replySubmission:FixtureInboxReplyPort(directory:directory),handoffSubmission:fixture);await owner.load(business:101,epoch:282);await owner.open(id:901);let snapshot=inboxReadSnapshot(owner.thread,owner.items),flag=owner.handoffState,reads=await transport.recorded().count,entry=owner.handoff.entryControl!,parent=owner.control!,returned=owner.returnControl
    owner.openHandoff(entry:entry,expected:parent);let h=owner.handoff;owner.openReply(owner.reply.session.context!,expected:owner.control);owner.backToThreadList(expected:returned);try expect(h.control != nil && owner.reply.control==nil && inboxReadSnapshot(owner.thread,owner.items)==snapshot,"Root stale Back or sibling displaced handoff editor")
    h.update(" Saved test reason ",input:h.inputControl);h.prepare(expected:h.control);await h.submit(h.session.review!,expected:h.control);let receipt=h.record!,after=await transport.recorded().count
    try expect(receipt.phase == .confirmed && inboxReadSnapshot(owner.thread,owner.items)==snapshot && flag==owner.handoffState && reads==after,"Fake handoff updated real-read flag/AI/messages/counts or reloaded")
    h.acknowledge(expected:h.control,record:receipt);try expect(h.control==nil && h.session.raw.isEmpty && h.retainedAttemptCount==1,"Known handoff acknowledgement lost attempt or left editor")
    let lp=ControlledHandoffPort(fixture.grants),late=InboxHandoffViewModel(port:lp);prepare(late);let lj=Task {await late.submit(late.session.review!,expected:late.control)};await lp.wait(0);let a=await lp.recorded()[0];late.verified(try thread(202,951),business:202,id:951,epoch:283);late.open(expected:late.entryControl);late.update(" Other owner ",input:late.inputControl);let replacement=late.control,input=late.inputControl
    await lp.resolve(0,try await fixture.execute(a));await lj.value;try expect(late.control==replacement && late.inputControl==input && late.session.raw==" Other owner " && late.record==nil,"Late handoff completion touched foreign input")
    return count
}
