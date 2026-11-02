import SwiftUI
import CRMCore

struct InboxScreen: View {
    @ObservedObject var agenda: AgendaViewModel
    @ObservedObject var model: InboxViewModel
    var isActive = true
    private var business: Int? { agenda.session.selection?.business.id }
    private var current: Bool { model.business == business && model.scopeEpoch == agenda.businessEpoch }
    private func value(_ raw: String?) -> String {
        guard let raw, !raw.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return AppCopy.text("notAvailable") }; return raw
    }
    private func error(_ failure: ReadFailure) -> String { failure == .notFound ? AppCopy.text("notAvailable") : AppCopy.error(failure) }
    private func sender(_ raw: String?) -> String {
        switch raw { case "client": AppCopy.text("senderClient"); case "manager": AppCopy.text("senderManager"); case "ai": AppCopy.text("senderAi"); default: value(raw) }
    }
    private func owns(_ expected:InboxControl?) -> Bool {guard let expected else {return false};return model.matches(expected) && agenda.session.selection?.business.id==expected.business && agenda.businessEpoch==expected.epoch}
    var body:some View {
        InboxReplyObservedContent(reply:model.reply) {
            InboxHandoffObservedContent(handoff:model.handoff) {
                if let files=model.fileMetadata {InboxConversationFilesObservedContent(files:files) {messageObservedContent}} else {messageObservedContent}
            }
        }
    }
    @ViewBuilder private var messageObservedContent:some View {if let files=model.messageMetadata {InboxMessageFilesObservedContent(files:files) {linkedContent}} else {linkedContent}}
    @ViewBuilder private var linkedContent:some View {if let links=model.clientLinks {InboxClientObservedContent(links:links) {screenContent}} else {screenContent}}
    private var screenContent:some View {
        let control=model.control,epoch=agenda.businessEpoch
        let readScope=AppCopy.text("inbox"),bootstrapScope=AppCopy.text("inbox")+": "+AppCopy.text("business")
        let list=model.listControl,input=model.listInputControl
        let threadSelection=model.threadSelection,rootReturn=model.returnControl
        return NavigationStack {
            VStack(spacing: 12) {
                Label(AppCopy.text("fixtureMode"), systemImage: "testtube.2").font(.caption)
                if let business {
                    Picker(AppCopy.text("business"), selection: Binding(get: { business }, set: { id in Task { await agenda.load(business: id) } })) {
                        ForEach(agenda.session.businesses) { Text($0.name).tag($0.id) }
                    }
                }
                if business == nil, let failure = agenda.failure {
                    Text(error(failure)).accessibilityLabel(Text(bootstrapScope+": "+error(failure))); Button(AppCopy.text("retry")) { Task { await agenda.start() } }.accessibilityLabel(Text(bootstrapScope+": "+AppCopy.text("retry")))
                } else if business == nil || !current || model.loading {
                    ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))
                } else {
                    TextField(AppCopy.text("inboxSearch"), text: Binding(get:{model.query},set:{if owns(control) {model.search($0,input:input)}})).textFieldStyle(.roundedBorder)
                    Toggle(AppCopy.text("unread"), isOn: Binding(get:{model.unreadOnly},set:{if owns(control) {model.filterUnread($0,list:list)}}))
                    if let failure = model.failure {
                        Text(error(failure)).accessibilityLabel(Text(readScope+": "+error(failure))); Button(AppCopy.text("retry")) { Task { if owns(control) {await model.retryList(list:list)} } }.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                    } else {
                        if model.partial { Label(AppCopy.text("partial"), systemImage: "exclamationmark.triangle") }
                        if model.showsEmpty { Text(AppCopy.text(model.query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !model.unreadOnly ? "inboxEmpty" : "noResults")) }
                        if model.visible.isEmpty { Button(AppCopy.text("retry")) { Task { if owns(control) {await model.retryList(list:list)} } }.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry"))) }
                        List(model.visible) { item in
                            Button { Task { if owns(control) {await model.open(id:item.id,list:list)} } } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(value(item.title))
                                    Text(value(item.last_message_preview?.text)).font(.caption)
                                    Text("\(AppCopy.text("unread")): \(item.unread_count)").font(.caption)
                                }.foregroundStyle(.primary)
                            }
                        }.listStyle(.plain)
                    }
                }
                Spacer(minLength: 0)
            }
            .padding(.horizontal)
            .navigationTitle(AppCopy.text("inbox"))
            .environment(\.locale, Locale(identifier: AppCopy.language))
            .navigationDestination(isPresented: Binding(get: { current && model.selectedID != nil }, set: { if !$0,owns(control) { model.backToThreadList(expected:rootReturn) } })) {
                if current {
                    ReplyDraftRoute(model:model.reply,context:replyContext,isCurrent:{owns(control) && model.threadSelection==threadSelection && model.thread != nil && !model.threadLoading && model.threadFailure==nil && model.clientLinks?.selectedID==nil && model.handoff.control==nil && model.fileMetadata?.presented != true && model.messageMetadata?.presented != true}) {
                        if let links = model.clientLinks, let business = agenda.session.selection?.business {
                            InboxClientRoute(links:links,business:business,isCurrent:{owns(control) && model.threadSelection==threadSelection && model.reply.control==nil && model.handoff.control==nil && model.fileMetadata?.presented != true && model.messageMetadata?.presented != true},retry:{child in Task {if owns(control) {await model.retryClient(expected:child,parent:control)}}}) { threadContent }
                        } else { threadContent }
                    }
                }
            }
            .task(id: "\(business ?? 0):\(agenda.businessEpoch):\(isActive)") {
                guard isActive else { return }
                guard agenda.session.selection?.business.id==business,agenda.businessEpoch==epoch else {return}
                if !current || (!model.loaded && !model.loading && model.failure == nil) {await model.load(business:business,epoch:epoch)} }
        }
    }
    private var replyContext: ReplyDraftContext? {
        guard current,let business,let id=model.selectedID,let epoch=model.scopeEpoch else { return nil };return ReplyDraftContext(business:business,conversation:id,epoch:epoch)
    }
    private var threadContent:some View {
        let control=model.control,target=model.threadSelection
        return InboxConversationFilesRoute(parent:model,isCurrent:{owns(control) && model.threadSelection==target && model.thread != nil && !model.threadLoading && model.threadFailure==nil}) {
            InboxMessageFilesRoute(parent:model,isCurrent:{owns(control) && model.threadSelection==target && model.thread != nil && !model.threadLoading && model.threadFailure==nil}) {
                InboxHandoffRoute(model:model.handoff,isCurrent:{owns(control) && model.threadSelection==target && model.thread != nil && !model.threadLoading && model.threadFailure==nil && model.reply.control==nil && model.clientLinks?.selectedID==nil && model.fileMetadata?.presented != true && model.messageMetadata?.presented != true}) {threadBody}
            }
        }
    }
    private var threadBody: some View {
        let control=model.control,retry=model.threadRetryControl
        let threadScope=AppCopy.text("inbox")+": "+AppCopy.text("details")
        return VStack(spacing: 12) {
            Label(AppCopy.text("fixtureMode"), systemImage: "testtube.2").font(.caption)
            if model.threadLoading { ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(threadScope+": "+AppCopy.text("loading"))) }
            else if let failure = model.threadFailure,model.selectedID != nil {
                Text(error(failure)).accessibilityLabel(Text(threadScope+": "+error(failure))); Button(AppCopy.text("retry")) { Task { if owns(control) {await model.retryThread(control:retry)} } }.accessibilityLabel(Text(threadScope+": "+AppCopy.text("retry")))
            } else if let thread = model.thread {
                Text(value(thread.conversation.title)).font(.headline)
                if let entry=model.filesEntryControl {Button(AppCopy.text("inboxFilesTitle")) {if owns(control) {model.openFiles(expected:entry)}}}
                Text("\(AppCopy.text("channel")): \(ReadChannelText.label(thread.conversation.channel,text: AppCopy.text))")
                if let state=model.handoffState {LabeledContent(AppCopy.text("handoffReadTitle"),value:AppCopy.text(state.copyKey)).accessibilityAddTraits(.updatesFrequently)}
                if let links = model.clientLinks { InboxClientButton(links:links) {entry in Task {if owns(control) {await model.openClient(entry:entry,expected:control)}}} }
                if let entry=model.handoff.entryControl,!model.reply.submissionBlocked,!model.retryCommandsBlocked {Button(AppCopy.text("handoffTestAction")) {if owns(control) {model.openHandoff(entry:entry,expected:control)}}}
                if model.retryCommandsBlocked {Text(AppCopy.text("inboxRetryBlocked"))} else {ReplyDraftButton(model:model.reply) { context in if owns(control) {model.openReply(context,expected:control)} }}
                if thread.windowCapped { Label(AppCopy.text("partial"), systemImage: "exclamationmark.triangle") }
                if thread.messages.isEmpty { Text(AppCopy.text("messagesEmpty")) }
                List(thread.messages) { message in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(sender(message.sender_type)).font(.caption)
                        if let entry=model.messageFilesEntryControl(message) {Button(AppCopy.text("inboxMessageReadTitle")) {if owns(control) {model.openMessageFiles(expected:entry)}}}
                        Text(value(message.text))
                        Text(AppCopy.text("messageStateTitle")+": "+AppCopy.text(message.sourceState.copyKey)).font(.caption)
                        Text(message.created_at.flatMap { AppointmentDate.format(startAt: $0, timezone: agenda.session.selection?.business.timezone, language: AppCopy.language) } ?? AppCopy.text("notAvailable")).font(.caption)
                    }.frame(maxWidth: .infinity, alignment: message.direction == "outbound" ? .trailing : .leading)
                }.listStyle(.plain)
            }
            Spacer(minLength: 0)
        }.padding(.horizontal).navigationTitle(AppCopy.text("inbox"))
    }
}

private struct InboxReplyObservedContent<Content:View>:View {
    @ObservedObject var reply:ReplyDraftViewModel
    let content:()->Content
    init(reply:ReplyDraftViewModel,@ViewBuilder content:@escaping ()->Content) {self.reply=reply;self.content=content}
    var body:some View {let _=reply.returnControl;return content()}
}

private struct InboxHandoffObservedContent<Content:View>:View {
    @ObservedObject var handoff:InboxHandoffViewModel
    let content:()->Content
    init(handoff:InboxHandoffViewModel,@ViewBuilder content:@escaping ()->Content) {self.handoff=handoff;self.content=content}
    var body:some View {let _=handoff.returnControl;return content()}
}
