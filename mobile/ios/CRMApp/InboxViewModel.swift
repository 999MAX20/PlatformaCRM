import Foundation
import SwiftUI
import CRMCore

// Captured local UI identity, not a server version/key or access grant.
struct InboxControl:Equatable {let business:Int;let epoch:Int;let generation:Int;let thread:InboxReadSelection?}

struct InboxListInputControl:Equatable {let parent:InboxControl;let window:Int}
struct InboxListControl:Equatable {let input:InboxListInputControl;let revision:Int}
struct InboxThreadRetryControl:Equatable {let parent:InboxReturnControl;let failure:ReadFailure}

struct InboxReturnControl:Equatable {let parent:InboxControl?;let thread:InboxReadSelection?;let reply:ReplyDraftReturnControl;let client:InboxClientReturnControl?;let handoff:HandoffReturnControl;let files:InboxConversationFilesControl?;let messageFiles:InboxMessageFilesControl?}

struct InboxFilesEntryControl:Equatable {let parent:InboxReturnControl;let child:InboxConversationFilesControl}
struct InboxFilesPresentationControl:Equatable {let parent:InboxControl;let thread:InboxReadSelection;let child:InboxConversationFilesPresentation;let reply:ReplyDraftReturnControl;let client:InboxClientReturnControl?;let handoff:HandoffReturnControl}

struct InboxMessageFilesEntryControl:Equatable {
    let parent:InboxReturnControl;let row:InboxMessage;let child:InboxMessageFilesControl
    static func ==(a:Self,b:Self)->Bool {a.parent==b.parent && a.child==b.child && InboxMessageFileSourceIdentity.same(a.row,b.row)}
}
struct InboxMessageFilesPresentationControl:Equatable {let parent:InboxControl;let thread:InboxReadSelection;let child:InboxMessageFilesPresentation;let reply:ReplyDraftReturnControl;let client:InboxClientReturnControl?;let handoff:HandoffReturnControl;let files:InboxConversationFilesControl?}
@MainActor final class InboxViewModel: ObservableObject {
    @Published private(set) var business: Int?
    @Published private(set) var items: [InboxConversation] = []
    @Published private(set) var total = 0
    @Published var query = "" {didSet {if !query.utf8.elementsEqual(oldValue.utf8) {listViewRevision += 1}}}
    @Published var unreadOnly = false {didSet {if unreadOnly != oldValue {listViewRevision += 1}}}
    @Published private(set) var loading = false
    @Published private(set) var loaded = false
    @Published private(set) var failure: ReadFailure?
    @Published private(set) var selectedID: Int?
    @Published private(set) var thread: InboxThread?
    @Published private(set) var threadLoading = false
    @Published private(set) var threadFailure: ReadFailure?
    @Published private(set) var searchRevision = 0
    @Published private(set) var scopeEpoch: Int?
    let reply: ReplyDraftViewModel
    let handoff:InboxHandoffViewModel
    let clientLinks: InboxClientViewModel?
    let fileMetadata:InboxConversationFilesViewModel?
    let messageMetadata:InboxMessageFilesViewModel?
    @Published private var controlGeneration=0
    var control:InboxControl? {guard let business,business>0,let scopeEpoch,scopeEpoch>0 else {return nil};return InboxControl(business:business,epoch:scopeEpoch,generation:controlGeneration,thread:threadSelection)}
    func matches(_ expected:InboxControl?) -> Bool {expected != nil && control==expected}
    var returnControl:InboxReturnControl {InboxReturnControl(parent:control,thread:threadSelection,reply:reply.returnControl,client:clientLinks?.returnControl,handoff:handoff.returnControl,files:fileMetadata?.control,messageFiles:messageMetadata?.control)}
    @Published private var listViewRevision=0
    var listInputControl:InboxListInputControl? {guard messageMetadata?.presented != true,fileMetadata?.presented != true,let control,!loading,selectedID==nil,reply.control==nil,handoff.control==nil,clientLinks?.selectedID==nil else {return nil};return InboxListInputControl(parent:control,window:listRevision)}
    var listControl:InboxListControl? {listInputControl.map {InboxListControl(input:$0,revision:listViewRevision)}}
    var threadRetryControl:InboxThreadRetryControl? {guard messageMetadata?.presented != true,fileMetadata?.presented != true,control != nil,threadSelection != nil,!threadLoading,thread==nil,let failure=threadFailure,reply.control==nil,handoff.control==nil,clientLinks?.selectedID==nil else {return nil};return InboxThreadRetryControl(parent:returnControl,failure:failure)}
    private var listRevision = 0
    private var threadRevision = 0
    private let repository: any InboxRepository
    var threadSelection: InboxReadSelection? {guard let business,let selectedID else {return nil};return InboxReadSelection(business:business,id:selectedID,revision:threadRevision)}
    var handoffState: HandoffReadState? {
        guard let business,let selectedID,let scopeEpoch,scopeEpoch>0,!threadLoading,threadFailure==nil,let thread,thread.valid(for:business,id:selectedID) else {return nil}
        return thread.conversation.handoffState
    }
    init(repository: any InboxRepository,quickReplies: (any QuickReplyRepository)? = nil,replySubmission:(any SyntheticInboxReplyPort)?=nil,handoffSubmission:(any SyntheticHandoffPort)?=nil,files:(any InboxConversationFilesRepository)?=nil,messageFiles:(any InboxMessageFilesRepository)?=nil,retrySubmission:(any SyntheticInboxRetryPort)?=nil,assignmentRead:(any InboxSelfAssignmentRepository)?=nil,assignmentSubmission:(any SyntheticInboxSelfAssignmentPort)?=nil,markerRead:(any InboxReadMarkerRepository)?=nil,markerSubmission:(any SyntheticInboxReadMarkerPort)?=nil,priorityRead:(any InboxPriorityRepository)?=nil,prioritySubmission:(any SyntheticInboxPriorityPort)?=nil,lifecycleRead:(any InboxLifecycleRepository)?=nil,lifecycleSubmission:(any SyntheticInboxLifecyclePort)?=nil,linkRead:(any InboxLinkClientRepository)?=nil,linkClients:(any ClientSearchRepository)?=nil,linkSubmission:(any SyntheticInboxLinkClientPort)?=nil,leads:(any LeadReadRepository)?=nil,leadLinkRead:(any InboxLinkLeadRepository)?=nil,leadLinkSubmission:(any SyntheticInboxLinkLeadPort)?=nil,deals:(any DealReadRepository)?=nil,dealLinkRead:(any InboxLinkDealRepository)?=nil,dealLinkSubmission:(any SyntheticInboxLinkDealPort)?=nil,members:(any TeamMemberReadRepository)?=nil,targetAssignmentRead:(any InboxTargetAssignmentRepository)?=nil,targetAssignmentSubmission:(any SyntheticInboxTargetAssignmentPort)?=nil,taskSourceRead:(any InboxTaskSourceRepository)?=nil,taskCreateSubmission:(any SyntheticInboxCreateTaskPort)?=nil,existingClientRead:(any InboxExistingClientRepository)?=nil,existingClientSubmission:(any SyntheticInboxExistingClientPort)?=nil,existingLeadRead:(any InboxExistingLeadRepository)?=nil,existingLeadSubmission:(any SyntheticInboxExistingLeadPort)?=nil,existingDealRead:(any InboxExistingDealRepository)?=nil,existingDealSubmission:(any SyntheticInboxExistingDealPort)?=nil) {self.messageMetadata=messageFiles.map {InboxMessageFilesViewModel(repository:$0,retryPort:retrySubmission)};fileMetadata=files.map {InboxConversationFilesViewModel(repository:$0,assignmentRead:assignmentRead,assignmentPort:assignmentSubmission,markerRead:markerRead,markerPort:markerSubmission,priorityRead:priorityRead,priorityPort:prioritySubmission,lifecycleRead:lifecycleRead,lifecyclePort:lifecycleSubmission,linkRead:linkRead,linkClients:linkClients,linkPort:linkSubmission,leads:leads,leadLinkRead:leadLinkRead,leadLinkPort:leadLinkSubmission,deals:deals,dealLinkRead:dealLinkRead,dealLinkPort:dealLinkSubmission,members:members,targetAssignmentRead:targetAssignmentRead,targetAssignmentPort:targetAssignmentSubmission,taskSourceRead:taskSourceRead,taskCreatePort:taskCreateSubmission,existingClientRead:existingClientRead,existingClientPort:existingClientSubmission,existingLeadRead:existingLeadRead,existingLeadPort:existingLeadSubmission,existingDealRead:existingDealRead,existingDealPort:existingDealSubmission)}; self.repository = repository;handoff=InboxHandoffViewModel(port:handoffSubmission);reply=ReplyDraftViewModel(quickReplies:quickReplies,submission:replySubmission); clientLinks = (repository as? any InboxClientRepository).map { InboxClientViewModel(repository: $0) }
        messageMetadata?.commandsBlocked = { [weak self] in guard let self else {return true};return self.conversationCommandsBlocked || self.reply.submissionBlocked || self.handoff.blocked || self.reply.control != nil || self.handoff.control != nil || self.clientLinks?.selectedID != nil }
        fileMetadata?.commandsBlocked = { [weak self] in guard let self else {return true};return self.retryCommandsBlocked || self.reply.submissionBlocked || self.handoff.blocked || self.reply.control != nil || self.handoff.control != nil || self.clientLinks?.selectedID != nil }
        reply.externalCommandBlocked = { [weak self] in guard let self else {return true};return self.retryCommandsBlocked || self.conversationCommandsBlocked }
        handoff.externalCommandBlocked = { [weak self] in guard let self else {return true};return self.retryCommandsBlocked || self.conversationCommandsBlocked }
    }
    var assignmentCommandsBlocked:Bool {conversationCommandsBlocked}
    var conversationCommandsBlocked:Bool {guard let business,let id=selectedID else {return false};return fileMetadata?.blocksCommands(business:business,conversation:id)==true}
    var retryCommandsBlocked:Bool {guard let business,let id=selectedID else {return false};return messageMetadata?.blocksCommands(business:business,conversation:id)==true}
    var partial: Bool { total > items.count }
    var visible: [InboxConversation] {
        let needle = query.trimmingCharacters(in: .whitespacesAndNewlines)
        return items.filter { item in
            (!unreadOnly || item.unread_count > 0) && (needle.isEmpty || [item.title, item.last_message_preview?.text].compactMap { $0 }.contains { $0.range(of: needle, options: .caseInsensitive) != nil })
        }
    }
    var showsEmpty: Bool { loaded && !loading && failure == nil && !partial && visible.isEmpty }
    func load(business next: Int?, epoch: Int? = nil) async {
        reply.retainOwner(business:next,epoch:epoch);handoff.retainOwner(business:next,epoch:epoch)
        searchRevision += 1
        listRevision += 1; let ticket = listRevision; back()
        if business != next || scopeEpoch != epoch { query = ""; unreadOnly = false }
        scopeEpoch = epoch; business = next; items = []; total = 0; failure = nil; loaded = false; loading = next != nil
        guard let next else { return }
        guard next > 0 else { loading = false; failure = .invalidContext; return }
        do {
            let page = try await repository.inbox(business: next)
            guard ticket == listRevision else { return }
            guard page.valid(for: next) else { throw ReadFailure.invalidPayload }
            items = page.items; total = page.summary.open; loaded = true; loading = false
        } catch {
            guard ticket == listRevision else { return }
            loading = false
            if !(error is CancellationError) { failure = error as? ReadFailure ?? .unavailable }
        }
    }
    func open(id:Int) async {await openImpl(id:id)}
    func open(id:Int,expected:InboxControl?) async {guard let expected else {return};await openImpl(id:id,expected:expected)}
    private func openImpl(id: Int,expected:InboxControl?=nil) async {
        if let expected {guard matches(expected),loaded,!loading,failure==nil,selectedID==nil,visible.contains(where:{$0.id==id}) else {return}}
        guard let business, items.contains(where: { $0.id == id }) else { return }
        controlGeneration += 1
        messageMetadata?.bind(nil);fileMetadata?.bind(nil);clientLinks?.clear()
        reply.beginRead(business:business,id:id,epoch:scopeEpoch);handoff.beginRead(business:business,id:id,epoch:scopeEpoch)
        threadRevision += 1; let ticket = threadRevision, scope = listRevision
        selectedID = id; thread = nil; threadLoading = true; threadFailure = nil
        do {
            let detail = try await repository.thread(business: business, id: id)
            guard ticket == threadRevision, scope == listRevision else { return }
            guard detail.valid(for: business, id: id) else { throw ReadFailure.invalidPayload }
            searchRevision += 1; thread = detail; items = items.map { $0.id == id ? detail.conversation : $0 }; threadLoading = false
            bindFiles();reply.verified(detail,business:business,id:id,epoch:scopeEpoch);handoff.verified(detail,business:business,id:id,epoch:scopeEpoch)
            clientLinks?.bind(detail,request: InboxReadSelection(business: business,id: id,revision: ticket)) { [weak self] result in
                guard let self, ticket == self.threadRevision, scope == self.listRevision else { return }
                self.messageMetadata?.bind(nil);self.fileMetadata?.bind(nil)
                switch result {
                case .success(let fresh): self.reply.verified(fresh,business:business,id:id,epoch:self.scopeEpoch);self.handoff.verified(fresh,business:business,id:id,epoch:self.scopeEpoch); self.searchRevision += 1; self.thread = fresh; self.items = self.items.map { $0.id == id ? fresh.conversation : $0 }; self.threadFailure = nil;self.bindFiles()
                case .failure(let failure): self.reply.pause();self.handoff.pause(); self.thread = nil; self.threadFailure = failure
                }
            }
        } catch {
            guard ticket == threadRevision, scope == listRevision else { return }
            if error is CancellationError { back() }
            else { reply.pause();handoff.pause(); threadLoading = false; threadFailure = error as? ReadFailure ?? .unavailable }
        }
    }
    func back() {messageMetadata?.bind(nil);fileMetadata?.bind(nil);controlGeneration += 1; reply.pause();handoff.pause(); clientLinks?.clear(); threadRevision += 1; selectedID = nil; thread = nil; threadLoading = false; threadFailure = nil }
    func back(expected: InboxReadSelection?) {guard let expected,threadSelection==expected else {return};back()}
    func retryThread(expected: InboxReadSelection?) async {guard let expected,threadSelection==expected else {return};await open(id:expected.id)}
    func reconcileHandoffOwner(business next: Int?,epoch: Int) {guard business != next || scopeEpoch != epoch else {return};clear()}
    func clear() { reply.clear();handoff.clear(); searchRevision += 1; scopeEpoch = nil; listRevision += 1; back(); business = nil; items = []; total = 0; query = ""; unreadOnly = false; loading = false; loaded = false; failure = nil }
}

extension InboxViewModel {
    func back(expected:InboxControl?,thread:InboxReadSelection?) {guard messageMetadata?.presented != true,fileMetadata?.presented != true,matches(expected),threadSelection==thread,thread != nil else {return};back()}
    func retryThread(expected:InboxReadSelection?,control:InboxControl?) async {guard matches(control) else {return};await retryThread(expected:expected)}
    func search(_ text:String,expected:InboxControl?) {guard matches(expected),!loading,selectedID==nil else {return};query=text}
    func filterUnread(_ value:Bool,previous:Bool,expected:InboxControl?) {guard matches(expected),!loading,selectedID==nil,unreadOnly==previous else {return};unreadOnly=value}
    func retryList(expected:InboxControl?) async {guard let expected,matches(expected),!loading,selectedID==nil else {return};await load(business:expected.business,epoch:expected.epoch)}
    func openReply(_ context:ReplyDraftContext,expected:InboxControl?) {
        guard !retryCommandsBlocked,!conversationCommandsBlocked,messageMetadata?.presented != true,fileMetadata?.presented != true,matches(expected),!threadLoading,threadFailure==nil,thread != nil,handoff.control==nil,!handoff.blocks(context),reply.session.available,reply.session.context==context,reply.session.selection==nil,clientLinks?.selectedID==nil else {return}
        controlGeneration += 1;_ = clientLinks?.back(expected:threadSelection);reply.open(context)
    }
    func openClient(_ presentation:InboxClientPresentation?,expected:InboxControl?) async {
        guard messageMetadata?.presented != true,fileMetadata?.presented != true,matches(expected),!threadLoading,threadFailure==nil,thread != nil,reply.session.selection==nil,handoff.control==nil,let clientLinks,let presentation,clientLinks.presentation==presentation,presentation.request==threadSelection else {return}
        controlGeneration += 1;await clientLinks.open(presentation:presentation)
    }
    // Continuous input retains its visit; list actions additionally capture each query/filter window.
    func search(_ text:String,input:InboxListInputControl?) {guard let input,listInputControl==input else {return};query=text}
    func filterUnread(_ value:Bool,list:InboxListControl?) {guard let list,listControl==list else {return};unreadOnly=value}
    func open(id:Int,list:InboxListControl?) async {guard let list,listControl==list else {return};await open(id:id,expected:list.input.parent)}
    func retryList(list:InboxListControl?) async {guard let list,listControl==list else {return};await load(business:list.input.parent.business,epoch:list.input.parent.epoch)}
    func retryThread(control:InboxThreadRetryControl?) async {guard let control,threadRetryControl==control,let target=control.parent.thread else {return};await retryThread(expected:target)}
    // Captured UI actions; raw entry/back methods above retain trusted behavior.
    func openClient(entry:InboxClientEntryControl?,expected:InboxControl?) async {
        guard let entry,clientLinks?.entryControl==entry else {return}
        await openClient(entry.presentation,expected:expected)
    }
    func retryClient(expected:InboxClientControl?,parent:InboxControl?) async {
        guard messageMetadata?.presented != true,fileMetadata?.presented != true,matches(parent),reply.session.selection==nil,handoff.control==nil,!threadLoading,threadFailure==nil,thread != nil,let expected,expected.presentation.request==threadSelection else {return}
        await clientLinks?.retry(expected:expected)
    }
    func openHandoff(entry:HandoffEntryControl?,expected:InboxControl?) {
        guard !retryCommandsBlocked,!conversationCommandsBlocked,messageMetadata?.presented != true,fileMetadata?.presented != true,matches(expected),!threadLoading,threadFailure==nil,let thread,let business,let id=selectedID,thread.valid(for:business,id:id),reply.control==nil,!reply.submissionBlocked,clientLinks?.selectedID==nil,let entry,handoff.entryControl==entry,entry.context.business==business,entry.context.conversation==id,entry.context.epoch==scopeEpoch else {return}
        controlGeneration += 1;_ = clientLinks?.back(expected:threadSelection);handoff.open(expected:entry)
    }
    func backToThreadList(expected:InboxReturnControl?) {
        guard messageMetadata?.presented != true,fileMetadata?.presented != true,let expected,returnControl==expected,let parent=expected.parent,let thread=expected.thread,reply.session.selection==nil,handoff.control==nil,clientLinks?.selectedID==nil else {return}
        back(expected:parent,thread:thread)
    }
}


extension InboxViewModel {
    private var filesContext:InboxConversationFilesContext? {
        guard let read=threadSelection,let epoch=scopeEpoch,epoch>0,!threadLoading,threadFailure==nil,let thread,thread.valid(for:read.business,id:read.id) else {return nil}
        return InboxConversationFilesContext(business:read.business,conversation:read.id,epoch:epoch,revision:read.revision)
    }
    private var messageFilesOwner:InboxMessageFilesOwner? {guard let read=filesContext,let thread else {return nil};let owner=InboxMessageFilesOwner(read:read,limit:thread.payload_budget.max_messages);return owner.valid ? owner:nil}
    private func bindFiles() {fileMetadata?.bind(filesContext);messageMetadata?.bind(messageFilesOwner)}
    var filesEntryControl:InboxFilesEntryControl? {
        guard messageMetadata?.presented != true,filesContext==fileMetadata?.context,reply.control==nil,handoff.control==nil,clientLinks?.selectedID==nil,fileMetadata?.presented==false,let child=fileMetadata?.control else {return nil}
        return InboxFilesEntryControl(parent:returnControl,child:child)
    }
    var filesPresentationControl:InboxFilesPresentationControl? {
        guard messageMetadata?.presented != true,let parent=control,let read=threadSelection,filesContext==fileMetadata?.context,reply.control==nil,handoff.control==nil,clientLinks?.selectedID==nil,let child=fileMetadata?.presentation else {return nil}
        return InboxFilesPresentationControl(parent:parent,thread:read,child:child,reply:reply.returnControl,client:clientLinks?.returnControl,handoff:handoff.returnControl)
    }
    func matchesFiles(_ expected:InboxFilesPresentationControl?)->Bool {expected != nil && filesPresentationControl==expected}
    func openFiles(expected:InboxFilesEntryControl?) {guard let expected,filesEntryControl==expected,returnControl==expected.parent,fileMetadata?.open(expected:expected.child)==true else {return};controlGeneration += 1}
    func closeFiles(expected:InboxFilesPresentationControl?) {guard let expected,matchesFiles(expected) else {return};fileMetadata?.close(expected:expected.child);controlGeneration += 1}
}


extension InboxViewModel {
    func messageFilesEntryControl(_ row:InboxMessage)->InboxMessageFilesEntryControl? {
        guard let owner=messageFilesOwner,messageMetadata?.owner==owner,messageMetadata?.presented==false,fileMetadata?.presented != true,reply.control==nil,handoff.control==nil,clientLinks?.selectedID==nil,
              row.id>0,row.id<=Int(Int32.max),row.conversation_id==owner.read.conversation,let current=thread?.messages.first(where:{$0.id==row.id}),InboxMessageFileSourceIdentity.same(current,row),let child=messageMetadata?.control else {return nil}
        return InboxMessageFilesEntryControl(parent:returnControl,row:row,child:child)
    }
    var messageFilesPresentationControl:InboxMessageFilesPresentationControl? {
        guard let owner=messageFilesOwner,messageMetadata?.owner==owner,let parent=control,let read=threadSelection,let child=messageMetadata?.presentation,fileMetadata?.presented != true,reply.control==nil,handoff.control==nil,clientLinks?.selectedID==nil,thread?.messages.contains(where:{$0.id==child.context.message})==true else {return nil}
        return InboxMessageFilesPresentationControl(parent:parent,thread:read,child:child,reply:reply.returnControl,client:clientLinks?.returnControl,handoff:handoff.returnControl,files:fileMetadata?.control)
    }
    func matchesMessageFiles(_ expected:InboxMessageFilesPresentationControl?)->Bool {expected != nil && messageFilesPresentationControl==expected}
    func openMessageFiles(expected:InboxMessageFilesEntryControl?) {guard let expected,messageFilesEntryControl(expected.row)==expected,returnControl==expected.parent,messageMetadata?.open(message:expected.row.id,expected:expected.child)==true else {return};controlGeneration += 1}
    func closeMessageFiles(expected:InboxMessageFilesPresentationControl?) {guard let expected,matchesMessageFiles(expected) else {return};messageMetadata?.close(expected:expected.child);controlGeneration += 1}
}
