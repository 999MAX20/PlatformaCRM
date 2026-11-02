import Foundation
import CRMCore

@MainActor func checkReplyDraftExactText(directory:URL) async throws -> Int {
    var count=0
    func expect(_ v:Bool,_ message:String) throws {guard v else {throw ViewModelCheckFailure(message:message)};count += 1}
    let f=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("reply-draft-exact-text.json"))) as! [String:Any],thread=try JSONDecoder().decode(InboxThread.self,from:Data(contentsOf:directory.appendingPathComponent("inbox-101-901.json")))
    for row in f["snapshot_cases"] as! [[String:Any]] {
        let left=row["left"] as! String,right=row["right"] as! String;guard !left.utf8.elementsEqual(right.utf8) else {continue}
        let m=ReplyDraftViewModel();m.verified(thread,business:101,id:901,epoch:260);m.open(expected:m.entryControl);let input=m.inputControl;m.update(left,input:input);m.askClear(expected:m.control);let question=m.clearConfirmation!
        m.update(right,input:input);m.confirmClear(question)
        try expect(m.clearConfirmation==nil && m.session.selection != nil && m.session.text.utf8.elementsEqual(right.utf8),"Old clear discarded canonically-equivalent changed reply raw")
        m.prepare(expected:m.control);let review=m.session.review!
        try expect(review.raw.utf8.elementsEqual(right.utf8) && review.text.utf8.elementsEqual(ReplyDraftText.stripped(right).utf8),"Actual ViewModel failed immutable exact review")
        m.back(expected:m.returnControl);m.update("stale",input:input);try expect(m.session.text.utf8.elementsEqual(right.utf8),"Old preview input changed raw after Back")
    }
    let transport=SearchTransport(directory),owner=InboxViewModel(repository:APIReadRepository(transport:transport));await owner.load(business:101,epoch:262);await owner.open(id:901);let original=owner.thread!,snapshot=inboxReadSnapshot(owner.thread,owner.items),reads=await transport.recorded().count,m=owner.reply
    owner.openReply(m.session.context!,expected:owner.control);let raw=String(repeating:"e\u{0301}",count:250)+"Z";m.update(raw,input:m.inputControl);m.prepare(expected:m.control);let review=m.session.review!
    try expect(review.text.unicodeScalars.count==501 && review.raw.utf8.elementsEqual(raw.utf8),"Long manual text silently truncated or rejected at response excerpt size")
    m.back(expected:m.returnControl);m.close(expected:m.returnControl);owner.back();await owner.open(id:901);owner.openReply(m.session.context!,expected:owner.control)
    try expect(m.session.text.utf8.elementsEqual(raw.utf8),"Card return lost full raw")
    let after=await transport.recorded().count;try expect(after==reads+1 && inboxReadSnapshot(owner.thread,owner.items)==snapshot && owner.thread?.messages.map(\.id)==original.messages.map(\.id) && owner.thread?.conversation.unread_count==original.conversation.unread_count,"Reply foundation sent/requested/mutated source beyond explicit thread return read")
    owner.clear();try expect(m.session.text.isEmpty && m.session.context==nil && review.raw.utf8.elementsEqual(raw.utf8),"Clear retained visible private raw or changed old immutable snapshot")
    return count
}
