import Foundation
import CRMCore

@MainActor func checkQuickReplyControls(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let source=ControlledQuickReplies(directory),transport=SearchTransport(directory)
    let inbox=InboxViewModel(repository:APIReadRepository(transport:transport),quickReplies:source)
    await inbox.load(business:101,epoch:80);await inbox.open(id:901)
    let reply=inbox.reply,picker=reply.quickReplies!,context=ReplyDraftContext(business:101,conversation:901,epoch:80)
    reply.open(context);let editor=reply.control!,input=reply.inputControl!
    reply.update("  Operator own note  \n",input:input)
    let messages=inbox.thread?.messages.map(\.id),unread=inbox.thread?.conversation.unread_count,threadRead=inbox.threadSelection
    let reads=await transport.recorded(),entry=picker.entryControl!,parent=reply.returnControl
    await source.hold(true)
    let first=Task {await reply.openQuickReplies(expected:editor,entry:entry)};await source.wait(0)
    let pending=picker.control!,search=picker.inputControl!
    await reply.openQuickReplies(expected:editor,entry:entry);await picker.retry(expected:pending)
    try expect(await source.recorded().count==1 && picker.session.loading,"Duplicate entry/pending Retry restarted catalogue read")
    reply.back(expected:parent);reply.update("hidden old editor input",input:input);reply.prepare(expected:editor)
    try expect(picker.session.selection==pending.selection && reply.session.text=="  Operator own note  \n" && reply.session.phase == .editing,"Old composer action affected active picker")
    picker.search(" APPOINTMENTS ",input:search);let filteredPending=picker.control!
    picker.close(expected:pending)
    try expect(picker.session.loading && picker.control==filteredPending && picker.inputControl==search,"Old result-window Back closed current search or broke input")
    let page=try await FixtureQuickReplyRepository(directory:directory).quickReplies(business:101,channel:"website")
    await source.resolve(0,.success(page));await first.value;let loaded=picker.control!
    try expect(picker.inputControl==search && picker.session.query==" APPOINTMENTS " && picker.session.choices.map(\.id)==[9102],"Pending search was lost or source filtering/order changed")
    picker.close(expected:filteredPending);await picker.retry(expected:pending)
    let afterOldRetry=await source.recorded().count
    try expect(picker.control==loaded && !picker.session.loading && afterOldRetry==1,"Old completion/retry control acted on current source")
    picker.search("",input:search);let oldChoice=picker.session.choices[0],oldWindow=picker.control!
    picker.search("{{client}}",input:search);picker.search("",input:search);let window=picker.control!,choice=picker.session.choices[0]
    try expect(!reply.insert(oldChoice,expected:editor,picker:window) && !reply.insert(choice,expected:editor,picker:oldWindow),"Old filter choice or result-window inserted")
    try expect(reply.insert(choice,expected:editor,picker:window),"Current literal template failed to insert")
    let inserted=reply.session.text,current=reply.control!
    try expect(inserted=="  Operator own note\n"+choice.template.text && inserted.contains("{{client}}") && picker.control==nil && current.selection != editor.selection,"Insertion changed trim/literal body or failed to advance draft generation")
    reply.update("late input",input:input);try expect(!reply.insert(choice,expected:editor,picker:window) && reply.session.text==inserted,"Old composer/double pick mutated current draft")
    let readsAfterInsert=await transport.recorded()
    try expect(inbox.thread?.messages.map(\.id)==messages && inbox.thread?.conversation.unread_count==unread && inbox.threadSelection==threadRead && readsAfterInsert==reads,"Local picker/insert changed Inbox or issued transport read")
    // A dismissed pending catalogue cannot advance the newer picker's UI window.
    let secondEntry=picker.entryControl!;let leaving=Task {await reply.openQuickReplies(expected:current,entry:secondEntry)};await source.wait(1)
    let leavingInput=picker.inputControl!,leavingWindow=picker.control!;picker.close(expected:leavingWindow)
    let newEntry=picker.entryControl!;let reopening=Task {await reply.openQuickReplies(expected:current,entry:newEntry)};await source.wait(2)
    let newPending=picker.control!,newInput=picker.inputControl!
    await source.resolve(1,.success(page));await leaving.value;picker.search("old input",input:leavingInput)
    try expect(picker.control==newPending && picker.inputControl==newInput && picker.session.loading && picker.session.query=="","Late old completion advanced or repopulated new picker")
    await source.resolve(2,.failure(.denied));await reopening.value;let denied=picker.control!
    try expect(picker.session.failure == .denied && picker.session.choices.isEmpty && reply.session.text==inserted,"Denied catalogue erased own draft or kept choices")
    let retry=Task {await picker.retry(expected:denied)};await source.wait(3);let retryWindow=picker.control!
    await picker.retry(expected:denied);await picker.retry(expected:retryWindow);picker.search("absent needle",input:newInput)
    try expect((await source.recorded()).count==4 && picker.inputControl==newInput,"Retry duplicated pending source or revoked continuous search")
    var object=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("quick-replies-101-website.json"))) as! [String:Any]
    object.removeValue(forKey:"count");object.removeValue(forKey:"next")
    let partial=try JSONDecoder().decode(QuickReplyPage.self,from:JSONSerialization.data(withJSONObject:object))
    await source.resolve(3,.success(partial));await retry.value
    try expect(picker.session.partial && picker.session.choices.isEmpty && !picker.session.showsEmpty,"Unknown catalogue metadata turned a filtered window into complete empty")
    reply.back(expected:reply.returnControl);reply.prepare(expected:current);let review=reply.control!,reviewSnapshot=reply.session.review
    reply.back(expected:ReplyDraftReturnControl(editor:current,picker:nil,clear:nil))
    try expect(reply.control==review && reply.session.review==reviewSnapshot,"Old editing Back changed review")
    reply.back(expected:reply.returnControl);let editing=reply.control!;reply.prepare(expected:editing);let review2=reply.control!
    reply.back(expected:ReplyDraftReturnControl(editor:review,picker:nil,clear:nil))
    try expect(review2.selection==review.selection && reply.control==review2 && review2 != review,"Same-selection old review Back changed newer review")
    reply.back(expected:reply.returnControl);let clearControl=reply.control!,clearInput=reply.inputControl!
    reply.askClear(expected:clearControl);let oldQuestion=reply.clearConfirmation!
    reply.update("Own text after confirmation",input:clearInput);reply.confirmClear(oldQuestion)
    try expect(reply.clearConfirmation==nil && reply.session.text=="Own text after confirmation","Old clear consent erased newer input")
    reply.askClear(expected:clearControl);let dismissed=reply.clearConfirmation!;reply.dismissClear(dismissed);reply.askClear(expected:clearControl);let question=reply.clearConfirmation!
    reply.dismissClear(dismissed);reply.confirmClear(dismissed)
    try expect(reply.clearConfirmation==question && reply.session.text=="Own text after confirmation","Old dialog consumed replacement consent")
    let beforeQuestion=ReplyDraftReturnControl(editor:clearControl,picker:nil,clear:nil);reply.back(expected:beforeQuestion)
    try expect(reply.clearConfirmation==question && reply.control==clearControl,"Old parent Back bypassed clear dialog")
    reply.back(expected:reply.returnControl);try expect(reply.clearConfirmation==nil && reply.control==clearControl,"Current dialog Back closed editor")
    reply.close(expected:reply.returnControl);reply.open(context)
    try expect(reply.session.text=="Own text after confirmation","Close/reopen discarded own draft")
    reply.confirmClear(question);try expect(reply.session.text=="Own text after confirmation","Old closed-editor consent erased reopened text")
    reply.askClear(expected:reply.control);reply.confirmClear(reply.clearConfirmation!)
    try expect(reply.control==nil && reply.session.text.isEmpty,"Current explicit clear did not close and clear local draft")
    reply.open(context);reply.update("Old epoch private text",input:reply.inputControl);reply.askClear(expected:reply.control);let priorEpoch=reply.clearConfirmation!,oldInput=reply.inputControl
    await inbox.load(business:202,epoch:81);reply.confirmClear(priorEpoch);reply.update("old epoch callback",input:oldInput)
    try expect(reply.control==nil && reply.session.text.isEmpty && picker.session.context==nil,"Old owner actions retained or repopulated private draft")
    count += try await checkQuickReplyRawUnicode(directory:directory)
    return count
}

@MainActor private func checkQuickReplyRawUnicode(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let cases=(try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("quick-reply-raw-unicode-cases.json"))) as! [String:Any])["cases"] as! [[String:Any]]
    for (index,row) in cases.enumerated() {
        let before=row["before"] as! String,after=row["after"] as! String,changed=row["changed"] as! Bool,literal=row["template"] as! String,inserted=row["inserted"] as! String
        let page=try JSONDecoder().decode(QuickReplyPage.self,from:Data((row["page_json"] as! String).utf8)),source=ControlledQuickReplies(directory),transport=SearchTransport(directory),port=ControlledInboxReplyPort(FixtureInboxReplyPort(directory:directory).grants)
        await source.set(.success(page));let inbox=InboxViewModel(repository:APIReadRepository(transport:transport),quickReplies:source,replySubmission:port)
        let epoch=1800+index;await inbox.load(business:101,epoch:epoch);await inbox.open(id:901)
        let reply=inbox.reply,picker=reply.quickReplies!;reply.open(expected:reply.entryControl);reply.update(row["draft"] as! String,input:reply.inputControl);let editor=reply.control!
        let messages=inbox.thread?.messages.map(\.id),unread=inbox.thread?.conversation.unread_count,threadRead=inbox.threadSelection,reads=await transport.recorded()
        await reply.openQuickReplies(expected:editor,entry:picker.entryControl);let input=picker.inputControl!;picker.search(before,input:input)
        let oldChoice=picker.session.choices[0],oldWindow=picker.control!;picker.search(after,input:input);let current=picker.control!,choice=picker.session.choices[0]
        try expect(picker.session.query.utf8.elementsEqual(after.utf8) && picker.inputControl==input,"QuickReply dropped raw Unicode edit or continuous input")
        try expect((current != oldWindow)==changed && (choice.filterRevision != oldChoice.filterRevision)==changed && choice.id==oldChoice.id,"Same visible row retained an old raw filter/window")
        if changed {try expect(!reply.insert(oldChoice,expected:editor,picker:current) && !reply.insert(choice,expected:editor,picker:oldWindow),"Old filter choice/window inserted literal into composer")}
        else {try expect(picker.resolve(oldChoice,expected:oldWindow)?.utf8.elementsEqual(literal.utf8)==true,"Byte-identical input revoked current choice")}
        try expect(reply.insert(choice,expected:editor,picker:current),"Current explicit Unicode filter choice failed insertion")
        try expect(reply.session.text.utf8.elementsEqual(inserted.utf8) && inserted.contains("{{client}}") && picker.control==nil && reply.control?.selection != editor.selection,"Literal insertion normalized/interpolated body or reused old editor visit")
        let readsAfter=await transport.recorded();try expect(inbox.thread?.messages.map(\.id)==messages && inbox.thread?.conversation.unread_count==unread && inbox.threadSelection==threadRead && readsAfter==reads,"Local filter/insert mutated Inbox/read/unread or called transport")
        try expect(await source.recorded()==["101:website"],"Raw filter/insert re-read catalogue")
        reply.prepare(expected:reply.control);let review=reply.session.review!,sendControl=reply.control!,send=Task {await reply.submit(review,expected:sendControl)};await port.wait(0)
        let attempt=await port.recorded()[0],body=attempt.preparedBody();try expect(attempt.review.raw.utf8.elementsEqual(inserted.utf8),"Synthetic attempt lost raw literal insertion")
        await port.fail(0);await send.value;let unknown=reply.submission!
        try expect(unknown.phase == .unknown,"Lost reply did not retain unknown phase")
        try expect(unknown.attempt.preparedBody()==body,"Unknown changed frozen prepared body bytes")
        try expect(unknown.attempt==attempt && unknown.attempt.review==review,"Unknown changed literal/review/attempt identity")
        await reply.openQuickReplies(expected:reply.control,entry:picker.entryControl);try expect(picker.control==nil && reply.submissionBlocked && !reply.insert(choice,expected:editor,picker:current),"Unknown reopened picker or accepted old choice")
        await inbox.open(id:901);reply.open(expected:reply.entryControl);try expect(reply.submissionBlocked && reply.submission?.phase == .unknown,"Matching thread reread became outcome proof")
        await inbox.load(business:101,epoch:epoch+100);await inbox.open(id:901);reply.open(expected:reply.entryControl)
        let attempts=await port.recorded();try expect(reply.submissionBlocked && reply.submission==nil && reply.retainedAttemptCount==1 && reply.inputControl==nil && attempts.count==1,"Epoch bypassed literal unknown guard or replayed attempt")
    }
    return count
}
